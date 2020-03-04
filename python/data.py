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


@dataclass
class DataDesc(DataReqDesc):
    datetime: np.uint64
    ilonstart: np.uint64
    jlatstart: np.uint64
    levelstart: np.uint64
    lonlen: np.uint64
    latlen: np.uint64
    levlen: np.uint64


class FieldObject:
    def __init__(self, field: fieldop.field3d, datadesc: DataDesc):
        self.data_: fieldop.field3d = field
        self.datadesc_: DataDesc = datadesc


@dataclass
class UserDataReq:
    name: str
    data_desc: DataReqDesc


@dataclass
class DataRequest:

    def __init__(self, user_data_req: UserDataReq):
        self.user_data_req_: UserDataReq = user_data_req
        self.patches_ = []
        self.npatches_ = None
        self.datadesc_ = None

    def insert(self, patch: fieldop.SinglePatch, msgKey: MsgKey):
        self.patches_.append(patch)

        if not self.datadesc_:
            self.datadesc_ = DataDesc(msgKey.longitudeOfFirstGridPoint, msgKey.longitudeOfLastGridPoint, msgKey.latitudeOfFirstGridPoint,
                                      msgKey.latitudeOfLastGridPoint, msgKey.datetime, msgKey.ilonstart, msgKey.jlatstart, 0, msgKey.totlonlen, msgKey.totlatlen, msgKey.levlen)
        else:
            print("ASSERT", self.datadesc_.longitudeOfFirstGridPoint,
                  msgKey.longitudeOfFirstGridPoint)
            print("ASSERT", self.datadesc_.longitudeOfLastGridPoint,
                  msgKey.longitudeOfLastGridPoint)

            assert self.datadesc_.longitudeOfFirstGridPoint == msgKey.longitudeOfFirstGridPoint
            assert self.datadesc_.longitudeOfLastGridPoint == msgKey.longitudeOfLastGridPoint
            assert self.datadesc_.latitudeOfFirstGridPoint == msgKey.latitudeOfFirstGridPoint
            assert self.datadesc_.latitudeOfLastGridPoint == msgKey.latitudeOfLastGridPoint
            assert self.datadesc_.datetime == msgKey.datetime
#            assert self.datadesc_.ilonstart == msgKey.ilonstart
#            assert self.datadesc_.jlatstart == msgKey.jlatstart
            assert self.datadesc_.levelstart == 0
            assert self.datadesc_.lonlen == msgKey.totlonlen
            assert self.datadesc_.latlen == msgKey.totlatlen
#            assert self.datadesc_.levlen == msgKey.levlen

        if not self.npatches_:
            print("NPATCHES ", self.user_data_req_.name, msgKey.npatches)
            self.npatches_ = msgKey.npatches
        else:
            assert self.npatches_ == msgKey.npatches

        # TODO check in the else the keymsg is compatible with others msgs

    # The NLevels can not come via the msgKey, but rather on a separate header msg
    def setNLevels(self, nlevels):
        if not self.datadesc_:
            assert False
#            self.domain_ = fieldop.DomainConf(0, 0, nlevels)
        else:
            self.datadesc_.levlen = nlevels

    def complete(self) -> bool:
        # Not a single patch was inserted
        if not self.datadesc_:
            return False
        print("RET ", self.user_data_req_.name,  len(self.patches_), self.npatches_, self.datadesc_.levlen, (len(
            self.patches_) == self.npatches_ * self.datadesc_.levlen) and (len(self.patches_) != 0))
        return (len(self.patches_) == self.npatches_ * self.datadesc_.levlen) and (len(self.patches_) != 0)


class DataPool:

    def __init__(self):
        self.data_ = {}

    def delete(self, key):
        self.data_.pop(key)

    def __getitem__(self, item):
        return self.data_[item]

    def insert(self, timestamp, fieldname, field, msgKey):
        self.data_.setdefault(timestamp, {})[
            fieldname] = FieldObject(field, msgKey)
