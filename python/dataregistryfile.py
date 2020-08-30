import dataregistry as dreg
import data
import eccodes as ecc
import parseGrib
from datetime import datetime, timezone
import bisect
import numpy as np
import fieldop
import os.path
from netCDF4 import Dataset
from values import undef


class OutputDataRegistryFile(dreg.OutputDataRegistry):
    def __init__(self, filename: str, datapool: data.DataPool, verboseprint=print):
        self.datapool_ = datapool
        self.filename_ = filename
        self.verboseprint_ = verboseprint

    def sendData(self):
        for timest in self.datapool_.data_:
            self.writeDataTimestamp(timest, self.datapool_.data_[timest])
        self.datapool_.data_ = {}

    def writeDataTimestamp(self, timestamp, datapool):
        dt = datetime.fromtimestamp(timestamp)

        for fieldname in datapool:

            filename = self.filename_ + "_"+fieldname+"_"+str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + str(dt.hour).zfill(
                2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2) + ".nc"

            if os.path.isfile(filename):
                raise Exception("File for field exists:", filename)

            out_nc = Dataset(filename, 'w', format='NETCDF4')

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

            self.verboseprint_("creating netcdf variable ", fieldname)
            fvar = out_nc.createVariable(fieldname, "f4",
                                         (levdimname, latdimname, londimname),
                                         fill_value=-undef)
            fvar.missing_value = -undef
            garray = np.array(field, copy=False)

            tmp = np.transpose(garray, (2, 1, 0))

            fvar[:, :, :] = tmp[:, :, :]

            out_nc.close()


class DataRegistryFile(dreg.DataRegistry):
    def __init__(self, filename, verboseprint=print):
        self.filename_ = filename
        self.npart_ = [2, 3]
        dreg.DataRegistry.__init__(self, verboseprint)

    def subscribeImpl(self, topicPrefix, *, userDataReqs, registerall):
        requestHandle = dreg.DataRegistry.subscribeImpl(
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

    def sendGribData(self, *, requestHandle: dreg.RequestHandle = None, userDataReqs=None):
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
                    requestHandle = dreg.DataRegistry.subscribeIfNotExists(
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
