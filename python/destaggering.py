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
import uuid
import grid_operator as go

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

class staggering_operator:
    def __init__(self, dx, dy):
        self.dx_ = dx
        self.dy_ = dy

    def __call__(self, datapool: data.DataPool, timestamp, gbc ):
        for fieldname in tmpDatapool[timestamp]:
            key = datapool[timestamp][fieldname].metadata_
            field = datapool[timestamp][fieldname].data_
            dx_stag = (key.longitudeOfLastGridPoint - hsurfkey.longitudeOfLastGridPoint) / self.dx_
            dy_stag = (key.latitudeOfLastGridPoint - hsurfkey.latitudeOfLastGridPoint) / self.dy_
            xstag = math.isclose(dx_stag, 0.5, rel_tol=1e-5)
            ystag = math.isclose(dy_stag, 0.5, rel_tol=1e-5)
            if xstag or ystag:
                print("Field :", fieldname, " is staggered in (x,y):", xstag, ",", ystag)
                staggeredField = destagger(field, math.isclose(dx_stag, 0.5, rel_tol=1e-5),
                                   math.isclose(dy_stag, 0.5, rel_tol=1e-5))
                ## Avoid garbage collector
                gbc[uuid.uuid1()] = staggeredField
                datapool.insert(timestamp, fieldname, fieldop.field3d(staggeredField), key)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='consumer')
    parser.add_argument('--file', help='grib/netcdf filename')
    parser.add_argument('--topics', help='comma separated list of topics to subscribe')

    args = parser.parse_args()

    if args.file:
        reghs = dreg.DataRegistryFile(args.file)
    else:
        reghs = dreg.DataRegistryStreaming()

    tmpDatapool = data.DataPool()

    reghs.loadData(__file__.replace(".py",".yaml"), tag="masspointref")
    go.grid_operator()(go.identity(), reghs, tmpDatapool)
    hsurfkey = None
    for timestamp in tmpDatapool.data_:
        if "T" in tmpDatapool[timestamp]:
            hsurfkey = tmpDatapool[timestamp]["T"].metadata_

    dx = (hsurfkey.longitudeOfLastGridPoint - hsurfkey.longitudeOfFirstGridPoint)/float(hsurfkey.totlonlen-1)
    dy = (hsurfkey.latitudeOfLastGridPoint - hsurfkey.latitudeOfFirstGridPoint)/float(hsurfkey.totlatlen-1)

    del reghs

    if args.file:
        reg = dreg.DataRegistryFile(args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    if args.topics:
        reg.subscribe(args.topics)
    else:
        reg.loadData(__file__.replace(".py",".yaml"), tag="default")

    outreg = dreg.OutputDataRegistryFile("ou_ncfile", tmpDatapool)

    go.grid_operator()(staggering_operator(dx, dy), reg, tmpDatapool, outreg=outreg, service=True)

