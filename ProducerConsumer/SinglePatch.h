#pragma once
#include <array>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <string.h>

struct BBox {
  std::array<std::array<size_t, 2>, 3> limits_;
  BBox boundingBox(const BBox &other) const {
    return BBox{
        {std::array<size_t, 2>{std::min(limits_[0][0], other.limits_[0][0]),
                               std::max(limits_[0][1], other.limits_[0][1])},
         std::array<size_t, 2>{std::min(limits_[1][0], other.limits_[1][0]),
                               std::max(limits_[1][1], other.limits_[1][1])},
         std::array<size_t, 2>{std::min(limits_[2][0], other.limits_[2][0]),
                               std::max(limits_[2][1], other.limits_[2][1])}}};
  }
  friend std::ostream &operator<<(std::ostream &os, const BBox &);
};

class field3d {
  std::array<size_t, 3> m_strides;
  size_t m_i, m_j, m_k;
  float *data_;

public:
  field3d(const BBox &bbox)
      : field3d((bbox.limits_[0][1] - bbox.limits_[0][0] + 1),
                (bbox.limits_[1][1] - bbox.limits_[1][0] + 1),
                (bbox.limits_[2][1] - bbox.limits_[2][0] + 1)) {}

  field3d(size_t i, size_t j, size_t k)
      : m_i(i), m_j(j), m_k(k), m_strides({1, i, i * j}) {
    data_ = static_cast<float *>(malloc(i * j * k * sizeof(float)));
  }

  field3d(size_t i, size_t j, size_t k, std::array<size_t, 3> strides,
          float *data)
      : m_i(i), m_j(j), m_k(k), m_strides(strides), data_(data) {}

  float &operator()(int i, int j, int k) {
    if (i * m_strides[0] + j * m_strides[1] + k * m_strides[2] >=
        m_i * m_j * m_k) {
      std::cout << "RRRRRRERROR i:" << i << " j:" << j << " k: " << k
                << "m_i:" << m_i << " m_j:" << m_j << " m_k: " << m_k
                << std::endl;
      std::cout << "strides " << m_strides[0] << "," << m_strides[1] << ","
                << m_strides[2] << std::endl;
    }
    return data_[i * m_strides[0] + j * m_strides[1] + k * m_strides[2]];
  }
  float operator()(int i, int j, int k) const {
    return data_[i * m_strides[0] + j * m_strides[1] + k * m_strides[2]];
  }
  float *data() { return data_; }
  size_t isize() const { return m_i; }
  size_t jsize() const { return m_j; }
  size_t ksize() const { return m_k; }
  std::array<size_t, 3> strides() const { return m_strides; }
};

class field2d {
  std::array<size_t, 2> m_strides;
  size_t m_i, m_j;
  float *m_data;

public:
  field2d(size_t i, size_t j) : m_i(i), m_j(j), m_strides({1, i}) {
    m_data = static_cast<float *>(malloc(i * j * sizeof(float)));
  }
  field2d(size_t i, size_t j, std::array<size_t, 2> strides, float *data)
      : m_i(i), m_j(j), m_strides(strides), m_data(data) {}
  field2d(size_t i, size_t j, std::array<size_t, 2> strides)
      : m_i(i), m_j(j), m_strides(strides) {
    m_data = static_cast<float *>(malloc(i * j * sizeof(float)));
  }

  float &operator()(int i, int j) {
    if (i * m_strides[0] + j * m_strides[1] >= m_i * m_j)
      std::cout << "RRRRRRERROR i:" << i << " j:" << j << "m_i:" << m_i
                << " m_j:" << m_j << std::endl;

    return m_data[i * m_strides[0] + j * m_strides[1]];
  }
  float operator()(int i, int j) const {
    if (i * m_strides[0] + j * m_strides[1] >= m_i * m_j)
      std::cout << "RRRRRRERROR i:" << i << " j:" << j << "m_i:" << m_i
                << " m_j:" << m_j << std::endl;

    return m_data[i * m_strides[0] + j * m_strides[1]];
  }
  float *data() const { return m_data; }
  size_t isize() const { return m_i; }
  size_t jsize() const { return m_j; }
  std::array<size_t, 2> strides() const { return m_strides; }
};

class SinglePatch : public field2d {
public:
  SinglePatch(size_t ilonstart, size_t jlatstart, size_t lonlen, size_t latlen,
              size_t lev, float *data)
      : bbox_{{std::array<size_t, 2>{{ilonstart, ilonstart + lonlen - 1}},
               std::array<size_t, 2>{{jlatstart, jlatstart + latlen - 1}},
               std::array<size_t, 2>{{lev, lev}}}},
        field2d(lonlen, latlen) {
    // TODO this will create copies all the time, even from python
    memcpy(field2d::data(), data, lonlen * latlen * sizeof(float));
  }
  // TODO fix this
  //  ~SinglePatch() { free(data_); }

  size_t ilonStart() { return bbox_.limits_[0][0]; }
  size_t jlatStart() { return bbox_.limits_[1][0]; }
  size_t lonlen() { return isize(); }
  size_t latlen() { return jsize(); }
  size_t lev() { return bbox_.limits_[2][0]; }
  const BBox &bbox() const { return bbox_; }

private:
  BBox bbox_;
};
