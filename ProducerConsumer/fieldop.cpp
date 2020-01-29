#include "DistributedField.h"
#include <array>
#include <iostream>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>

using namespace pybind11::literals;

PYBIND11_MODULE(config, m) { pybind11::class_<DomainConf>(m, "DomainConf"); }

PYBIND11_MODULE(fieldop, m) {
  pybind11::class_<DomainConf>(m, "DomainConf")
      .def(pybind11::init<int, int, int>())
      .def_readwrite("isize", &DomainConf::isize)
      .def_readwrite("jsize", &DomainConf::jsize)
      .def_readwrite("levels", &DomainConf::levels);

  pybind11::class_<BBox>(m, "BBox").def_readwrite("limits_", &BBox::limits_);

  pybind11::class_<DistributedField>(m, "DistributedField",
                                     pybind11::buffer_protocol())
      .def(pybind11::init<const std::string &, const DomainConf &,
                          unsigned long int>())
      .def("insertPatch", (void (DistributedField::*)(SinglePatch &)) &
                              DistributedField::insertPatch)
      .def("gatherField", &DistributedField::gatherField)
      .def("bboxPatches", &DistributedField::bboxPatches);

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
      .def("__getitem__",
           [](const field2d &m, std::pair<ssize_t, ssize_t> i) {
             if (i.first >= m.isize() || i.second >= m.jsize())
               throw pybind11::index_error();
             return m(i.first, i.second);
           })
      .def_buffer([](field2d &m) -> pybind11::buffer_info {
        return pybind11::buffer_info(
            m.data(), /*Pointer to buffer*/ sizeof(float),
            /*Size of one scalar*/ pybind11::format_descriptor<float>::format(),
            /*Python struct-style format˓→descriptor*/ 2,
            /*Number of dimensions*/ {m.isize(), m.jsize()}, /*Buffer
                                                                dimensions*/
            {sizeof(float) * m.jsize(),
             /*Strides (in bytes) for each˓→index*/ sizeof(float)});
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
      .def("__getitem__",
           [](const field3d &m, ssize_t i, ssize_t j, ssize_t k) {
             if (i >= m.isize() || j >= m.jsize() || k >= m.ksize())
               throw pybind11::index_error();
             return m(i, j, k);
           })
      .def_buffer([](field3d &m) -> pybind11::buffer_info {
        return pybind11::buffer_info(
            m.data(), /*Pointer to buffer*/ sizeof(float),
            /*Size of one scalar*/ pybind11::format_descriptor<float>::format(),
            /*Python struct-style format˓→descriptor*/ 3,
            /*Number of dimensions*/ {m.isize(), m.jsize(), m.ksize()}, /*Buffer
                                                              dimensions*/
            {sizeof(float) * m.jsize() * m.ksize(), sizeof(float) * m.ksize(),
             /*Strides (in bytes) for each˓→index*/ sizeof(float)});
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
