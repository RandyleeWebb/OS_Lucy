#include "Renderer.h"
#include "../Platform/Window.h"
#include "../World/World.h"
#include <iostream>

namespace AME {

Renderer::Renderer(Window* window) : window(window) {
    std::cout << "[Renderer] Initialized (Vulkan stub)\n";
}

Renderer::~Renderer() {}

void Renderer::BeginFrame() {
    // placeholder
}

void Renderer::Render(World* world) {
    world->Render();
}

void Renderer::EndFrame() {
    // placeholder
}

}
