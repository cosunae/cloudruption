cmake_minimum_required(VERSION 3.13)
project(toy)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)
find_package(MPI)
find_package(netCDF REQUIRED)
find_package(Rdkafka REQUIRED)
set(COMMONSRC KeyMessage.h)

add_executable(producer producer.cpp ${COMMONSRC})
target_include_directories(producer SYSTEM PUBLIC ${netCDF_INCLUDE_DIR})
target_include_directories(producer SYSTEM PUBLIC ${RDKAFKA_INCLUDE_DIRS})
target_link_libraries(producer ${netCDF_LIBRARIES})
target_link_libraries(producer ${RDKAFKA_LIBRARIES})

add_executable(consumer consumer.cpp ${COMMONSRC})
target_include_directories(consumer SYSTEM PUBLIC ${netCDF_INCLUDE_DIR})
target_include_directories(consumer SYSTEM PUBLIC ${RDKAFKA_INCLUDE_DIRS})
target_link_libraries(consumer ${netCDF_LIBRARIES})
target_link_libraries(consumer ${RDKAFKA_LIBRARIES})

