#pragma once

namespace AME {

class NPC {
public:
    NPC(float x, float z);

    void Update();

private:
    float x, z;
    float direction = 1.0f;
};

}
