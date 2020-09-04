from dataclasses import dataclass
import numpy as np
import fieldop
import struct


@dataclass
class MsgKey:
    action_type: int
    key: str
    npatches: int
    mpirank: int
    datetime: np.uint64
    ilonstart: np.uint64
    jlatstart: np.uint64
    level: np.uint64
    lonlen: np.uint64
    latlen: np.uint64
    levlen: np.uint64
    totlonlen: np.uint64
    totlatlen: np.uint64
    longitudeOfFirstGridPoint: float
    longitudeOfLastGridPoint: float
    latitudeOfFirstGridPoint: float
    latitudeOfLastGridPoint: float

    @staticmethod
    def fromBytes(msg):
        c1 = struct.unpack('i32c2i9Q4f', msg)
        stringlist = ''.join([x.decode('utf-8') for x in c1[1:33]])
        allargs = list(c1[0:1]) + [stringlist] + list(c1[33:])
        key = MsgKey(*allargs)
        key.key = key.key.rstrip().rstrip('\x00')
        return key

    def toBytes(self):
        strlistb = [bytes(x, 'UTF-8')
                    for x in list(self.key+" "*(32-len(self.key)))]
        args = [self.action_type] + strlistb + [self.npatches, self.mpirank,
                                                self.datetime, self.ilonstart, self.jlatstart, self.level, self.lonlen,
                                                self.latlen, self.levlen, self.totlonlen, self.totlatlen,
                                                self.longitudeOfFirstGridPoint, self.longitudeOfLastGridPoint,
                                                self.latitudeOfFirstGridPoint, self.latitudeOfLastGridPoint]

        return struct.pack('i32c2i9Q4f', *args)


@dataclass
class DataReqDesc:
    longitudeOfFirstGridPoint: float
    longitudeOfLastGridPoint: float
    latitudeOfFirstGridPoint: float
    latitudeOfLastGridPoint: float


class FieldObject:
    def __init__(self, field: fieldop.field3d, datadesc: fieldop.DataDesc):
        self.data_: fieldop.field3d = field
        self.datadesc_: fieldop.DataDesc = datadesc


@dataclass
class UserDataReq:
    name: str
    data_desc: DataReqDesc


class DataPool:

    def __init__(self):
        self.data_ = {}

    def delete(self, key):
        self.data_.pop(key)

    def __getitem__(self, item):
        return self.data_[item]

    def insert(self, timestamp, fieldname, field, datadesc):
        self.data_.setdefault(timestamp, {})[
            fieldname] = FieldObject(field, datadesc)

    def timestamps(self):
        return self.data_.keys()
