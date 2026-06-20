#pragma once
#include <vector>
#include <memory>

namespace AME {

class NPC;

class World {
public:
    World();

    void Update();
    void Render();

private:
    void SpawnNPCs();

private:
    std::vector<std::unique_ptr<NPC>> npcs;
};

}
