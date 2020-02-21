import time
import struct
import numpy as np
import string
import matplotlib.pyplot as plt
import argparse
import time
import dataregistry as dreg
from numba import jit, stencil
from typing import List
import math
import fieldop
import data

@stencil
def stencilx(a):
    return np.float32(0.5) * (a[-1,0,0] + a[1, 0,0 ])

@stencil
def stencily(a):
    return np.float32(0.5) * (a[0,-1,0] + a[0, 1,0 ])

def destagger(field, stagx, stagy):
    garray = np.array(field, copy=False)

    if stagx:
        return stencilx(garray)
    if stagy:
        return stencily(garray)

    return garray

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='consumer')
    parser.add_argument('--file', help='grib/netcdf filename')
    parser.add_argument('--format', help='grib or nc')
    parser.add_argument('--topics', help='comma separated list of topics to subscribe')

    args = parser.parse_args()
    format = args.format
    if not format:
        format="grib"

    topics = ['^.*']
    if args.topics:
        topics = args.topics.split(',')

    if format not in ("grib", "nc"):
        print("invalid file format")
        sys.exit(1)

    if args.file:
        reghs = dreg.DataRegistryFile(format, args.file)
    else:
        reghs = dreg.DataRegistryStreaming()

    tmpDatapool = data.DataPool()

    reghs.subscribe(["T"])

    hsurfkey = None
    while True:
        reghs.poll(1.0)
        reqHandle = reghs.complete()
        if reqHandle:
            reghs.gatherField(reqHandle, tmpDatapool)
            hsurfkey = tmpDatapool[reqHandle.timestamp_]["T"].metadata_
            break

    dx = (hsurfkey.longitudeOfLastGridPoint - hsurfkey.longitudeOfFirstGridPoint)/float(hsurfkey.totlonlen-1)
    dy = (hsurfkey.latitudeOfLastGridPoint - hsurfkey.latitudeOfFirstGridPoint)/float(hsurfkey.totlatlen-1)

    del reghs

    if args.file:
        reg = dreg.DataRegistryFile(format, args.file)
    else:
        # Since we use only 1 partition, we can not use two consumers with the same group
        reg = dreg.DataRegistryStreaming("group2")

    reg.subscribe(topics)
    outDataPool = data.DataPool()
    outreg = dreg.OutputDataRegistryFile("ou_ncfile", outDataPool)
    while True:
        reg.poll(1.0)
        reqHandle = reg.complete()
        if reqHandle:
            reg.gatherField(reqHandle, tmpDatapool)
            for timestamp in tmpDatapool.data_:
                for fieldname in tmpDatapool[timestamp]:
                    key = tmpDatapool[timestamp][fieldname].metadata_
                    field = tmpDatapool[timestamp][fieldname].data_
                    dx_stag = (key.longitudeOfLastGridPoint - hsurfkey.longitudeOfLastGridPoint) / dx
                    dy_stag = (key.latitudeOfLastGridPoint - hsurfkey.latitudeOfLastGridPoint) / dy
                    xstag =math.isclose(dx_stag, 0.5, rel_tol=1e-5)
                    ystag = math.isclose(dy_stag, 0.5, rel_tol=1e-5)
                    if  xstag or ystag:
                        print("Field :",fieldname, " is staggered in (x,y):", xstag,",",ystag )
                        staggeredField = destagger(field, math.isclose(dx_stag, 0.5, rel_tol=1e-5), math.isclose(dy_stag, 0.5, rel_tol=1e-5))
                        outDataPool.insert(timestamp, fieldname, fieldop.field3d(staggeredField), key)
                    else:
                        outDataPool.insert(timestamp, fieldname, field, key)

            tmpDatapool.delete(timestamp)

            outreg.sendData()
