from dataclasses import dataclass
import numpy as np
import fieldop


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
