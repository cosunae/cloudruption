#include <cstddef>

struct DataReqDesc {
  double longitudeOfFirstGridPoint, longitudeOfLastGridPoint,
      latitudeOfFirstGridPoint, latitudeOfLastGridPoint;
};

struct DataDesc : public DataReqDesc {
  size_t datetime, ilonstart, jlatstart, levelstart, totlonlen, totlatlen,
      levlen;
};
