import struct
import traceback
from datetime import datetime, timezone
from enum import IntEnum
from typing import List

import data
import sys
import eccodes as ecc
import fieldop
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import parseGrib
from confluent_kafka import Consumer, KafkaError
# from kafka import KafkaConsumer
from dataclasses import dataclass
from netCDF4 import Dataset
from values import undef
import yaml
import os.path
import datarequest as dreq
import bisect


class ActionType(IntEnum):
    HeaderData = 0
    Data = 1
    EndData = 2


def plot2d(arr):
    fig = plt.figure(figsize=(6, 3.2))

    ax = fig.add_subplot(111)
    ax.set_title('colorMap')
    plt.imshow(arr)
    ax.set_aspect('equal')

    cax = fig.add_axes([0.12, 0.1, 0.78, 0.8])
    cax.get_xaxis().set_visible(False)
    cax.get_yaxis().set_visible(False)
    cax.patch.set_alpha(0)
    cax.set_frame_on(False)
    plt.colorbar(orientation='vertical')
    plt.show()


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

    def __init__(self):
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

        self.subscribe(userdatareqs)

    def complete(self):
        for groupId, group in enumerate(self.groupRequests_):
            print("check completeness of group", groupId, )
            reqHandle = self.completeg(groupId)
            if reqHandle:
                return reqHandle
        return None

    # https://stackoverflow.com/questions/10202938/how-do-i-use-method-overloading-in-python
    def completegt(self, groupId, timestamp):
        groupRequest = self.groupRequests_[groupId]

        dataRequestDict = groupRequest.timeDataRequests_[timestamp]
        print("checking for completeness of groupd/timestamp", groupId, timestamp)
        for field in [x.name for x in groupRequest.reqFields_]:
            print(" ... checking field", field)
            if not dataRequestDict.get(field, NullRequest()).complete():
                return None
        return RequestHandle(groupId, timestamp)

    def completeg(self, groupId):
        groupRequest = self.groupRequests_[groupId]

        for timestamp in groupRequest.timeDataRequests_:
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
        datareqs = self.groupRequests_[
            requestHandle.groupId_].timeDataRequests_[requestHandle.timestamp_]

        for field in datareqs:
            print("GATHERING ", field, requestHandle.groupId_,
                  requestHandle.timestamp_)

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
        del self.groupRequests_[requestHandle.groupId_].timeDataRequests_[
            requestHandle.timestamp_]

    def setRegisterAll(self):
        self.registerAll_ = True

    def subscribeIfNotExists(self, topic):
        for groupId, gr in enumerate(self.groupRequests_):
            if topic in [x.name for x in gr.reqFields_]:
                return RequestHandle(groupId, None)
        return DataRegistry.createNewGroupRequest(self, [data.UserDataReq(topic, None)])

    def subscribe(self, userDataReqs):
        if len(userDataReqs) > 1:
            for field in [x.name for x in userDataReqs]:
                if field.find('*') != -1:
                    raise RuntimeError(
                        "If wildcard is used, only one field (.*) can be declared:", field)

            self.subscribeImpl(userDataReqs=userDataReqs, registerall=False)
        else:
            if userDataReqs[0].name == ".*":
                self.subscribeImpl(userDataReqs=userDataReqs, registerall=True)
            else:
                self.subscribeImpl(
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
    key.key = key.key.rstrip('\x00')
    return key


class DataRegistryStreaming(DataRegistry):
    def __init__(self, group="group1"):
        self.c_ = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': group,
            'auto.offset.reset': 'earliest',
            #            # ''
            #            'debug': "consumer"
        })
        # self.c_ = KafkaConsumer(bootstrap_servers='localhost:9092',
        #                        group_id=group)
        DataRegistry.__init__(self)

    def __del__(self):
        self.c_.close()

    def subscribeImpl(self, *, userDataReqs, registerall):
        DataRegistry.subscribeImpl(
            self, userDataReqs=userDataReqs, registerall=registerall)

        if registerall:
            print("SUBSCRIBING TO ^cosmo_.*")
            self.c_.subscribe(["^cosmo_.*"])
        else:
            print("SUBSCRIBING TO ", ["cosmo_"+x.name for x in userDataReqs])
            self.c_.subscribe(["cosmo_"+x.name for x in userDataReqs])

    def poll(self, seconds):
        msg = self.c_.poll(seconds)
        if msg is None:
            return -1

        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            sys.exit(1)
            return -1

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
            if msKey.key in [x.name for x in groupRequests.reqFields_]:
                field = msKey.key
                self.insertDataPatch(RequestHandle(groupId, msKey.datetime), field,
                                     fieldop.SinglePatch(msKey.ilonstart, msKey.jlatstart, msKey.lonlen, msKey.latlen,
                                                         msKey.level,
                                                         np.reshape(al, (msKey.lonlen, msKey.latlen), order='F')),
                                     msKey)


class OutputDataRegistry:
    pass


class OutputDataRegistryFile(OutputDataRegistry):
    def __init__(self, filename: str, datapool: data.DataPool):
        self.datapool_ = datapool
        self.filename_ = filename

    def sendData(self):
        for timest in self.datapool_.data_:
            self.writeDataTimestamp(timest, self.datapool_.data_[timest])
        self.datapool_.data_ = {}

    def writeDataTimestamp(self, timestamp, datapool):
        dt = datetime.fromtimestamp(timestamp)
        filename = self.filename_ + str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + str(dt.hour).zfill(
            2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2) + ".nc"

        openmode = 'a' if os.path.isfile(filename) else 'w'

        out_nc = Dataset(filename, openmode, format='NETCDF4')

        for fieldname in datapool:
            field = datapool[fieldname].data_
            levdimname = "lev" + str(field.ksize())
            if not levdimname in out_nc.dimensions:
                out_nc.createDimension(levdimname, field.ksize())

            londimname = "lon" + str(field.isize())
            if not londimname in out_nc.dimensions:
                out_nc.createDimension(londimname, field.isize())

            latdimname = "lat" + str(field.jsize())
            if not latdimname in out_nc.dimensions:
                out_nc.createDimension(latdimname, field.jsize())

            fvar = out_nc.createVariable(fieldname, "f4",
                                         (levdimname, latdimname, londimname),
                                         fill_value=-undef)
            fvar.missing_value = -undef
            garray = np.array(field, copy=False)

            tmp = np.transpose(garray, (2, 1, 0))

            fvar[:, :, :] = tmp[:, :, :]

        out_nc.close()


class DataRegistryFile(DataRegistry):
    def __init__(self, filename):
        self.filename_ = filename
        self.npart_ = [2, 3]
        DataRegistry.__init__(self)

    def subscribeImpl(self, *, userDataReqs, registerall):
        requestHandle = DataRegistry.subscribeImpl(
            self, userDataReqs=userDataReqs, registerall=registerall)
        self.sendGribData(requestHandle=requestHandle,
                          userDataReqs=userDataReqs)

        return requestHandle

    def wait(self):
        pass

    def getTimestamp(self, gribMsg):
        dt = datetime(gribMsg["year"], gribMsg["month"], gribMsg["day"], gribMsg["hour"], gribMsg["minute"],
                      gribMsg["second"],
                      tzinfo=timezone.utc)
        return int(datetime.timestamp(dt))

    def sendGribData(self, *, requestHandle: RequestHandle = None, userDataReqs=None):
        if not self.registerAll_ and (not requestHandle or not userDataReqs):
            raise RuntimeError(
                "If not all topics are registered, we need to pass a request handle and list of topics")

        luserDataReqs = userDataReqs
        # timestamp: {fieldname: []}
        fieldsmetadata = {}
        with ecc.GribFile(self.filename_) as grib:
            # Warning do not use/print/etc len(grib), for strange reasons it will always return the same msg
            for i in range(len(grib)):
                msg = ecc.GribMessage(grib)

                fieldname = parseGrib.getGribFieldname(table2Version=msg["table2Version"], indicatorOfParameter=msg["indicatorOfParameter"],
                                                       indicatorOfTypeOfLevel=msg["indicatorOfTypeOfLevel"],
                                                       typeOfLevel=msg["typeOfLevel"], timeRangeIndicator=msg["timeRangeIndicator"])
                # fieldname2 = self.getGribFieldname(msg)
                if not fieldname:
                    print('WARNING: found a grib field with no match in table : ', msg['cfVarName'],
                          msg['table2Version'], msg['indicatorOfParameter'], msg['indicatorOfTypeOfLevel'])
                    continue

                if fieldname in [x.name for x in luserDataReqs] or self.registerAll_:
                    timestamp = self.getTimestamp(msg)
                    toplevel = msg["topLevel"]
                    levels = fieldsmetadata.setdefault(
                        timestamp, {}).setdefault(fieldname, [])
                    bisect.insort(levels, toplevel)

        with ecc.GribFile(self.filename_) as grib:
            # Warning do not use/print/etc len(grib), for strange reasons it will always return the same msg
            for i in range(len(grib)):
                msg = ecc.GribMessage(grib)

                fieldname = parseGrib.getGribFieldname(table2Version=msg["table2Version"], indicatorOfParameter=msg["indicatorOfParameter"],
                                                       indicatorOfTypeOfLevel=msg["indicatorOfTypeOfLevel"],
                                                       typeOfLevel=msg["typeOfLevel"], timeRangeIndicator=msg["timeRangeIndicator"])
                # fieldname2 = self.getGribFieldname(msg)
                if not fieldname:
                    print('WARNING: found a grib field with no match in table : ', msg['cfVarName'],
                          msg['table2Version'], msg['indicatorOfParameter'], msg['indicatorOfTypeOfLevel'])
                    continue
                if self.registerAll_:
                    # Only subscribe if the field was not registered yet
                    requestHandle = DataRegistry.subscribeIfNotExists(
                        self, fieldname)
                    assert requestHandle

                if fieldname in [x.name for x in luserDataReqs] or self.registerAll_:
                    timestamp = self.getTimestamp(msg)

                    levels = fieldsmetadata[timestamp][fieldname]

                    requestHandle.timestamp_ = timestamp

                    ni = msg['Ni']
                    nj = msg['Nj']

                    lord = 'F'
                    if not msg['jPointsAreConsecutive'] == 0:
                        lord = 'C'

                    arr = np.reshape(ecc.codes_get_values(
                        msg.gid), (ni, nj), order='F').astype(np.float32)
                    lev = msg["topLevel"]

                    level_index = levels.index(lev)
                    msgkey = data.MsgKey(1, fieldname, 1, 0, timestamp, 0, 0, level_index, ni,
                                         nj, len(
                                             levels), ni, nj, msg["longitudeOfFirstGridPoint"],
                                         msg["longitudeOfLastGridPoint"],
                                         msg["latitudeOfFirstGridPoint"], msg["latitudeOfLastGridPoint"])
                    self.insertDataPatch(requestHandle, fieldname, fieldop.SinglePatch(
                        0, 0, ni, nj, level_index, arr), msgkey)

    def poll(self, seconds):
        pass
