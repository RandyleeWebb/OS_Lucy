#pragma once

namespace AME {

class Window;
class World;

class Renderer {
public:
    Renderer(Window* window);
    ~Renderer();

    void BeginFrame();
    void Render(World* world);
    void EndFrame();

private:
    Window* window;
};

}
