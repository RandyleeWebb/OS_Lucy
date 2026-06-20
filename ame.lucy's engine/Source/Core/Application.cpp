#include "Application.h"
#include "../Platform/Window.h"
#include "../Rendering/Renderer.h"
#include "../World/World.h"

namespace AME {

Application::Application() {
    Init();
}

Application::~Application() {
    Shutdown();
}

void Application::Init() {
    window = std::make_unique<Window>(3840, 2160, "Alpha Matrix Engine"); // start 4K, scale to 8K later
    renderer = std::make_unique<Renderer>(window.get());
    world = std::make_unique<World>();
}

void Application::Shutdown() {
    renderer.reset();
    world.reset();
    window.reset();
}

void Application::Run() {
    while (isRunning && !window->ShouldClose()) {
        window->PollEvents();

        renderer->BeginFrame();

        world->Update();
        renderer->Render(world.get());

        renderer->EndFrame();
    }
}

}
