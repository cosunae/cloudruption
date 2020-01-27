#include "DistributedField.h"
#include <array>
#include <iostream>
#include <pybind11/pybind11.h>
#include <string>

using namespace pybind11::literals;

PYBIND11_MODULE(config, m) { pybind11::class_<DomainConf>(m, "DomainConf"); }

PYBIND11_MODULE(fieldop, m) {
  pybind11::class_<DomainConf>(m, "DomainConf")
      .def(pybind11::init<int, int, int, int, int>())
      .def_readwrite("isize", &DomainConf::isize)
      .def_readwrite("jsize", &DomainConf::jsize)
      .def_readwrite("levels", &DomainConf::levels)
      .def_readwrite("istart", &DomainConf::istart)
      .def_readwrite("jstart", &DomainConf::jstart);

  pybind11::class_<DistributedField>(m, "DistributedField",
                                     pybind11::buffer_protocol())
      .def(pybind11::init<const std::string &, const DomainConf &,
                          unsigned long int>())
      .def("insertPatch", (void (DistributedField::*)(SinglePatch &)) &
                              DistributedField::insertPatch)
      .def("gatherField", &DistributedField::gatherField);

  pybind11::class_<field2d>(m, "field2d", pybind11::buffer_protocol())
      /// Construct from a buffer
      .def(pybind11::init([](pybind11::buffer const b) {
        pybind11::buffer_info info = b.request();
        if (info.format != pybind11::format_descriptor<float>::format() ||
            info.ndim != 2)
          throw std::runtime_error("Incompatible buffer format!");

        //        auto strides = std::array<size_t, 2>({1, info.shape[1]});
        //            {(size_t)info.strides[1], (size_t)info.strides[0]});

        std::cout << "elem  " << info.shape[0] << " --- " << info.shape[1]
                  << " --- " << info.strides[1] << " oo " << info.strides[0]
                  << std::endl;
        return field2d(info.shape[0], info.shape[1], (float *)info.ptr);
      }))
      .def("__getitem__", [](const field2d &m, std::pair<ssize_t, ssize_t> i) {
        if (i.first >= m.isize() || i.second >= m.jsize())
          throw pybind11::index_error();
        return m(i.first, i.second);
      });

  pybind11::class_<field3d>(m, "field3d", pybind11::buffer_protocol())
      /// Construct from a buffer
      .def(pybind11::init([](pybind11::buffer const b) {
        pybind11::buffer_info info = b.request();
        if (info.format != pybind11::format_descriptor<float>::format() ||
            info.ndim != 3)
          throw std::runtime_error("Incompatible buffer format!");

        return field3d(info.shape[0], info.shape[1], info.shape[2],
                       (float *)info.ptr);
      }))
      .def("__getitem__", [](const field3d &m, std::array<ssize_t, 3> i) {
        if (i[0] >= m.isize() || i[1] >= m.jsize() || i[2] >= m.ksize())
          throw pybind11::index_error();
        return m(i[0], i[1], i[2]);
      });

  pybind11::class_<SinglePatch>(m, "SinglePatch", pybind11::buffer_protocol())
      /// Construct from a buffer
      .def(pybind11::init([](size_t ilonstart, size_t jlatstart, size_t lonlen,
                             size_t latlen, size_t lev,
                             pybind11::buffer const b) {
             pybind11::buffer_info info = b.request();
             if (info.format != pybind11::format_descriptor<float>::format() ||
                 info.ndim != 2)
               throw std::runtime_error("Incompatible buffer format!");

             return SinglePatch(ilonstart, jlatstart, lonlen, latlen, lev,
                                (float *)info.ptr);
           }),
           "ilonstart"_a, "jlatstart"_a, "lonlen"_a, "latlen"_a, "lev"_a,
           "ptr"_a)
      .def("ilonstart", &SinglePatch::ilonStart)
      .def("jlatstart", &SinglePatch::jlatStart)
      .def("lonlen", &SinglePatch::lonlen)
      .def("latlen", &SinglePatch::latlen)
      .def("lev", &SinglePatch::lev)
      .def("__getitem__",
           [](const SinglePatch &m, std::pair<ssize_t, ssize_t> i) {
             if (i.first >= m.isize() || i.second >= m.jsize())
               throw pybind11::index_error();
             return m(i.first, i.second);
           });
}
