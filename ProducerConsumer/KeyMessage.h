#pragma once
#include <cstddef>
#include <string>

enum ActionType { HeaderData, Data, EndData };

struct KeyMessage {
  int actionType_;
  char key[32];
  int npatches;
  int myrank;
  size_t datetime;
  size_t ilon_start, jlat_start, lev;
  size_t lonlen, latlen, levlen;
  size_t totlonlen, totlatlen;
  float longitudeOfFirstGridPoint, longitudeOfLastGridPoint,
      latitudeOfFirstGridPoint, latitudeOfLastGridPoint;
};

struct TopicHeader {
  char filename[256];
};
