cmake_minimum_required(VERSION 3.10)
project(toy)
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

find_package(netCDF REQUIRED)
find_package(Rdkafka REQUIRED)
set(COMMONSRC KeyMessage.h nctools.cpp nctools.h Field.cpp Field.h Grid.cpp Grid.h Config.h)

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
#python bindings
#find_package(pybind11 CONFIG REQUIRED)

#MESSAGE( [MAIN] "Found pybind11 v${pybind11_VERSION}: ${pybind11_INCLUDE_DIR}")
#MESSAGE( [Main] " pybind11_INCLUDE_DIR = ${pybind11_INCLUDE_DIR}")
#MESSAGE( [Main] " pybind11_LIBRARIES = ${pybind11_LIBRARIES}")

#execute_process(COMMAND python3-config --extension-suffix OUTPUT_VARIABLE python_suffix_f)
#string(REPLACE ".so" "" python_suffix ${python_suffix_f})

#set(python_libname key_message)#${python_suffix})

#add_library(${python_libname} SHARED
#	python/key_message.cpp
#)

#set_property(TARGET ${python_libname} PROPERTY POSITION_INDEPENDENT_CODE ON)

#execute_process(COMMAND python3 -m pybind11 --includes OUTPUT_VARIABLE pybind_includes_str)
#string (REPLACE " " ";" pybind_includes_t "${pybind_includes_str}")
#string (REPLACE "-I" "" pybind_includes "${pybind_includes_t}")

#set(pybind_includes ";${pybind_includes}")
#target_include_directories(${python_libname} PRIVATE $<BUILD_INTERFACE:${pybind_includes}>)

#install(TARGETS ${python_libname} DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/)