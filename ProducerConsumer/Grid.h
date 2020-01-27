#pragma once

#include <cstddef>

struct GridConf {
  size_t lonlen, latlen, levlen;
  size_t nbx = -1;
  size_t nby = -1;
  size_t isizepatch, jsizepatch;
  void print();
};

struct DomainConf {
  size_t isize, jsize, levels, istart, jstart;
};
