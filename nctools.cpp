#include "nctools.h"
#include <iostream>
#include <netcdf.h>

/* Handle errors by printing an error message and exiting with a
 * non-zero status. */
#define ERR(e)                                                                 \
  {                                                                            \
    printf("Error: %s\n", nc_strerror(e));                                     \
    return 2;                                                                  \
  }

int netcdfDump(int mpirank, float *f, const FieldProp &fieldProp,
               std::string output) {

  std::string filename = output + std::to_string(mpirank) + ".nc";
  int retval, ncid;
  if ((retval = nc_create(filename.c_str(), NC_WRITE | NC_NETCDF4, &ncid)))
    ERR(retval);

  int dims[3];
  if ((retval = nc_def_dim(ncid, "longitude", fieldProp.sizes_[0], &(dims[2]))))
    ERR(retval);

  if ((retval = nc_def_dim(ncid, "latitude", fieldProp.sizes_[1], &(dims[1]))))
    ERR(retval);

  if ((retval = nc_def_dim(ncid, "level", fieldProp.sizes_[2], &(dims[0]))))
    ERR(retval);

  int uid;
  if ((retval = nc_def_var(ncid, "u", NC_FLOAT, 3, dims, &uid)))
    ERR(retval);

  if ((retval = nc_put_var_float(ncid, uid, f)))
    ERR(retval);

  if ((retval = nc_close(ncid)))
    ERR(retval);

  std::cout << "******************* writing file " << filename
            << " *****************" << std::endl;

  return 0;
}
