#!/usr/bin/python3.7
import time
import struct
import numpy as np
import string
import argparse
import time
import dataregistry as dreg
import dataregistryfile as freg
from numba import jit, stencil
from typing import List
import math
import fieldop
import data
import uuid
import grid_operator as go
import yaml


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
            key = datapool[timestamp][fieldname].datadesc_
            # if not key.levlen == 1:
            #     continue
            field = datapool[timestamp][fieldname].data_
            dx_stag = (key.longitudeOfLastGridPoint -
                       hsurfkey.longitudeOfLastGridPoint) / self.dx_
            dy_stag = (key.latitudeOfLastGridPoint -
                       hsurfkey.latitudeOfLastGridPoint) / self.dy_
            xstag = math.isclose(dx_stag, 0.5, rel_tol=1e-5)
            ystag = math.isclose(dy_stag, 0.5, rel_tol=1e-5)
            if xstag or ystag:
                print("Field :", fieldname,
                      " is staggered in (x,y):", xstag, ",", ystag, key.levlen, np.array(field, copy=False).shape)
                staggeredField = destagger(field, math.isclose(dx_stag, 0.5, rel_tol=1e-5),
                                           math.isclose(dy_stag, 0.5, rel_tol=1e-5))

                print("result :", staggeredField.shape)
                # Avoid garbage collector
                gbc[uuid.uuid1()] = staggeredField
                datapool.insert(timestamp, fieldname,
                                fieldop.field3d(staggeredField), key)


def replace_conf(params):
    conffile = __file__.replace(".py", ".yaml")
    with open(conffile) as f:
        doc = yaml.load(f, Loader=yaml.FullLoader)

    for key, val in params.items():
        doc[key] = val

    with open(conffile, 'w') as f:
        yaml.dump(doc, f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='destaggering')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='grib/netcdf filename')
    group.add_argument('--kafkabroker', help='kafka broker url')

    parser.add_argument(
        '--product', help='the product that defines kafka topic prefix')
    parser.add_argument('--ofile', nargs=1, help='netcdf output filename')
    parser.add_argument('--oproduct', nargs=1, help='product of the output')
    parser.add_argument('-v', default=False, action='store_true')
    args = parser.parse_args()

    if args.product and not args.kafkabroker:
        raise Exception("product can only be defined when kafkabroker is set")

    if not args.kafkabroker and not args.ofile:
        raise Exception('An output mechanism must be specified')

    if not args.ofile and not args.oproduct:
        raise Exception(
            'In streaming mode, output product, --oproduct, must be specified')

    if args.product:
        replace_conf({"product": args.product})

    verboseprint=lambda *a, **k: None
    if args.v:
        verboseprint=print

    if args.file:
        reghs = freg.DataRegistryFile(args.file, verboseprint=verboseprint)
    else:
        reghs = dreg.DataRegistryStreaming(broker=args.kafkabroker, verboseprint=verboseprint)

    datapool = data.DataPool()

    reghs.loadData(__file__.replace(".py", ".yaml"), tag="masspointref")
    go.grid_operator()(go.identity(), reghs, datapool)
    hsurfkey = None
    for timestamp in datapool.data_:
        if "T" in datapool[timestamp]:
            hsurfkey = datapool[timestamp]["T"].datadesc_

    dx = (hsurfkey.longitudeOfLastGridPoint -
          hsurfkey.longitudeOfFirstGridPoint)/float(hsurfkey.totlonlen-1)
    dy = (hsurfkey.latitudeOfLastGridPoint -
          hsurfkey.latitudeOfFirstGridPoint)/float(hsurfkey.totlatlen-1)

    del reghs

    outDatapool = data.DataPool()

    if args.file:
        reg = freg.DataRegistryFile(args.file, verboseprint=verboseprint)
    else:
        reg = dreg.DataRegistryStreaming(broker=args.kafkabroker, verboseprint=verboseprint)

    reg.loadData(__file__.replace(".py", ".yaml"), tag="default")

    if args.ofile:
        outreg = freg.OutputDataRegistryFile(args.ofile[0], outDatapool)
    else:
        outreg = dreg.OutputDataRegistryStreaming(args.oproduct[0], outDatapool,
                                                  args.kafkabroker)

    go.grid_operator()(staggering_operator(dx, dy), reg,
                       outDatapool, outreg=outreg, service=True)
