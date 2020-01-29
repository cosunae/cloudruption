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
    domain_ : None

    def __init__(self, fieldname):
        self.fieldname_ = fieldname
        self.patches_ = []
        self.npatches_ = -1
        self.domain_ = None

    def insert(self, patch: fieldop.SinglePatch, msgKey: MsgKey):
        self.patches_.append(patch)

        if self.npatches_ == -1:
            self.npatches_ = msgKey.npatches
            self.domain_ = fieldop.DomainConf(msgKey.totlonlen, msgKey.totlatlen, msgKey.levlen)
        #TODO check in the else the keymsg is compatible with others msgs

    def complete(self) -> bool:
        print("TEST ", len(self.patches_), self.npatches_)
        return (len(self.patches_) == self.npatches_ * self.domain_.levels) and len(self.patches_) != 0

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

    def gatherField(self, datapool):

        for field in self.dataRequests_:

            dataReq = self.dataRequests_[field]
            df = fieldop.DistributedField(field, dataReq.domain_, dataReq.npatches_)

            for patch in dataReq.patches_:
                df.insertPatch(patch)

            bbox = df.bboxPatches()
            gfield = fieldop.field3d(bbox)
            df.gatherField(gfield)
            #TODO insert in datapool

            out_nc = Dataset('compare_2012.nc', 'w', format='NETCDF4')
            out_nc.createDimension("lev", gfield.ksize())
            out_nc.createDimension("lat", gfield.jsize())
            out_nc.createDimension("lon", gfield.isize())

            fvar = out_nc.createVariable(field,"f4",("lev","lat","lon",))

            garray = np.array(gfield, copy=False)

            tmp = np.transpose(garray, (2,1,0))
            fvar[:,:,:] = tmp[:,:,:]
            out_nc.close()
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
                DataField(ilonstart, jlatstart, lonlen, latlen, level,
                                    np.reshape(al, (msgkey.lonlen, msgkey.latlen))), msgkey)


class OutputDataRegistry:
    pass

class OutputDataRegistryFile(OutputDataRegistry):
    def __init__(self, filename):
        self.filename_ = filename

#    def put(self, datafield: DataField):
#        pass

class DataRegistryFile(DataRegistry):
    def __init__(self, filename):
        self.filename_ = filename
        self.npart_ = [2,3]
        DataRegistry.__init__(self)

    def subscribe(self, topics):
        DataRegistry.subscribe(self, topics)
        ncdfData = Dataset(self.filename_, "r")
        for fieldname in topics:
            var = ncdfData[fieldname][0,:,:,:]
            iwidth = int(var.shape[2] / self.npart_[0])
            jwidth = int(var.shape[1] / self.npart_[1])
            for ni in range(0,self.npart_[0]):
                for nj in range(0,self.npart_[1]):
                    istart = ni*iwidth
                    jstart = nj*jwidth
                    iend = min((ni+1)*iwidth, var.shape[2])
                    jend = min((nj + 1) * jwidth, var.shape[1])
                    subpatch = var[:, jstart:jend, istart:iend]

                    for k in range(0,var.shape[0]):
                        npsubpatch = np.empty([(iend - istart), (jend - jstart)]).astype(np.float32)

                        for j in range(0, subpatch.shape[1]):
                            for i in range(0,subpatch.shape[2]):
                                npsubpatch[i,j] = subpatch[k,j,i]

                        msgkey = MsgKey(1, fieldname, self.npart_[0]*self.npart_[1], 0, istart, jstart, k, 0, 0, iwidth, jwidth, var.shape[0], var.shape[2], var.shape[1])
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


    outDatapool = {}
    while True:
        reg.poll(1.0)
        if reg.complete():
            print("COMPLETE")
            reg.gatherField(outDatapool)
            break

#    if args.f:
#        reg = OutputDataRegistryFile("ou_ncfile.nc")
#    else:
#        print("Data streaming not supported yet")

