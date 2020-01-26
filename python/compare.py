import time
from confluent_kafka import Consumer, KafkaError
import struct
from dataclasses import dataclass
import numpy as np
import string
import matplotlib.pyplot as plt
from enum import IntEnum
import argparse
import fieldop
from netCDF4 import Dataset
import time


class ActionType(IntEnum):
    InitFile = 0
    Data = 1
    CloseFile = 2


@dataclass
class MsgKey:
    action_type: int
    key: str
    npatches: int
    mpirank: int
    ilonstart: int
    jlatstart: int
    level: int
    dlon: float
    dlat: float
    lonlen: int
    latlen: int
    levlen: int
    totlonlen: int
    totlatlen: int


@dataclass
class DataRequest:
    fieldname_: str
    patches_: []
    npatches_: -1
    nlevels_: -1

    def __init__(self, fieldname):
        self.fieldname_ = fieldname
        self.patches_ = []
        self.npatches_ = -1
        self.nlevels_ = -1

    def insert(self, patch, msgKey: MsgKey):
        self.patches_.append(patch)
        if self.npatches_ == -1:
            print("KK ", msgKey.npatches)
            self.npatches_ = msgKey.npatches
            self.nlevels_ = msgKey.levlen

    def complete(self) -> bool:
        print("TEST ", len(self.patches_), self.npatches_)
        return (len(self.patches_) == self.npatches_ * self.nlevels_) and len(self.patches_) != 0


@dataclass
class DataRegistry:
    dataRequests_: {}

    def __init__(self):
        self.dataRequests_ = {}


    def complete(self) -> bool:
        for req in self.dataRequests_.values():
            if not req.complete():
                return False
        return True

    def gatherField(self):

        for field in self.dataRequests_:
            domain = fieldop.DomainConf(-1,-1, 0,0,0,0,0)

            df = fieldop.DistributedField(field, domain, self.dataRequests_[field].npatches_)
            df.

        #        for patch in self.dataRequests_["u"].patches_:

        #        domain = field.DomainConf()
        #        df = fieldop.DistributedField
        #        for patch in self.dataRequests_["u"].patches_:

        return
    def subscribe(self, topics):
        for fieldname in topics:
            self.dataRequests_[fieldname] = DataRequest(fieldname)

class DataRegistryStreaming:
    c_ = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'group1',
        'auto.offset.reset': 'earliest'
    })

    def __init__(self):
        self.c_ = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'group1',
            'auto.offset.reset': 'earliest'
        })

    def __del__(self):
        self.c_.close()

    def subscribe(self, topics):
        DataRegistry.subscribe(self, topics)
        print("subscribing to ", topics)
        self.c_.subscribe(topics)

    def poll(self, seconds):
        msg = self.c_.poll(seconds)

        if msg is None:
            print("cont")
            return -1
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            return -1

        print("NNN")
        dt = np.dtype('<f4')
        al = np.frombuffer(msg.value(), dtype=dt)
        msgkey = get_key(msg.key())

        if msgkey.action_type != int(ActionType.Data):
            return

        if msgkey.key[0] in self.dataRequests_.keys():
            field = msgkey.key[0]
            print("ADD", field)

            reg.dataRequests_[field].insert(
                fieldop.SinglePatch(msgkey.ilonstart, msgkey.jlatstart, msgkey.lonlen, msgkey.latlen, msgkey.level,
                                    np.reshape(al, (msgkey.lonlen, msgkey.latlen))), msgkey)


class DataRegistryFile(DataRegistry):
    def __init__(self, filename):
        self.filename_ = filename
        self.npart_ = [2,3]
        DataRegistry.__init__(self)

    def subscribe(self, topics):
        DataRegistry.subscribe(self, topics)
        ncdfData = Dataset(self.filename_, "r")
        for fieldname in topics:
            var = ncdfData[fieldname][:,:,:,0]
            iwidth = int(var.shape[0] / self.npart_[0])
            jwidth = int(var.shape[1] / self.npart_[1])
            for ni in range(0,self.npart_[0]):
                for nj in range(0,self.npart_[1]):
                    istart = ni*iwidth
                    jstart = nj*jwidth
                    iend = min((ni+1)*iwidth, var.shape[0])
                    jend = min((nj + 1) * jwidth, var.shape[1])
                    npsubpatch = np.empty([(iend-istart), (jend-jstart)]).astype(np.float32)
                    subpatch = var[istart:iend, jstart:jend,:]

                    for k in range(0,var.shape[2]):
                        for i in range(0,subpatch.shape[0]):
                            for j in range(0, subpatch.shape[1]):
                                npsubpatch[i,j] = subpatch[i,j,k]

                        msgkey = MsgKey(1, fieldname, self.npart_[0]*self.npart_[1], 0, istart, jstart, k, 0, 0, iwidth, jwidth, var.shape[2], var.shape[0], var.shape[1])

                        self.dataRequests_[fieldname].insert(
                            fieldop.SinglePatch(istart, jstart, iend-istart, jend-jstart, k, npsubpatch), msgkey)


    def poll(self, seconds):
        pass
#        for fieldname in topics:
#            self.dataRequests_[fieldname] = DataRequest(fieldname)
#        print("subscribing to ", topics)
#        self.c_.subscribe(topics)


def get_key(msg):
    c1 = struct.unpack('i8c2i3Q2f5Q', msg)
    stringlist = ''.join([x.decode('utf-8') for x in c1[1:9]])
    allargs = list(c1[0:1]) + [stringlist] + list(c1[9:])
    return MsgKey(*allargs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='consumer')
    parser.add_argument('-f', help='grib/netcdf filename')

    args = parser.parse_args()

    if args.f:
        reg = DataRegistryFile(args.f)
    else:
        reg = DataRegistryStreaming()

    reg.subscribe(["u", "v"])

    vert_prof = None

    while True:
        reg.poll(1.0)
        if reg.complete():
            print("COMPLETE")
            reg.gatherField()
            break