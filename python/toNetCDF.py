import time
import struct
import numpy as np
import string
import argparse
import time
import dataregistry as dreg
import dataregistryfile as freg
import math
import fieldop
import data
import grid_operator as go
import yaml


def outputProducts(configfile, verboseprint=lambda *a, **k: None):
    f = open(configfile, "r", encoding="utf-8")
    datad = yaml.load(f, Loader=yaml.Loader)
    f.close()

    if "inputfile" in datad and "kafkabroker" in datad:
        raise Exception("Only inputfile or kafkabroker option can be set")

    if "inputfile" in datad:
        reg = freg.DataRegistryFile(datad["inputfile"], verboseprint)
    else:
        kafkabroker = datad["kafkabroker"]
        verboseprint("Setting kafka broker :", kafkabroker)
        reg = dreg.DataRegistryStreaming(
            broker=kafkabroker, verboseprint=verboseprint)

    print("*******************")

    reg.loadData(configfile)
    print("*******************")

    tmpDatapool = data.DataPool()

    outreg = freg.OutputDataRegistryFile(
        "ou_ncfile", tmpDatapool, verboseprint=verboseprint, s3bucket=datad["s3bucket"])

    go.grid_operator()(go.identity(), reg, tmpDatapool, outreg=outreg, service=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='toNetCDF')
    parser.add_argument('-v', default=False, action='store_true')

    args = parser.parse_args()
    verboseprint = print if args.v else lambda *a, **k: None

    configfile = __file__.replace(".py", ".yaml")
    outputProducts(configfile, verboseprint=verboseprint)
