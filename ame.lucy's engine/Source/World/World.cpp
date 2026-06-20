#include "World.h"
#include "../Entities/NPC.h"
#include <iostream>

namespace AME {

World::World() {
    SpawnNPCs();
    std::cout << "[World] Monument initialized\n";
}

void World::SpawnNPCs() {
    for (int i = 0; i < 6; i++) {
        npcs.push_back(std::make_unique<NPC>(i * 2.0f, 0.0f));
    }
}

void World::Update() {
    for (auto& npc : npcs) {
        npc->Update();
    }
}

void World::Render() {
    std::cout << "[Render] Monument + " << npcs.size() << " NPCs\n";
}

}
