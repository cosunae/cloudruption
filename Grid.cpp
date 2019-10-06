#include "Grid.h"
#include <iostream>

void GridConf::print() {
  std::cout << "Lon : " << lonlen << " lat: " << latlen << " lev : " << levlen
            << std::endl;
}
