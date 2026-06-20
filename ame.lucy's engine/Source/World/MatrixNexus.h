#pragma once

namespace AME {

class MatrixNexus {
public:
    float luminance = 1.0f;
    float emissive = 0.5f;

    void Apply();
};

}
