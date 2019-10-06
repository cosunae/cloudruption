#pragma once

#include "Field.h"
#include <string>

int netcdfDump(int mpirank, float *f, const FieldProp &fieldProp,
               std::string output);
