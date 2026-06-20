#pragma once
#include <stdint.h>
#include <stdbool.h>

// Versioning ensures the Node.js bridge and C++ plugins are aligned
#define LUCY_PLUGIN_API_VERSION 1

// Cross-platform export macros for dynamic loading (.dll / .so)
#if defined(_WIN32) || defined(_WIN64)
    #define LUCY_EXPORT __declspec(dllexport)
#else
    #define LUCY_EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

// -----------------------------------------------------------------------------
// Data Structures
// -----------------------------------------------------------------------------

// Passed FROM the Lucy Kernel (via Node Bridge) TO the C++ Plugin
struct LucyContext {
    int apiVersion;             // Must match LUCY_PLUGIN_API_VERSION
    const char* input;          // The specific command/payload for the plugin
    const char* memorySnapshot; // JSON string of relevant memory/state
    const char* intentId;       // Unique ID for tracing the execution
};

// Returned FROM the C++ Plugin TO the Lucy Kernel
struct LucyResult {
    bool success;               // True if execution succeeded
    const char* output;         // JSON or string result data
    float confidence;           // 0.0 to 1.0 confidence in the result
    double executionTimeMs;     // Internal execution time tracking
    const char* errors;         // Error message if success == false (nullable)
};

// -----------------------------------------------------------------------------
// Plugin Lifecycle & Execution Signatures
// -----------------------------------------------------------------------------

// 1. Initialization: Called once when the DLL/SO is loaded by the Node Bridge
LUCY_EXPORT bool LucyPlugin_Initialize();

// 2. Execution: The core stateless function called per-tick by Lucy
LUCY_EXPORT LucyResult LucyPlugin_Execute(LucyContext context);

// 3. Shutdown: Called when the DLL/SO is being unloaded
LUCY_EXPORT void LucyPlugin_Shutdown();

// -----------------------------------------------------------------------------
// Plugin Metadata Signatures
// -----------------------------------------------------------------------------

LUCY_EXPORT const char* LucyPlugin_GetName();
LUCY_EXPORT const char* LucyPlugin_GetCategory(); // e.g., "Analysis", "Action", "CognitiveAssist"
LUCY_EXPORT const char* LucyPlugin_GetVersion();

// -----------------------------------------------------------------------------
// Memory Management
// -----------------------------------------------------------------------------

// Because the plugin allocates strings for LucyResult (output, errors), 
// the Node Bridge MUST call this to free the memory after reading it,
// preventing memory leaks across the FFI boundary.
LUCY_EXPORT void LucyPlugin_FreeResult(LucyResult result);

} // extern "C"
