cmake_minimum_required(VERSION 3.13)
project(toy)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)
find_package(MPI)
find_package(netCDF REQUIRED)
find_package(Rdkafka REQUIRED)

add_executable(toy main.cpp)
target_include_directories(toy SYSTEM PUBLIC ${netCDF_INCLUDE_DIR})
target_include_directories(toy SYSTEM PUBLIC ${RDKAFKA_INCLUDE_DIRS})
target_link_libraries(toy ${netCDF_LIBRARIES})
target_link_libraries(toy ${RDKAFKA_LIBRARIES})

