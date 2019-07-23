#pragma once
#include <cstddef>

struct KeyMessage {
  int myrank;
  float lon, lat;
  float dlon, dlat;
  size_t lonlen, latlen, levlen;
};
