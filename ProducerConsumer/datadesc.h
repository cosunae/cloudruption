#pragma once
#include <cstddef>

// frame in radian coordinates and indices of the compute domain
// for the user request of the data
struct DataReqDesc {
  double longitudeOfFirstGridPoint, longitudeOfLastGridPoint,
      latitudeOfFirstGridPoint, latitudeOfLastGridPoint;
  size_t ifirst, ilast, jfirst, jlast;
};

// DataDesc contains sizes of the full field (not only the requested area)
struct DataDesc : public DataReqDesc {
  size_t datetime, ilonstart, jlatstart, levelstart, totlonlen, totlatlen,
      levlen;
};
