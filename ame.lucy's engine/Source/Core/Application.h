#pragma once
#include <memory>

namespace AME {

class Window;
class Renderer;
class World;

class Application {
public:
    Application();
    ~Application();

    void Run();

private:
    void Init();
    void Shutdown();

private:
    std::unique_ptr<Window> window;
    std::unique_ptr<Renderer> renderer;
    std::unique_ptr<World> world;

    bool isRunning = true;
    bool isEditorMode = true;
};

}
