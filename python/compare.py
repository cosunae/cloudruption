import time
import struct
import numpy as np
import string
import matplotlib.pyplot as plt
import argparse
import time
import dataregistry as dreg

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='consumer')
    parser.add_argument('-f', help='grib/netcdf filename')

    args = parser.parse_args()

    if args.f:
        reg = dreg.DataRegistryFile(args.f)
    else:
        reg = dreg.DataRegistryStreaming()

    reg.subscribe(["u", "v"])

    vert_prof = None


    outDatapool = {}
    while True:
        reg.poll(1.0)
        if reg.complete():
            print("COMPLETE")
            reg.gatherField(outDatapool)
            break

    if args.f:
        reg = dreg.OutputDataRegistryFile("ou_ncfile.nc", outDatapool)
        reg.sendData()
    else:
        print("Data streaming not supported yet")

