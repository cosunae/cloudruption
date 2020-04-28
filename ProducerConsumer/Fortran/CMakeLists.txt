cmake_minimum_required(VERSION 3.10)
project(fproducer-consumer Fortran)

set(CMAKE_Fortran_MODULE_DIRECTORY ${CMAKE_BINARY_DIR}/Fortran)

option(ENABLE_MPI OFF)
if(ENABLE_MPI)
  find_package(MPI COMPONENTS CXX Fortran REQUIRED)
endif()
find_package(producer-consumer)

add_library(fbindproducer ../interface/bindproducer.f90 ../interface/bind_data.f90)
target_link_libraries(fbindproducer INTERFACE pc::bindproducer)
add_executable(testBindings ../test/testBindings.f90)
target_compile_options(testBindings PUBLIC -cpp)

if(ENABLE_MPI)
  target_compile_definitions(testBindings PRIVATE ENABLE_MPI)
  target_include_directories(testBindings PRIVATE ${MPI_Fortran_INCLUDE_DIRS})
  target_link_libraries(testBindings PRIVATE ${MPI_Fortran_LIBRARIES})
endif(ENABLE_MPI)

target_link_libraries(testBindings PRIVATE fbindproducer)
    
install(TARGETS fbindproducer EXPORT fproducer-consumer PUBLIC_HEADER LIBRARY DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/)
install(DIRECTORY ${CMAKE_BINARY_DIR}/Fortran DESTINATION include/)

