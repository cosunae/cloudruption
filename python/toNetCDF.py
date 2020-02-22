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
import grid_operator as go

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='consumer')
    parser.add_argument('--file', help='grib/netcdf filename')
    parser.add_argument('--topics', help='comma separated list of topics to subscribe')

    args = parser.parse_args()
    if args.file:
        reg = dreg.DataRegistryFile(args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    if args.topics:
        reg.subscribe(args.topics.split(','))
    else:
        reg.subscribe(['^.*'])

    tmpDatapool = data.DataPool()

    outreg = dreg.OutputDataRegistryFile("ou_ncfile", tmpDatapool)

    go.grid_operator()(go.identity(), reg, tmpDatapool, outreg=outreg, service=True)

