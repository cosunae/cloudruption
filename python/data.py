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
class DataRequest:

    def __init__(self, fieldname):
        self.fieldname_ : str= fieldname
        self.patches_ = []
        self.domain_ = None
        self.msgKey_ = None

    def insert(self, patch: fieldop.SinglePatch, msgKey: MsgKey):
        self.patches_.append(patch)

        if not self.msgKey_:
            self.msgKey_ = msgKey
            if self.domain_:
                #levels is not check since for the file grib send, the value is only sent at the end and not with every message
                assert self.domain_.isize == msgKey.totlonlen
                assert self.domain_.jsize == msgKey.totlatlen
            else:
                self.domain_ = fieldop.DomainConf(msgKey.totlonlen, msgKey.totlatlen, msgKey.levlen)
        else:
            assert msgKey.npatches == self.msgKey_.npatches

        # TODO check in the else the keymsg is compatible with others msgs

    # The NLevels can not come via the msgKey, but rather on a separate header msg
    def setNLevels(self, nlevels):
        if not self.domain_:
            self.domain_ = fieldop.DomainConf(0, 0, nlevels)
        else:
            self.domain_.levels = nlevels

    def complete(self) -> bool:
        # Not a single patch was inserted
        #print("COMPLETE ", self.msgKey_, len(self.patches_), self.msgKey_.npatches, self.domain_.levels)
        if not ((len(self.patches_) == self.msgKey_.npatches * self.domain_.levels) and len(self.patches_) != 0):
            print("COMPLETE ", self.msgKey_, len(self.patches_), self.msgKey_.npatches, self.domain_.levels)
            print("NOT COMPLETE")
        if not self.msgKey_:
            print("Early ret")
            return False
        print("RET " , (len(self.patches_) == self.msgKey_.npatches * self.domain_.levels) and (len(self.patches_) != 0))
        return (len(self.patches_) == self.msgKey_.npatches * self.domain_.levels) and (len(self.patches_) != 0)


class DataDesc:
    def __init__(self, field: fieldop.field3d, msgKey: MsgKey):
        self.data_: fieldop.field3d = field
        self.metadata_: MsgKey = msgKey

class DataPool:

    def __init__(self):
        self.data_ = {}

    def delete(self, key):
        self.data_.pop(key)

    def __getitem__(self, item):
        return self.data_[item]

    def insert(self, timestamp, fieldname, field, msgKey):
        self.data_.setdefault(timestamp, {})[fieldname] = DataDesc(field, msgKey)
