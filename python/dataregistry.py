import struct
import traceback
from enum import IntEnum
from typing import List

import data
import sys
import fieldop
import numpy as np
from confluent_kafka import Consumer, KafkaError, Producer
from dataclasses import dataclass
import yaml
import datarequest as dreq
import socket
from datetime import datetime, timezone


class ActionType(IntEnum):
    HeaderData = 0
    Data = 1
    EndData = 2


class NullRequest:
    def complete(self):
        return False


# Warning, dataclass decorator here generates static members
class GroupRequest:
    """ A group of requested fields that are associated to a group.
    A group request is considered completed only when all fields registered
    in the group are complete

    Attributes:
      reqFields_ ([UserDataReq])
      timeDataRequests_ ({timestamp: {"field": DataRequest}})
    """

    def __init__(self):
        self.timeDataRequests_ = {}
        self.reqFields_ = []


@dataclass
class RequestHandle:
    groupId_: int
    timestamp_: np.uint64


@dataclass
class DataRegistry:

    def __init__(self, verboseprint):
        self.verboseprint_ = verboseprint
        self.groupRequests_ = []
        self.registerAll_ = False

    def loadData(self, config_filename, *, tag="default"):
        f = open(config_filename, "r", encoding="utf-8")
        datad = yaml.load(f, Loader=yaml.Loader)

        userdatareqs = []
        for field, fieldval in datad[tag]['fields'].items():
            datareqdesc = None

            if "region" in fieldval.keys():
                if 'cuboid' in fieldval['region']:
                    datareqdesc = data.DataReqDesc(
                        *([float(x) for x in fieldval['region']['cuboid']['hregion'].split(',')]))
            userdatareqs.append(data.UserDataReq(field, datareqdesc))

        self.subscribe(datad["product"]+"_", userdatareqs)

    def complete(self):
        self.verboseprint_("checking completeness of data request groups:")
        for groupId, group in enumerate(self.groupRequests_):
            self.verboseprint_("   ... in group ", groupId)
            reqHandle = self.completeg(groupId)
            if reqHandle:
                return reqHandle
        return None

    # https://stackoverflow.com/questions/10202938/how-do-i-use-method-overloading-in-python
    def completegt(self, groupId, timestamp):
        groupRequest = self.groupRequests_[groupId]

        dataRequestDict = groupRequest.timeDataRequests_[timestamp]
        self.verboseprint_(
            "   ... checking for completeness of groupid/timestamp", groupId, "/", timestamp)
        for field in [x.name for x in groupRequest.reqFields_]:
            self.verboseprint_("      ... checking field", field)
            if not dataRequestDict.get(field, NullRequest()).complete():
                return None
        return RequestHandle(groupId, timestamp)

    def completeg(self, groupId):
        groupRequest = self.groupRequests_[groupId]

        self.verboseprint_("  ... groupreq:", groupRequest,
                           groupRequest.timeDataRequests_)
        for timestamp in groupRequest.timeDataRequests_:
            self.verboseprint_("   ... checking timestamp:", timestamp)
            requestHandle = self.completegt(groupId, timestamp)
            if requestHandle:
                return requestHandle

        return None

    def gatherFields(self, datapool: data.DataPool):
        for groupId, groupRequest in enumerate(self.groupRequests_):
            while len(groupRequest.timeDataRequests_):
                self.gatherField(RequestHandle(groupId, list(
                    groupRequest.timeDataRequests_.keys())[0]), datapool)

    def gatherField(self, requestHandle: RequestHandle, datapool: data.DataPool):
        print("gather field:", requestHandle.groupId_, requestHandle.timestamp_)
        if self.completegt(requestHandle.groupId_, requestHandle.timestamp_) is None:
            return
        datareqs = self.groupRequests_[
            requestHandle.groupId_].timeDataRequests_[requestHandle.timestamp_]

        for field in datareqs:
            self.verboseprint_("gathering field/groupid/timestamp: ", field, "/", requestHandle.groupId_,
                               "/", requestHandle.timestamp_)

            dataReq = datareqs[field]
            df = fieldop.DistributedField(
                field, dataReq.npatches_, dataReq.datadesc_)

            for patch in dataReq.completedPatches_:
                df.insertPatch(patch)

            bbox = df.bboxPatches()
            gfield = fieldop.field3d(bbox)
            df.gatherField(gfield)

            datapool.insert(requestHandle.timestamp_, field,
                            gfield, dataReq.datadesc_)

        self.cleanTimestamp(requestHandle)
        return

    def cleanTimestamp(self, requestHandle):
        print("Deleting timestamp ", requestHandle.groupId_,
              requestHandle.timestamp_)
        if requestHandle.timestamp_ in self.groupRequests_[requestHandle.groupId_].timeDataRequests_:
            del self.groupRequests_[requestHandle.groupId_].timeDataRequests_[
                requestHandle.timestamp_]

    def setRegisterAll(self):
        self.registerAll_ = True

    def subscribeIfNotExists(self, topic):
        for groupId, gr in enumerate(self.groupRequests_):
            if topic in [x.name for x in gr.reqFields_]:
                return RequestHandle(groupId, None)
        return DataRegistry.createNewGroupRequest(self, [data.UserDataReq(topic, None)])

    def subscribe(self, topicPrefix, userDataReqs):
        if len(userDataReqs) > 1:
            for field in [x.name for x in userDataReqs]:
                if field.find('*') != -1:
                    raise RuntimeError(
                        "If wildcard is used, only one field (.*) can be declared:", field)

            self.subscribeImpl(
                topicPrefix, userDataReqs=userDataReqs, registerall=False)
        else:
            if userDataReqs[0].name == ".*":
                self.subscribeImpl(
                    topicPrefix, userDataReqs=userDataReqs, registerall=True)
            else:
                self.subscribeImpl(topicPrefix,
                                   userDataReqs=userDataReqs, registerall=False)

    def subscribeImpl(self, *, userDataReqs, registerall: bool):
        if registerall:
            self.setRegisterAll()
            # groups will be created as messages arrive, one group per field
            return RequestHandle(None, None)

        return self.createNewGroupRequest(userDataReqs)

    def createNewGroupRequest(self, userDataReqs):
        self.groupRequests_.append(GroupRequest())
        self.groupRequests_[-1].reqFields_ = userDataReqs
        return RequestHandle(len(self.groupRequests_) - 1, None)

    def insertDataPatch(self, requestHandle: RequestHandle, fieldname, singlePatch, msgKey):
        groupRequest = self.groupRequests_[requestHandle.groupId_]
        userDataRequests = [
            x for x in groupRequest.reqFields_ if x.name == fieldname]
        if len(userDataRequests) > 1:
            raise RuntimeError("More than one field found")

        userDataRequest = userDataRequests[0]

        dataReqs = groupRequest.timeDataRequests_.setdefault(
            requestHandle.timestamp_, {})

        assert (fieldname in [x.name for x in groupRequest.reqFields_])
        if not fieldname in dataReqs:
            dataReqs[fieldname] = dreq.DataRequest(userDataRequest)
        dataReqs[fieldname].insert(singlePatch, msgKey)


def get_key(msg):
    c1 = struct.unpack('i32c2i9Q4f', msg)
    stringlist = ''.join([x.decode('utf-8') for x in c1[1:33]])
    allargs = list(c1[0:1]) + [stringlist] + list(c1[33:])
    key = data.MsgKey(*allargs)
    key.key = key.key.rstrip().rstrip('\x00')
    return key


class DataRegistryStreaming(DataRegistry):
    def __init__(self, broker='localhost:9092', group="group1", verboseprint=print):
        self.c_ = Consumer({
            'bootstrap.servers': broker,
            'group.id': group,
            'auto.offset.reset': 'earliest'
        })
        DataRegistry.__init__(self, verboseprint)

    def __del__(self):
        self.c_.close()

    def subscribeImpl(self, topicPrefix, *, userDataReqs, registerall):
        DataRegistry.subscribeImpl(
            self, userDataReqs=userDataReqs, registerall=registerall)

        if registerall:
            print("SUBSCRIBING TO ^"+topicPrefix+".*")
            self.c_.subscribe(["^"+topicPrefix+".*"])
        else:
            print("SUBSCRIBING TO ", [
                topicPrefix+x.name for x in userDataReqs])
            self.c_.subscribe([topicPrefix+x.name for x in userDataReqs])

    def poll(self, seconds):
        msg = self.c_.poll(seconds)
        if msg is None:
            return -1

        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            sys.exit(1)
            return -1

        self.verboseprint_("polling")
        dt = np.dtype('<f4')
        al = np.frombuffer(msg.value(), dtype=dt)

        msKey: data.MsgKey = get_key(msg.key())

        if msKey.action_type != int(ActionType.Data):
            return

        # Check if msg region overlaps with request
        if self.registerAll_:
            # Only subscribe if the field was not registered yet
            requestHandle = DataRegistry.subscribeIfNotExists(self, msKey.key)
            assert requestHandle
        for groupId, groupRequests in enumerate(self.groupRequests_):
            print("checking a message with key ", msKey.key, " among requests of fields:", [
                x.name for x in groupRequests.reqFields_])
            if msKey.key in [x.name for x in groupRequests.reqFields_]:
                print(" ... inserting data patch:", msKey.key)
                field = msKey.key
                self.insertDataPatch(RequestHandle(groupId, msKey.datetime), field,
                                     fieldop.SinglePatch(msKey.ilonstart, msKey.jlatstart, msKey.lonlen, msKey.latlen,
                                                         msKey.level,
                                                         np.reshape(al, (msKey.lonlen, msKey.latlen), order='F')),
                                     msKey)


class OutputDataRegistry:
    pass


class OutputDataRegistryStreaming(OutputDataRegistry):
    def __init__(self, product, datapool: data.DataPool, broker='localhost:9092', group="group1", verboseprint=print):
        self.product_ = product
        self.datapool_ = datapool
        self.verboseprint_ = verboseprint

        self.p_ = Producer({'bootstrap.servers': broker,
                            'client.id': socket.gethostname()})

    def sendData(self):
        for timest in self.datapool_.data_:
            self.writeDataTimestamp(
                timest, self.datapool_.data_[timest])
        self.datapool_.data_ = {}

    def writeDataTimestamp(self, timestamp, datapool):
        dt = datetime.fromtimestamp(timestamp)

        for fieldname in datapool:
            self.verboseprint_("streaming out ", fieldname)
            field = datapool[fieldname].data_
            fieldn = np.array(field, copy=False)

            for k in range(field.ksize()):
                self.verboseprint_("     on level ", k)

                # TODO there is no way to get that information
                # We should only have sizes. dlon and coordinates should
                # be map from a service from the product
                msgKey = data.MsgKey(1, fieldname, 1, 0, timestamp, 0, 0, 0, field.isize(), field.jsize(
                ), field.ksize(), field.isize(), field.jsize(), 0, 0, field.isize(), field.jsize())

                topic = self.product_+"_"+fieldname

                field2d = fieldn[:, :, k]
                self.p_.produce(topic, key=msgKey.toBytes(),
                                value=field2d.tobytes())
