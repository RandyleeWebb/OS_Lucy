#include "NPC.h"
#include <iostream>

namespace AME {

NPC::NPC(float x, float z) : x(x), z(z) {}

void NPC::Update() {
    x += 0.01f * direction;

    if (x > 5.0f || x < -5.0f)
        direction *= -1.0f;
}

}
