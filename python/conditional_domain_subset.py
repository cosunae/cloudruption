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
from values import undef, pc_b1, pc_b2w, pc_b3, pc_b4w, pc_rdv, pc_g, pc_r_d, pc_o_rdv
import math
import fieldop

#@jit(nopython=True, parallel=True)
def f_pv_sw(t: np.ndarray):
    return pc_b1 * np.exp( pc_b2w*(t  - pc_b3)/(t  - pc_b4w) )

#clip is not yet supported
#@jit(nopython=True, parallel=True)
def f_qv_pvp(pv: np.ndarray, p: np.ndarray):
    return pc_rdv * pv / np.clip((p - pc_o_rdv*pv), 1.0, None)

#clip is not yet supported
#@jit(nopython=True, parallel=True)
def relhum(qv: np.ndarray, p: np.ndarray, t: np.ndarray):
    max_rh = 100
    return np.clip(np.clip(100. * qv / f_qv_pvp(f_pv_sw(t), p * np.exp(-(2.*pc_g)/pc_r_d/t)), 0, None), None, max_rh)

def filter_t_nojit(t: np.ndarray, x: List[np.ndarray]):
    for tr in x:
        np.ma.masked_where( ((t > 233.15) & (t > 273.15)), tr)

@jit(nopython=True, parallel=True)
def filter_t(t: np.ndarray, x: List[np.ndarray]):
    for tr in x:
        for i in range(t.shape[0]):
            for j in range(t.shape[1]):
                for k in range(t.shape[2]):
                    if not (t[i,j,k] > 233.15 and t[i,j,k] < 273.15):
                        tr[i,j,k] = undef
                    if not (t[i,j,k] > 233.15 and t[i,j,k] < 273.15):
                        t[i,j,k] = undef

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

    reg.subscribe(["q","qc","qi", "pp", "t" ])

    tmpDatapool = {}
    while True:
        reg.poll(1.0)
        if reg.complete():
            print("COMPLETE")
            reg.gatherField(tmpDatapool)

            qv = np.array(tmpDatapool['q'], copy=False)
            qc = np.array(tmpDatapool['qc'], copy=False)
            qi = np.array(tmpDatapool['qi'], copy=False)
            t = np.array(tmpDatapool['t'], copy=False)

            pp = np.array(tmpDatapool['pp'], copy=False)

            # DO NOT REPORT THIS... COMPILATION TIME IS INCLUDED IN THE EXECUTION TIME!
            start = time.time()
            filter_t(t,[qv,qc, qi])
#            relhum(qv, pp, t)
            end = time.time()
            print("Elapsed (with compilation) = %s" % (end - start))

            # NOW THE FUNCTION IS COMPILED, RE-TIME IT EXECUTING FROM CACHE
            start = time.time()
            filter_t_nojit(t,[qv,qc, qi])
#            relh = relhum(qv, pp, t)
#            tmpDatapool["relhum"] = fieldop.field3d(relh)

            end = time.time()
            print("Elapsed (after compilation) = %s" % (end - start))

            break

    if args.file:
        reg = dreg.OutputDataRegistryFile("ou_ncfile.nc", tmpDatapool)
        reg.sendData()
    else:
        print("Data streaming not supported yet")

