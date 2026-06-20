#include "LucyPluginAPI.h"
#include <string>
#include <chrono>
#include <cstring>
#include <fstream>
#include <sstream>
#include <iostream>

static bool g_IsInitialized = false;

// Helper to allocate C-strings for the FFI boundary
static const char* AllocateString(const std::string& str) {
    char* cstr = new char[str.length() + 1];
    std::strcpy(cstr, str.c_str());
    return cstr;
}

// Helper to escape JSON strings safely
std::string EscapeJSON(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (c == '"') out += "\\\"";
        else if (c == '\\') out += "\\\\";
        else if (c == '\b') out += "\\b";
        else if (c == '\f') out += "\\f";
        else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "\\r";
        else if (c == '\t') out += "\\t";
        else out += c;
    }
    return out;
}

// Naive JSON extractor for MVP (avoids heavy dependencies like nlohmann/json for now)
std::string ExtractJsonValue(const std::string& json, const std::string& key) {
    std::string searchKey = "\"" + key + "\":";
    size_t pos = json.find(searchKey);
    if (pos == std::string::npos) return "";
    
    pos += searchKey.length();
    while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\t')) pos++;
    
    if (pos < json.length() && json[pos] == '"') {
        pos++;
        size_t endPos = pos;
        while (endPos < json.length() && json[endPos] != '"') {
            if (json[endPos] == '\\') endPos++; // skip escaped chars
            endPos++;
        }
        return json.substr(pos, endPos - pos);
    }
    return "";
}

extern "C" {

LUCY_EXPORT bool LucyPlugin_Initialize() {
    if (g_IsInitialized) return true;
    g_IsInitialized = true;
    return true;
}

LUCY_EXPORT LucyResult LucyPlugin_Execute(LucyContext context) {
    auto start = std::chrono::high_resolution_clock::now();
    
    LucyResult result;
    result.success = false;
    result.confidence = 0.0f;
    result.output = nullptr;
    result.errors = nullptr;

    if (context.apiVersion != LUCY_PLUGIN_API_VERSION) {
        result.errors = AllocateString("API Version mismatch.");
        return result;
    }

    std::string inputStr = context.input ? context.input : "{}";
    
    try {
        std::string action = ExtractJsonValue(inputStr, "action");
        std::string path = ExtractJsonValue(inputStr, "path");
        std::string content = ExtractJsonValue(inputStr, "content");

        if (action == "read") {
            std::ifstream file(path);
            if (!file.is_open()) {
                throw std::runtime_error("Failed to open file for reading: " + path);
            }
            std::stringstream buffer;
            buffer << file.rdbuf();
            
            std::string json = "{\"status\": \"read_success\", \"data\": \"" + EscapeJSON(buffer.str()) + "\"}";
            result.success = true;
            result.output = AllocateString(json);
            result.confidence = 1.0f;

        } else if (action == "write") {
            std::ofstream file(path, std::ios::trunc);
            if (!file.is_open()) {
                throw std::runtime_error("Failed to open file for writing: " + path);
            }
            file << content;
            
            std::string json = "{\"status\": \"write_success\", \"bytes_written\": " + std::to_string(content.length()) + "}";
            result.success = true;
            result.output = AllocateString(json);
            result.confidence = 1.0f;

        } else if (action == "append" || action == "log") {
            std::ofstream file(path, std::ios::app);
            if (!file.is_open()) {
                throw std::runtime_error("Failed to open file for appending: " + path);
            }
            file << content << "\n";
            
            std::string json = "{\"status\": \"append_success\", \"bytes_appended\": " + std::to_string(content.length()) + "}";
            result.success = true;
            result.output = AllocateString(json);
            result.confidence = 1.0f;

        } else {
            result.success = false;
            result.errors = AllocateString("Unknown file system action. Supported: read, write, append/log.");
        }
    } catch (const std::exception& e) {
        result.success = false;
        result.errors = AllocateString(e.what());
    }

    auto end = std::chrono::high_resolution_clock::now();
    result.executionTimeMs = std::chrono::duration<double, std::milli>(end - start).count();

    return result;
}

LUCY_EXPORT void LucyPlugin_Shutdown() {
    g_IsInitialized = false;
}

LUCY_EXPORT const char* LucyPlugin_GetName() {
    return "NativeFileSystem";
}

LUCY_EXPORT const char* LucyPlugin_GetCategory() {
    return "Action";
}

LUCY_EXPORT const char* LucyPlugin_GetVersion() {
    return "1.0.0";
}

LUCY_EXPORT void LucyPlugin_FreeResult(LucyResult result) {
    if (result.output) delete[] result.output;
    if (result.errors) delete[] result.errors;
}

} // extern "C"
