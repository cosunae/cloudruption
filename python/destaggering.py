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

    args = parser.parse_args()
    format = args.format
    if not format:
        format="grib"

    if format not in ("grib", "nc"):
        print("invalid file format")
        sys.exit(1)

    if args.file:
        reghs = dreg.DataRegistryFile(format, args.file)
    else:
        reghs = dreg.DataRegistryStreaming()

    tmpDatapool = {}

    reghs.subscribe(["HSURF"])
    reghs.wait()
    reghs.gatherField(tmpDatapool)

    hsurfkey = reghs.dataRequests_["HSURF"].msgKey_

    dx = (hsurfkey.longitudeOfLastGridPoint - hsurfkey.longitudeOfFirstGridPoint)/float(hsurfkey.totlonlen-1)
    dy = (hsurfkey.latitudeOfLastGridPoint - hsurfkey.latitudeOfFirstGridPoint)/float(hsurfkey.totlatlen-1)

    if args.file:
        reg = dreg.DataRegistryFile(format, args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    reg.subscribe(["all"])

    modNpField = {}
    while True:
        reg.poll(1.0)
        if reg.complete():

            reg.gatherField(tmpDatapool)
            for field in tmpDatapool:

                key = reg.dataRequests_[field].msgKey_
                dx_stag = (key.longitudeOfLastGridPoint - hsurfkey.longitudeOfLastGridPoint) / dx
                dy_stag = (key.latitudeOfLastGridPoint - hsurfkey.latitudeOfLastGridPoint) / dy
                if math.isclose(dx_stag, 0.5, rel_tol=1e-5) or math.isclose(dy_stag, 0.5, rel_tol=1e-5):
                    modNpField[field] = destagger(tmpDatapool[field], math.isclose(dx_stag, 0.5, rel_tol=1e-5), math.isclose(dy_stag, 0.5, rel_tol=1e-5))
            break

    for afield in modNpField:
        tmpDatapool[afield] = fieldop.field3d(modNpField[afield])
    reg = dreg.OutputDataRegistryFile("ou_ncfile.nc", tmpDatapool)
    reg.sendData()
