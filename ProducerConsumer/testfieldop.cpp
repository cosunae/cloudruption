#include "DistributedField.h"
#include <array>
#include <iostream>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>

using namespace pybind11::literals;

class TestFieldOp {
  field3d field_;

public:
  TestFieldOp(field3d &field) : field_(field) {}

  void compute() {
    for (size_t i = 0; i < field_.isize(); ++i) {
      for (size_t j = 0; j < field_.jsize(); ++j) {
        for (size_t k = 0; k < field_.ksize(); ++k) {
          field_(i, j, k) = i + j * 10 + k * 100;
        }
      }
    }
  }
};

PYBIND11_MODULE(testfieldop, m) {
  pybind11::class_<TestFieldOp>(m, "TestFieldOp")
      .def(pybind11::init<field3d &>())
      .def("compute", &TestFieldOp::compute);
}
