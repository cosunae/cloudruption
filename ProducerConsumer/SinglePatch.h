#pragma once
#include "field.h"
#include <array>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <string.h>

class SinglePatch : public field2d
{
public:
  SinglePatch(size_t ilonstart, size_t jlatstart, size_t lonlen, size_t latlen,
              size_t lev, float *data)
      : bbox_{{std::array<size_t, 2>{{ilonstart, ilonstart + lonlen - 1}},
               std::array<size_t, 2>{{jlatstart, jlatstart + latlen - 1}},
               std::array<size_t, 2>{{lev, lev}}}},
        field2d(lonlen, latlen)
  {
    // TODO this will create copies all the time, even from python
    memcpy(field2d::data(), data, lonlen * latlen * sizeof(float));
  }
  // TODO fix this
  //  ~SinglePatch() { free(data_); }

  size_t ilonStart() const { return bbox_.limits_[0][0]; }
  size_t jlatStart() const { return bbox_.limits_[1][0]; }
  size_t lonlen() const { return isize(); }
  size_t latlen() const { return jsize(); }
  size_t lev() const { return bbox_.limits_[2][0]; }
  const BBox &bbox() const { return bbox_; }

private:
  BBox bbox_;
};
