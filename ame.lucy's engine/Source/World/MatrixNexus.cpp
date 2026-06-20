#include "MatrixNexus.h"
#include <iostream>

namespace AME {

void MatrixNexus::Apply() {
    std::cout << "[MatrixNexus] Luminance: " << luminance
              << " Emissive: " << emissive << "\n";
}

}
