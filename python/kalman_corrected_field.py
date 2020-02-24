import data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='kalman_corrected_field')
    parser.add_argument('--file', required=True, help='grib/netcdf filename')

    args = parser.parse_args()

    if args.file:
        reg = dreg.DataRegistryFile(args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    reg.loadData(__file__.replace(".py",".yaml"))

#    tmpDatapool = data.DataPool()
#    outreg = dreg.OutputDataRegistryFile("ou_ncfile", tmpDatapool)

#    go.grid_operator()(filter_operator(), reg, tmpDatapool, outreg=outreg, service=True)

