cmake_minimum_required(VERSION 3.10)
project(producer-consumer C CXX Fortran)
include(FetchContent)
set (CMAKE_CXX_STANDARD 17)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)
option(ENABLE_PRODUCER ON)
option(ENABLE_MPI OFF)
option(ENABLE_FORTRAN OFF)
if(ENABLE_MPI)
  if(ENABLE_FORTRAN)
    find_package(MPI COMPONENTS CXX Fortran REQUIRED)
  else()
    find_package(MPI COMPONENTS CXX REQUIRED)
  endif()
endif()
  find_package(eccodes)

#FetchContent_Declare(pybind11
#  URL https://github.com/pybind/pybind11/archive/v2.4.3.tar.gz
#)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.4.3
)
FetchContent_GetProperties(pybind11)
if(NOT pybind11_POPULATED)
  FetchContent_Populate(pybind11)
endif()

#set(PYBIND11_PYTHON_VERSION 3.6)
set(PYBIND11_CPP_STANDARD -std=c++17)
add_subdirectory(${pybind11_SOURCE_DIR} ${pybind11_BINARY_DIR})


find_package(netCDF REQUIRED)
find_package(Rdkafka REQUIRED)
set(COMMONSRC 
    DistributedField.cpp 
    DistributedField.h
    KeyMessage.h 
    nctools.cpp 
    nctools.h 
    datadesc.h
    field.cpp
    field.h
    FieldProp.cpp 
    FieldProp.h 
    Grid.cpp 
    Grid.h 
    Config.h
    SinglePatch.h)

if(ENABLE_PRODUCER)
  find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
  set(KAFKAPROD_SRC 
    KafkaProducer.cpp
    KafkaProducer.h
  )
  add_library(kafkaproducer ${KAFKAPROD_SRC})
  target_include_directories(kafkaproducer SYSTEM PUBLIC ${RDKAFKA_INCLUDE_DIRS})
  target_link_libraries(kafkaproducer ${RDKAFKA_LIBRARIES})

  add_executable(producer producer.cpp ${COMMONSRC})
  target_link_libraries(producer kafkaproducer)
  target_link_libraries(producer stdc++fs)

  if(ENABLE_MPI)
    target_compile_definitions(producer PUBLIC ENABLE_MPI)
  endif()
  target_include_directories(producer SYSTEM PUBLIC ${netCDF_INCLUDE_DIR})
  target_include_directories(producer SYSTEM PUBLIC ${MPI_CXX_INCLUDE_DIRS})

  target_link_libraries(producer ${netCDF_LIBRARIES})
  target_link_libraries(producer ${MPI_CXX_LIBRARIES})
  target_link_libraries(producer eccodes)
  target_link_libraries(producer Python3::Python) 

  set(BINDPRODUCERSRC 
    interface/bindproducer.cpp
  )
  add_library(bindproducer ${BINDPRODUCERSRC})
  target_link_libraries(bindproducer PUBLIC kafkaproducer)
  target_link_libraries(bindproducer INTERFACE stdc++)

  install(TARGETS kafkaproducer bindproducer EXPORT producer-consumer LIBRARY DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/)
  install(TARGETS producer DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)


  if(ENABLE_FORTRAN)
    add_library(fbindproducer interface/bindproducer.f90 interface/bind_data.f90)
    target_link_libraries(fbindproducer INTERFACE bindproducer)
    add_executable(testBindings test/testBindings.f90)
    target_compile_options(testBindings PUBLIC -cpp)

    if(ENABLE_MPI)
      target_compile_definitions(testBindings PRIVATE ENABLE_MPI)
      target_include_directories(testBindings PRIVATE ${MPI_Fortran_INCLUDE_DIRS})
      target_link_libraries(testBindings PRIVATE ${MPI_Fortran_LIBRARIES})
    endif(ENABLE_MPI)

    target_link_libraries(testBindings PRIVATE fbindproducer)
    
    install(TARGETS fbindproducer EXPORT fproducer-consumer LIBRARY DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/)

  endif(ENABLE_FORTRAN)

endif()

add_executable(consumer consumer.cpp ${COMMONSRC})

target_include_directories(consumer SYSTEM PUBLIC ${netCDF_INCLUDE_DIR})
target_include_directories(consumer SYSTEM PUBLIC ${RDKAFKA_INCLUDE_DIRS})
target_link_libraries(consumer PRIVATE ${netCDF_LIBRARIES})
target_link_libraries(consumer PRIVATE ${RDKAFKA_LIBRARIES})
target_link_libraries(consumer PRIVATE "stdc++fs")

install(TARGETS consumer DESTINATION ${CMAKE_INSTALL_PREFIX}/bin/)

pybind11_add_module(fieldop fieldop.cpp DistributedField.cpp field.cpp)
pybind11_add_module(testfieldop test/testfieldop.cpp)


install(EXPORT producer-consumer DESTINATION cmake NAMESPACE pc:: FILE producer-consumer-config.cmake)
if(ENABLE_FORTRAN)
  install(EXPORT fproducer-consumer DESTINATION cmake NAMESPACE pc::)
endif()

#install(TARGETS ${python_libname} DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/)
