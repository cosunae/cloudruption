#pragma once
#include <array>

struct BBox {
  std::array<std::array<size_t, 2>, 3> limits_;
  BBox boundingBox(const BBox &other) const;

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

  float &operator()(int i, int j, int k);
  float operator()(int i, int j, int k) const;
  float *data() { return data_; }
  size_t isize() const { return m_i; }
  size_t jsize() const { return m_j; }
  size_t ksize() const { return m_k; }
  size_t size() const { return m_i * m_j * m_k; }
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

  float &operator()(int i, int j);
  float operator()(int i, int j) const;
  float *data() const { return m_data; }
  size_t isize() const { return m_i; }
  size_t jsize() const { return m_j; }
  std::array<size_t, 2> strides() const { return m_strides; }
};
