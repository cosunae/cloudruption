cmake_minimum_required(VERSION 3.10)
project(toy)
include(FetchContent)
set (CMAKE_CXX_STANDARD 17)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)
option(ENABLE_PRODUCER ON)
set(ENABLE_MPI OFF)
if(ENABLE_PRODUCER)
  set(ENABLE_MPI ON)
endif()
if(ENABLE_MPI)
  find_package(MPI COMPONENTS CXX REQUIRED)
endif()

#FetchContent_Declare(pybind11
#  URL https://github.com/pybind/pybind11/archive/v2.4.3.tar.gz
#)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.4.3
)
FetchContent_GetProperties(pybind11)
if(NOT googletest_POPULATED)
  FetchContent_Populate(pybind11)
endif()

#set(PYBIND11_PYTHON_VERSION 3.6)
set(PYBIND11_CPP_STANDARD -std=c++17)
add_subdirectory(${pybind11_SOURCE_DIR})


find_package(netCDF REQUIRED)
find_package(Rdkafka REQUIRED)
set(COMMONSRC 
    DistributedField.cpp 
    DistributedField.h 
    KeyMessage.h 
    nctools.cpp 
    nctools.h 
    field.cpp
    field.h
    FieldProp.cpp 
    FieldProp.h 
    Grid.cpp 
    Grid.h 
    Config.h
    SinglePatch.h)

if(ENABLE_PRODUCER)
  add_executable(producer producer.cpp ${COMMONSRC})

  target_include_directories(producer SYSTEM PUBLIC ${netCDF_INCLUDE_DIR})
  target_include_directories(producer SYSTEM PUBLIC ${RDKAFKA_INCLUDE_DIRS})
  target_include_directories(producer SYSTEM PUBLIC ${MPI_CXX_INCLUDE_DIRS})

  target_link_libraries(producer ${netCDF_LIBRARIES})
  target_link_libraries(producer ${RDKAFKA_LIBRARIES})
  target_link_libraries(producer ${MPI_CXX_LIBRARIES})
endif()

add_executable(consumer consumer.cpp ${COMMONSRC})

target_include_directories(consumer SYSTEM PUBLIC ${netCDF_INCLUDE_DIR})
target_include_directories(consumer SYSTEM PUBLIC ${RDKAFKA_INCLUDE_DIRS})
target_link_libraries(consumer PRIVATE ${netCDF_LIBRARIES})
target_link_libraries(consumer PRIVATE ${RDKAFKA_LIBRARIES})
target_link_libraries(consumer PRIVATE "stdc++fs")

pybind11_add_module(fieldop fieldop.cpp DistributedField.cpp field.cpp)
pybind11_add_module(testfieldop testfieldop.cpp)


#install(TARGETS ${python_libname} DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/)
