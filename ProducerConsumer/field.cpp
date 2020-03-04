#include "field.h"
#include <assert.h>
#include <iostream>

BBox BBox::boundingBox(const BBox &other) const {
  return BBox{
      {std::array<size_t, 2>{std::min(limits_[0][0], other.limits_[0][0]),
                             std::max(limits_[0][1], other.limits_[0][1])},
       std::array<size_t, 2>{std::min(limits_[1][0], other.limits_[1][0]),
                             std::max(limits_[1][1], other.limits_[1][1])},
       std::array<size_t, 2>{std::min(limits_[2][0], other.limits_[2][0]),
                             std::max(limits_[2][1], other.limits_[2][1])}}};
}

float &field3d::operator()(int i, int j, int k) {
  if (i * m_strides[0] + j * m_strides[1] + k * m_strides[2] >=
          m_i * m_j * m_k ||
      i < 0 || j < 0 || k < 0) {
    std::cout << "RRRRRRERROR i:" << i << " j:" << j << " k: " << k
              << "m_i:" << m_i << " m_j:" << m_j << " m_k: " << m_k
              << std::endl;
    std::cout << "strides " << m_strides[0] << "," << m_strides[1] << ","
              << m_strides[2] << std::endl;
  }
  assert((i * m_strides[0] + j * m_strides[1] + k * m_strides[2] <
          m_i * m_j * m_k) &&
         i >= 0 && j >= 0 && k >= 0);
  return data_[i * m_strides[0] + j * m_strides[1] + k * m_strides[2]];
}
float field3d::operator()(int i, int j, int k) const {
  return data_[i * m_strides[0] + j * m_strides[1] + k * m_strides[2]];
}

float &field2d::operator()(int i, int j) {
  if (i * m_strides[0] + j * m_strides[1] >= m_i * m_j)
    std::cout << "RRRRRRERROR i:" << i << " j:" << j << "m_i:" << m_i
              << " m_j:" << m_j << std::endl;

  return m_data[i * m_strides[0] + j * m_strides[1]];
}

float field2d::operator()(int i, int j) const {
  if (i * m_strides[0] + j * m_strides[1] >= m_i * m_j)
    std::cout << "RRRRRRERROR i:" << i << " j:" << j << "m_i:" << m_i
              << " m_j:" << m_j << std::endl;

  return m_data[i * m_strides[0] + j * m_strides[1]];
}
