#pragma once
#include <string>
#include <GLFW/glfw3.h>

namespace AME {

class Window {
public:
    Window(int width, int height, const std::string& title);
    ~Window();

    void PollEvents();
    bool ShouldClose() const;

    GLFWwindow* GetNative() { return window; }

private:
    GLFWwindow* window;
};

}
