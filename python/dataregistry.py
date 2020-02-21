import struct
import traceback
from datetime import datetime, timezone
from enum import IntEnum
from typing import List

import data
import eccodes as ecc
import fieldop
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import parseGrib as pgrib
from confluent_kafka import Consumer, KafkaError
from dataclasses import dataclass
from netCDF4 import Dataset
from values import undef


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
        print("nullR")
        return False


@dataclass
class GroupRequest:
    timeDataRequests_ = {}
    reqFields_ = {}


@dataclass
class RequestHandle:
    groupId_: int
    timestamp_: np.uint64


@dataclass
class DataRegistry:
    groupRequests_ = []
    registerAll_ = False

    def complete(self):
        for groupId, group in enumerate(self.groupRequests_):
            reqHandle = self.completeg(groupId)
            if reqHandle:
                return reqHandle
        return None

    # https://stackoverflow.com/questions/10202938/how-do-i-use-method-overloading-in-python
    def completegt(self, groupId, timestamp):
        groupRequest = self.groupRequests_[groupId]

        dataRequest = groupRequest.timeDataRequests_[timestamp]

        for field in groupRequest.reqFields_:
            if not dataRequest.get(field, NullRequest()).complete():
                return None
        return RequestHandle(groupId, timestamp)

    def completeg(self, groupId):
        groupRequest = self.groupRequests_[groupId]
        for timestamp in groupRequest.timeDataRequests_:
            requestHandle = self.completegt(groupId, timestamp)
            if requestHandle:
                return requestHandle

        return None

    def wait(self, groupId):
        while not self.completeg(groupId):
            self.poll(1.0)

        return self.complete(groupId)

    def gatherFields(self, datapool: data.DataPool):
        for groupId, groupRequest in enumerate(self.groupRequests_):
            while len(groupRequest.timeDataRequests_):
                self.gatherField(RequestHandle(groupId, list(groupRequest.timeDataRequests_.keys())[0]), datapool)

    def gatherField(self, requestHandle: RequestHandle, datapool: data.DataPool):
        datareqs = self.groupRequests_[requestHandle.groupId_].timeDataRequests_[requestHandle.timestamp_]

        for field in datareqs:
            print("GATHERING ", field)

            dataReq = datareqs[field]
            df = fieldop.DistributedField(field, dataReq.domain_, dataReq.msgKey_.npatches)

            for patch in dataReq.patches_:
                df.insertPatch(patch)

            bbox = df.bboxPatches()
            gfield = fieldop.field3d(bbox)
            df.gatherField(gfield)

            datapool.insert(requestHandle.timestamp_, field, gfield, dataReq.msgKey_)

        self.cleanTimestamp(requestHandle)
        return

    def cleanTimestamp(self, requestHandle):
        del self.groupRequests_[requestHandle.groupId_].timeDataRequests_[requestHandle.timestamp_]

    def registerAll(self):
        self.registerAll_ = True

    def subscribe(self, topics):
        if topics == ['^.*']:
            self.registerAll()
            return RequestHandle(None, None)

        self.groupRequests_.append(GroupRequest())
        self.groupRequests_[-1].reqFields_ = topics
        return RequestHandle(len(self.groupRequests_) - 1, None)

    def insertDataPatch(self, requestHandle: RequestHandle, fieldname, singlePatch, msgKey):
        groupRequest = self.groupRequests_[requestHandle.groupId_]

        dataReqs = groupRequest.timeDataRequests_.setdefault(requestHandle.timestamp_, {})
        assert (fieldname in groupRequest.reqFields_)
        if not fieldname in dataReqs:
            dataReqs[fieldname] = data.DataRequest(fieldname)
        dataReqs[fieldname].insert(singlePatch, msgKey)


def get_key(msg):
    c1 = struct.unpack('i8c2i9Q4f', msg)
    stringlist = ''.join([x.decode('utf-8') for x in c1[1:9]])
    allargs = list(c1[0:1]) + [stringlist] + list(c1[9:])
    key = data.MsgKey(*allargs)
    return key


class DataRegistryStreaming(DataRegistry):
    def __init__(self, group="group1"):
        self.c_ = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': group,
            'auto.offset.reset': 'earliest'
        })
        DataRegistry.__init__(self)

    def __del__(self):
        self.c_.close()

    def subscribe(self, topics):
        DataRegistry.subscribe(self, topics)
        print("subscribing to ", topics)
        self.c_.subscribe(topics)

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

        msKey: MsgKey = get_key(msg.key())
        if msKey.action_type != int(ActionType.Data):
            return

        for groupId, groupRequests in enumerate(self.groupRequests_):
            if msKey.key[0] in groupRequests.reqFields_:
                field = msKey.key[0]
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
        out_nc = Dataset(filename, 'w', format='NETCDF4')

        londims = {}
        latdims = {}
        levdims = {}

        for fieldname in datapool:
            field = datapool[fieldname].data_
            if field.ksize() not in levdims.keys():
                levdims[field.ksize()] = "lev" + str(len(levdims))
                out_nc.createDimension(levdims[field.ksize()], field.ksize())
            if field.isize() not in londims.keys():
                londims[field.isize()] = "lon" + str(len(londims))
                out_nc.createDimension(londims[field.isize()], field.isize())
            if field.jsize() not in latdims.keys():
                latdims[field.jsize()] = "lat" + str(len(latdims))
                out_nc.createDimension(latdims[field.jsize()], field.jsize())

            fvar = out_nc.createVariable(fieldname, "f4",
                                         (levdims[field.ksize()], latdims[field.jsize()], londims[field.isize()],),
                                         fill_value=-undef)
            fvar.missing_value = -undef
            garray = np.array(field, copy=False)

            tmp = np.transpose(garray, (2, 1, 0))

            fvar[:, :, :] = tmp[:, :, :]

        out_nc.close()


class DataRegistryFile(DataRegistry):
    def __init__(self, format, filename):
        self.format_ = format
        self.filename_ = filename
        self.npart_ = [2, 3]
        DataRegistry.__init__(self)

    def subscribe(self, topics):
        requestHandle = DataRegistry.subscribe(self, topics)
        self.sendGribData(requestHandle=requestHandle, topics=topics)

        return requestHandle

    def registerAll(self):
        DataRegistry.registerAll(self)

    def wait(self):
        pass

    def getGribFieldname(self, msg):

        gribDict = pgrib.gribParams
        candidateFields = []
        for field in gribDict:
            params = gribDict[field]
            if (params["table"] == msg["table2Version"]) and (
                    params["parameter"] == msg["indicatorOfParameter"]):
                candidateFields.append(field)

        if len(candidateFields) == 0:
            return None
        elif len(candidateFields) == 1:
            return candidateFields[0]
        else:
            candidateFieldsO = candidateFields.copy()
            candidateFields = []
            for field in candidateFieldsO:
                params = gribDict[field]
                if (not "typeLevel" in params and msg["indicatorOfTypeOfLevel"] == "ml"):
                    candidateFields.append(field)
                elif ("typeLevel" in params and params["typeLevel"] == pgrib.typeLevelParams[msg["typeOfLevel"]]):
                    candidateFields.append(field)
            if len(candidateFields) == 0:
                return None
            elif len(candidateFields) == 1:
                return candidateFields[0]
            else:
                candidateFieldsO = candidateFields.copy()
                candidateFields = []
                for field in candidateFieldsO:
                    params = gribDict[field]
                    if (not "timeRangeType" in params and msg["timeRangeIndicator"] == 0):

                        candidateFields.append(field)
                    elif ("timeRangeType" in params and params["timeRangeType"] == msg["timeRangeIndicator"]):
                        candidateFields.append(field)
                if len(candidateFields) == 0:
                    return None
                elif len(candidateFields) == 1:
                    return candidateFields[0]
                else:
                    print("WARNING NOT YET SP", len(candidateFields), candidateFields)

        return None

    def getTimestamp(self, gribMsg):
        dt = datetime(gribMsg["year"], gribMsg["month"], gribMsg["day"], gribMsg["hour"], gribMsg["minute"],
                      gribMsg["second"],
                      tzinfo=timezone.utc)
        return int(datetime.timestamp(dt))

    def sendGribData(self, *, requestHandle: RequestHandle = None, topics=None):
        if not self.registerAll_ and (not requestHandle or not topics):
            raise RuntimeError("If not all topics are registered, we need to pass a request handle and list of topics")

        ltopics = topics
        with ecc.GribFile(self.filename_) as grib:
            nlevels = {}
            for i in range(len(grib)):
                msg = ecc.GribMessage(grib)

                fieldname = self.getGribFieldname(msg)
                if not fieldname:
                    print('WARNING: found a grib field with no match in table : ', msg['cfVarName'],
                          msg['table2Version'], msg['indicatorOfParameter'], msg['indicatorOfTypeOfLevel'])
                    continue
                if self.registerAll_:
                    ltopics = [fieldname]
                    requestHandle = DataRegistry.subscribe(self, ltopics)

                if fieldname in ltopics:
                    timestamp = self.getTimestamp(msg)

                    nlevels.setdefault(timestamp, {}).setdefault(fieldname, 0)

                    nlevels[timestamp][fieldname] += 1
                    requestHandle.timestamp_ = timestamp

                    ni = msg['Ni']
                    nj = msg['Nj']

                    lord = 'F'
                    if not msg['jPointsAreConsecutive'] == 0:
                        lord = 'C'

                    arr = np.reshape(ecc.codes_get_values(msg.gid), (ni, nj), order='F').astype(np.float32)
                    lev = msg["bottomLevel"]

                    msgkey = data.MsgKey(1, fieldname, 1, 0, timestamp, 0, 0, lev, ni,
                                         ni, 60, ni, nj, msg["longitudeOfFirstGridPoint"],
                                         msg["longitudeOfLastGridPoint"],
                                         msg["latitudeOfFirstGridPoint"], msg["latitudeOfLastGridPoint"])

                    self.insertDataPatch(requestHandle, fieldname, fieldop.SinglePatch(0, 0, ni, nj, lev, arr), msgkey)

            # This is the equivalent to sending the header
            for timestamp in nlevels:
                for field in nlevels[timestamp]:
                    for groupRequest in self.groupRequests_:
                        if field in groupRequest.reqFields_:
                            groupRequest.timeDataRequests_[timestamp][field].setNLevels(nlevels[timestamp][field])

    def poll(self, seconds):
        pass
