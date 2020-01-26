#pragma once
#include <array>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <string.h>

class field3d {
  std::array<size_t, 3> m_strides;
  size_t m_i, m_j, m_k;
  float *data_;

public:
  field3d(size_t i, size_t j, size_t k)
      : m_i(i), m_j(j), m_k(k), m_strides({i * j * k, k, k * j}) {
    data_ = static_cast<float *>(malloc(i * j * k * sizeof(float)));
  }
  field3d(size_t i, size_t j, size_t k, float *data)
      : m_i(i), m_j(j), m_k(k), m_strides({i * j * k, k, k * j}) {
    data_ = data;
  }

  field3d(size_t i, size_t j, size_t k, std::array<size_t, 3> strides)
      : m_i(i), m_j(j), m_k(k), m_strides(strides) {
    data_ = static_cast<float *>(malloc(i * j * k * sizeof(float)));
  }

  float &operator()(int i, int j, int k) {
    if (k + j * m_strides[1] + i * m_strides[2] >= m_i * m_j * m_k) {
      std::cout << "RRRRRRERROR i:" << i << " j:" << j << " k: " << k
                << "m_i:" << m_i << " m_j:" << m_j << " m_k: " << m_k
                << std::endl;
      std::cout << "strides " << m_strides[1] << " " << m_strides[2]
                << std::endl;
    }
    return data_[k + j * m_strides[1] + i * m_strides[2]];
  }
  float operator()(int i, int j, int k) const {
    return data_[k + j * m_strides[1] + i * m_strides[2]];
  }
  float *data() { return data_; }
  size_t isize() const { return m_i; }
  size_t jsize() const { return m_j; }
  size_t ksize() const { return m_k; }
};

class field2d {
  std::array<size_t, 2> m_strides;
  size_t m_i, m_j;
  float *m_data;

public:
  field2d(size_t i, size_t j) : m_i(i), m_j(j), m_strides({i * j, j}) {
    m_data = static_cast<float *>(malloc(i * j * sizeof(float)));
  }
  field2d(size_t i, size_t j, float *data)
      : m_i(i), m_j(j), m_strides({i * j, j}), m_data(data) {}
  field2d(size_t i, size_t j, std::array<size_t, 2> strides)
      : m_i(i), m_j(j), m_strides(strides) {
    m_data = static_cast<float *>(malloc(i * j * sizeof(float)));
  }

  float &operator()(int i, int j) { return m_data[j + i * m_strides[1]]; }
  float operator()(int i, int j) const { return m_data[j + i * m_strides[1]]; }
  float *data() { return m_data; }
  size_t isize() const { return m_i; }
  size_t jsize() const { return m_j; }
};

class SinglePatch : public field2d {
public:
  SinglePatch(size_t ilonstart, size_t jlatstart, size_t lonlen, size_t latlen,
              size_t lev, float *data)
      : ilonstart_(ilonstart), jlatstart_(jlatstart), lev_(lev),
        field2d(lonlen, latlen) {
    // TODO this will create copies all the time, even from python
    memcpy(field2d::data(), data, lonlen * latlen * sizeof(float));
  }
  // TODO fix this
  //  ~SinglePatch() { free(data_); }

  size_t ilonStart() { return ilonstart_; }
  size_t jlatStart() { return jlatstart_; }
  size_t lonlen() { return isize(); }
  size_t latlen() { return jsize(); }
  size_t lev() { return lev_; }

private:
  size_t ilonstart_, jlatstart_;
  size_t lev_;
};
