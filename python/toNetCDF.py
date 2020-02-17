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
        reg = dreg.DataRegistryFile(format, args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    reg.subscribe(["U", "V"])

    tmpDatapool = {}
    while True:
        reg.poll(1.0)
        if reg.complete():
            reg.gatherField(tmpDatapool)
            break

    reg = dreg.OutputDataRegistryFile("ou_ncfile.nc", tmpDatapool)
    reg.sendData()

