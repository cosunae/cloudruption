from enum import IntEnum

import eccodes as ecc
import fieldop
import matplotlib.pyplot as plt
import numpy as np
from confluent_kafka import Consumer, KafkaError
from dataclasses import dataclass
from netCDF4 import Dataset
from values import undef


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
    longitudeOfFirstGridPoint: float
    longitudeOfLastGridPoint: float
    latitudeOfFirstGridPoint: float
    latitudeOfLastGridPoint: float


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


@dataclass
class DataRequest:
    fieldname_: str
    patches_: []
    npatches_: -1
    domain_: None
    nlevels_ : None

    def __init__(self, fieldname):
        self.fieldname_ = fieldname
        self.patches_ = []
        self.npatches_ = -1
        self.domain_ = None

    def insert(self, patch: fieldop.SinglePatch, msgKey: MsgKey):
        self.patches_.append(patch)

        if self.npatches_ == -1:
            self.npatches_ = msgKey.npatches
            self.domain_ = fieldop.DomainConf(msgKey.totlonlen, msgKey.totlatlen, -1)
        # TODO check in the else the keymsg is compatible with others msgs

    def setNLevels(self, nlevels):
        self.nlevels_ = nlevels
        self.domain_.levels = nlevels

    def complete(self) -> bool:
        print("TEST ",  self.fieldname_, len(self.patches_), self.npatches_)
        # Not a single patch was inserted
        if self.npatches_ == -1:
            return False
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

    def gatherField(self, datapool):

        for field in self.dataRequests_:

            dataReq = self.dataRequests_[field]
            df = fieldop.DistributedField(field, dataReq.domain_, dataReq.npatches_)

            for patch in dataReq.patches_:
                df.insertPatch(patch)

            bbox = df.bboxPatches()
            gfield = fieldop.field3d(bbox)
            df.gatherField(gfield)

            datapool[field] = gfield

        return

    def subscribe(self, topics):
        for fieldname in topics:
            if fieldname == 'all':
                continue
            self.dataRequests_[fieldname] = DataRequest(fieldname)

    def appendTopic(self, topic):
        print(topic, self.dataRequests_.keys())
        if topic not in self.dataRequests_.keys():
            print("INS ", topic)
            self.dataRequests_[topic] = DataRequest(topic)

def get_key(msg):
    c1 = struct.unpack('i8c2i3Q2f5Q4f', msg)
    stringlist = ''.join([x.decode('utf-8') for x in c1[1:9]])
    allargs = list(c1[0:1]) + [stringlist] + list(c1[9:])
    return MsgKey(*allargs)


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
            return -1
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            sys.exit(1)
            return -1

        dt = np.dtype('<f4')
        al = np.frombuffer(msg.value(), dtype=dt)
        msgkey = get_key(msg.key())

        if msgkey.action_type != int(ActionType.Data):
            return

        if msgkey.key[0] in self.dataRequests_.keys():
            field = msgkey.key[0]
            reg.dataRequests_[field].insert(
                DataField(ilonstart, jlatstart, lonlen, latlen, level,
                          np.reshape(al, (msgkey.lonlen, msgkey.latlen))), msgkey)


class OutputDataRegistry:
    pass


class OutputDataRegistryFile(OutputDataRegistry):
    def __init__(self, filename, datapool):
        self.datapool_ = datapool
        self.filename_ = filename

    def sendData(self):
        out_nc = Dataset('compare_2012.nc', 'w', format='NETCDF4')

        londims = {}
        latdims = {}
        levdims = {}

        for fieldname in self.datapool_:
            field = self.datapool_[fieldname]
            if field.ksize() not in levdims.keys():
                levdims[field.ksize()] = "lev"+str(len(levdims))
                out_nc.createDimension(levdims[field.ksize()], field.ksize())
            if field.isize() not in londims.keys():
                londims[field.isize()] = "lon"+str(len(londims))
                out_nc.createDimension(londims[field.isize()], field.isize())
            if field.jsize() not in latdims.keys():
                latdims[field.jsize()] = "lat"+str(len(latdims))
                out_nc.createDimension(latdims[field.jsize()], field.jsize())

            fvar = out_nc.createVariable(fieldname, "f4", (levdims[field.ksize()], latdims[field.jsize()], londims[field.isize()],), fill_value=-undef)
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
        DataRegistry.subscribe(self, topics)

        if self.format_ == 'nc':
            self.sendNetCDFData(topics)
        else:
            if self.format_ == 'grib':
                self.sendGribData(topics)

    def sendNetCDFData(self, topics):
        ncdfData = Dataset(self.filename_, "r")

        for fieldname in topics:
            var = ncdfData[fieldname][0, :, :, :]
            self.dataRequests_[fieldname].setNLevels(var.shape[0])

            iwidth = int(var.shape[2] / self.npart_[0])
            jwidth = int(var.shape[1] / self.npart_[1])
            for ni in range(0, self.npart_[0]):
                for nj in range(0, self.npart_[1]):
                    istart = ni * iwidth
                    jstart = nj * jwidth
                    iend = min((ni + 1) * iwidth, var.shape[2])
                    jend = min((nj + 1) * jwidth, var.shape[1])
                    subpatch = var[:, jstart:jend, istart:iend]

                    for k in range(0, var.shape[0]):
                        npsubpatch = np.empty([(iend - istart), (jend - jstart)]).astype(np.float32)

                        for j in range(0, subpatch.shape[1]):
                            for i in range(0, subpatch.shape[2]):
                                npsubpatch[i, j] = subpatch[k, j, i]

                        msgkey = MsgKey(1, fieldname, self.npart_[0] * self.npart_[1], 0, istart, jstart, k, 0, 0,
                                        iwidth, jwidth, var.shape[0], var.shape[2], var.shape[1], 0, 0, 0, 0)
                        self.dataRequests_[fieldname].insert(
                            fieldop.SinglePatch(istart, jstart, iend - istart, jend - jstart, k, npsubpatch), msgkey)

    def sendGribData(self, topics):

        with ecc.GribFile(self.filename_) as grib:
            nlevels = {}
            for i in range(len(grib)):
                msg = ecc.GribMessage(grib)

#                print(msg.keys())
                fieldname = msg["cfVarName"]
                #                print(fieldname)
                if fieldname in topics or 'all' in topics:
                    # Hack I dont know why t has 60 levels (in layer) plus [0,0]
                    if msg["bottomLevel"] == 0 and msg["topLevel"] == 0:
                        continue

                    if fieldname not in nlevels.keys():
                        nlevels[fieldname] = 0

                    nlevels[fieldname] += 1

                    if 'all' in topics:
                        self.appendTopic(fieldname)

                    print(msg["gridDefinition"], msg["gridType"], msg["gridDefinitionTemplateNumber"],
                          msg["gridDefinitionDescription"], msg["latitudeOfFirstGridPoint"], msg["cfVarName"],
                          msg["latitudeOfLastGridPoint"], msg["Ni"], msg["Nj"], msg["GRIBEditionNumber"],
                          msg['paramId'], msg['bottomLevel'], msg['topLevel'], msg['table2Version'], msg['indicatorOfParameter'])

                    ni = msg['Ni']
                    nj = msg['Nj']

                    arr2 = np.reshape(ecc.codes_get_values(msg.gid), (nj, ni)).astype(np.float32)

                    # TODO super hack. Need to understand the layouts, or pass strides to SinglePatch
                    var = np.empty([ni, nj]).astype(np.float32)
                    var[:, :] = np.transpose(arr2[:, :], (1, 0))

                    lev = msg["bottomLevel"]

                    #                    iwidth = int(var.shape[0] / self.npart_[0])
                    #                    jwidth = int(var.shape[1] / self.npart_[1])
                    #                    for nbi in range(0, self.npart_[0]):
                    #                       for nbj in range(0, self.npart_[1]):
                    #                           istart = nbi * iwidth
                    #                           jstart = nbj * jwidth
                    #                           iend = min((nbi + 1) * iwidth-1, nj)
                    #                           jend = min((nbj + 1) * jwidth-1, ni)
                    #                           subpatch = var[istart:iend, jstart:jend]

                    #                            print("III", istart, jstart, iend, jend, iwidth, jwidth)
                    #                            msgkey = MsgKey(1, fieldname, self.npart_[0] * self.npart_[1], 0, istart, jstart, lev, 0,
                    #                                                0, iwidth, jwidth, 60, ni,nj)
                    #                            self.dataRequests_[fieldname].insert(
                    #                                    fieldop.SinglePatch(istart, jstart, iend - istart, jend - jstart, lev, subpatch),
                    #                                    msgkey)

                    msgkey = MsgKey(1, fieldname, 1, 0, 0, 0, lev, 0, 0, ni,
                                    ni, 60, ni, nj, msg["longitudeOfFirstGridPoint"], msg["longitudeOfLastGridPoint"],
                                    msg["latitudeOfFirstGridPoint"], msg["latitudeOfLastGridPoint"], )
                    print("Inserting")
                    self.dataRequests_[fieldname].insert(
                        fieldop.SinglePatch(0, 0, ni, nj, lev, var), msgkey)

            #This is the equivalent to sending the header
            for field in nlevels:
                self.dataRequests_[field].setNLevels(nlevels[field])

    def poll(self, seconds):
        pass
