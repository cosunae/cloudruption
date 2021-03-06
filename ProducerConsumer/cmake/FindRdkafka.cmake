include (FindPackageHandleStandardArgs)
find_path(RDKAFKA_INCLUDE_DIR rdkafka.h HINTS ${RDKAFKA_ROOT} PATH_SUFFIXES librdkafka)
find_library(RDKAFKA_LIBRARY NAMES rdkafka)
find_library(RDKAFKA_CPP_LIBRARY NAMES rdkafka++)

find_package_handle_standard_args(Rdkafka  DEFAULT_MSG
                                  RDKAFKA_INCLUDE_DIR RDKAFKA_LIBRARY RDKAFKA_CPP_LIBRARY)

mark_as_advanced(RDKAFKA_INCLUDE_DIR RDKAFKA_LIBRARY RDKAFKA_CPP_LIBRARY)

set(RDKAFKA_LIBRARIES ${RDKAFKA_LIBRARY} ${RDKAFKA_CPP_LIBRARY})

set(RDKAFKA_INCLUDE_DIRS ${RDKAFKA_INCLUDE_DIR} )

