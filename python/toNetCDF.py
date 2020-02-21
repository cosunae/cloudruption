import time
import struct
import numpy as np
import string
import matplotlib.pyplot as plt
import argparse
import time
import dataregistry as dreg
from numba import jit
from typing import List
import math
import fieldop
import data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='consumer')
    parser.add_argument('--file', help='grib/netcdf filename')
    parser.add_argument('--format', help='grib or nc')
    parser.add_argument('--topics', help='comma separated list of topics to subscribe')

    args = parser.parse_args()
    format = args.format
    if not format:
        format="grib"

    if format not in ("grib", "nc"):
        print("invalid file format")
        sys.exit(1)

    if args.file:
        reg = dreg.DataRegistryFile(format, args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    if args.topics:
        reg.subscribe(args.topics.split(','))
    else:
        reg.subscribe(['^.*'])

    tmpDatapool = data.DataPool()

    outreg = dreg.OutputDataRegistryFile("ou_ncfile", tmpDatapool)

    while True:
        reg.poll(1.0)
        reqHandle = reg.complete()
        if reqHandle:
            reg.gatherField(reqHandle, tmpDatapool)
            outreg.sendData()


