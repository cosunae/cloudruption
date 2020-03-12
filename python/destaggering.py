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
    return np.float32(0.5) * (a[-1, 0, 0] + a[1, 0, 0])


@stencil
def stencily(a):
    return np.float32(0.5) * (a[0, -1, 0] + a[0, 1, 0])


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

    def __call__(self, datapool: data.DataPool, timestamp, gbc):
        for fieldname in datapool[timestamp]:
            if fieldname == "T":
                print("Nont inser")
                continue
            key = datapool[timestamp][fieldname].datadesc_
            field = datapool[timestamp][fieldname].data_
            dx_stag = (key.longitudeOfLastGridPoint -
                       hsurfkey.longitudeOfLastGridPoint) / self.dx_
            dy_stag = (key.latitudeOfLastGridPoint -
                       hsurfkey.latitudeOfLastGridPoint) / self.dy_
            xstag = math.isclose(dx_stag, 0.5, rel_tol=1e-5)
            ystag = math.isclose(dy_stag, 0.5, rel_tol=1e-5)
            if xstag or ystag:
                print("Field :", fieldname,
                      " is staggered in (x,y):", xstag, ",", ystag)
                staggeredField = destagger(field, math.isclose(dx_stag, 0.5, rel_tol=1e-5),
                                           math.isclose(dy_stag, 0.5, rel_tol=1e-5))
                # Avoid garbage collector
                gbc[uuid.uuid1()] = staggeredField
                datapool.insert(timestamp, fieldname,
                                fieldop.field3d(staggeredField), key)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='destaggering')
    parser.add_argument('--file', help='grib/netcdf filename')

    args = parser.parse_args()

    if args.file:
        reghs = dreg.DataRegistryFile(args.file)
    else:
        reghs = dreg.DataRegistryStreaming()

    datapool = data.DataPool()

    reghs.loadData(__file__.replace(".py", ".yaml"), tag="masspointref")
    go.grid_operator()(go.identity(), reghs, datapool)
    hsurfkey = None
    for timestamp in datapool.data_:
        if "T" in datapool[timestamp]:
            hsurfkey = datapool[timestamp]["T"].datadesc_

    dx = (hsurfkey.longitudeOfLastGridPoint -
          hsurfkey.longitudeOfFirstGridPoint)/float(hsurfkey.lonlen-1)
    dy = (hsurfkey.latitudeOfLastGridPoint -
          hsurfkey.latitudeOfFirstGridPoint)/float(hsurfkey.latlen-1)

    del reghs

    outDatapool = data.DataPool()

    if args.file:
        reg = dreg.DataRegistryFile(args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    reg.loadData(__file__.replace(".py", ".yaml"), tag="default")

    outreg = dreg.OutputDataRegistryFile("ou_ncfile", outDatapool)

    go.grid_operator()(staggering_operator(dx, dy), reg,
                       outDatapool, outreg=outreg, service=True)
