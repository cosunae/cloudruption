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
    parser.add_argument('--file', required=True, help='grib/netcdf filename')
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

    reg.subscribe(["u", "v"])

    vert_prof = None


    tmpDatapool = {}
    while True:
        reg.poll(1.0)
        if reg.complete():
            print("COMPLETE")
            reg.gatherField(tmpDatapool)
            break

    if args.file:
        reg = dreg.OutputDataRegistryFile("ou_ncfile.nc", tmpDatapool)
        reg.sendData()
    else:
        print("Data streaming not supported yet")

