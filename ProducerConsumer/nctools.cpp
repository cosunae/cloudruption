#include "nctools.h"
#include <iostream>
#include <netcdf.h>

/* Handle errors by printing an error message and exiting with a
 * non-zero status. */
#define ERR(e)                                                                 \
  {                                                                            \
    printf("Error: %s\n", nc_strerror(e));                                     \
    ierror = e;                                                                \
  }

void NetCDFDumper::closeFile(std::string filename, std::string topic) {
  auto ncid = filenameToNCID_.at(filename);
  auto &regTopics = *(ncidToRegTopics_.at(ncid));
  regTopics.topicCount_[topic] = false;

  if (regTopics.fileClosed)
    return;

  if (regTopics.topicCount_.size() != topics_.size())
    return;

  for (auto topicCount : regTopics.topicCount_) {
    if (topicCount.second)
      return;
  }

  nc_close(ncid);
  regTopics.fileClosed = true;
}

void NetCDFDumper::createFile(std::string filename, const Field &field) {
  int retval;
  int ncid = -1;
  std::array<int, 3> dims{-1, -1, -1};

  const auto fieldProp = field.fieldProp_;

  int ierror = 0;
  if (filenameToNCID_.count(filename)) {
    ncid = filenameToNCID_.at(filename);
    dims = ncidToDims_.at(ncid);
    topicToNCID_[field.variableName_] = ncid;
  } else {

    if ((retval = nc_create(filename.c_str(), NC_WRITE | NC_NETCDF4, &ncid)))
      ERR(retval);

    if ((retval =
             nc_def_dim(ncid, "longitude", fieldProp.sizes_[0], &(dims[2]))))
      ERR(retval);

    if ((retval =
             nc_def_dim(ncid, "latitude", fieldProp.sizes_[1], &(dims[1]))))
      ERR(retval);

    if ((retval = nc_def_dim(ncid, "level", fieldProp.sizes_[2], &(dims[0]))))
      ERR(retval);
    ncidToDims_[ncid] = dims;

    topicToNCID_[field.variableName_] = ncid;
    filenameToNCID_[filename] = ncid;
  }

  if (!topicToVarID_.count(field.variableName_)) {
    std::vector<int> idims(dims.begin(), dims.end());
    int varid;
    if ((retval = nc_def_var(ncid, field.variableName_.c_str(), NC_FLOAT, 3,
                             &(idims[0]), &varid)))
      ERR(retval);

    topicToVarID_[field.variableName_] = varid;
    if (!ncidToRegTopics_.count(ncid)) {
      ncidToRegTopics_.emplace(
          std::make_pair(ncid, std::make_unique<RegisteredTopics>()));
    }
    auto &regTopics = *(ncidToRegTopics_.at(ncid));

    regTopics.topicCount_[field.variableName_] = true;
  }
  if (ierror) {
    throw std::runtime_error("Error constructing netcdf file:" + filename);
  }
}

void NetCDFDumper::writeVar(std::string variableName, float *f) {
  int retval = 0;
  int ierror = 0;

  if (!topicToNCID_.count(variableName)) {
    throw std::runtime_error(
        "Attempt to write netcdf var in a file that was not created yet due to "
        "lack of init message from producer");
  }
  int ncid = topicToNCID_.at(variableName);
  int varid = topicToVarID_.at(variableName);

  if ((retval = nc_put_var_float(ncid, varid, f)))
    ERR(retval);
}
