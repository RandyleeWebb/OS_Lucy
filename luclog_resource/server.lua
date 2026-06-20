-- server.lua: Monitor FXServer logs and forward error lines to Lucy AI backend

local config = LoadResourceFile(GetCurrentResourceName(), "config.lua")
-- Load config values
LUCKY_LOG_ENDPOINT = "http://127.0.0.1:5000/lucy/log"
LOG_POLL_INTERVAL = 2000
SERVER_LOG_PATH = "server-data/logs/txAdmin.log"

-- Allow overriding via config.lua if present
if config then
    local func = load(config)
    if func then func() end
end

local lastSize = 0

-- Helper to extract resource name and severity from a log line
local function parseLogLine(line)
    -- Default values
    local resource = "unknown"
    local severity = "info"

    -- Extract resource name if present in [resource] pattern
    local res = line:match("%[(%w+)%]")
    if res then resource = res end

    local lower = line:lower()
    if lower:find("error") or lower:find("exception") then
        severity = "error"
    elseif lower:find("warn") or lower:find("failed") then
        severity = "warning"
    else
        severity = "info"
    end

    return resource, severity
end

-- Gather additional context (e.g., player count)
local function getContext()
    local playerCount = #GetPlayers()
    return { playerCount = playerCount }
end

Citizen.CreateThread(function()
    while true do
        Citizen.Wait(LOG_POLL_INTERVAL)
        local fullPath = GetResourcePath(GetCurrentResourceName()) .. "/" .. SERVER_LOG_PATH
        local file = io.open(fullPath, "r")
        if file then
            file:seek("end", 0)
            local size = file:seek()
            if size > lastSize then
                file:seek("set", lastSize)
                while true do
                    local line = file:read("*line")
                    if not line then break end
                    -- Simple heuristic: forward lines that contain typical error keywords
                    if line:lower():find("error") or line:lower():find("failed") or line:lower():find("exception") then
                        local resource, severity = parseLogLine(line)
                        local context = getContext()
                        local payload = json.encode({
                            timestamp = os.date("!%Y-%m-%dT%H:%M:%SZ"),
                            log_line = line,
                            source = "FXServer",
                            resource = resource,
                            severity = severity,
                            context = context
                        })
                        PerformHttpRequest(LUCKY_LOG_ENDPOINT, function(status, response, headers)
                            -- You could add handling here; for now just debug print
                            if status >= 200 and status < 300 then
                                print("[LucyLog] Sent error line successfully: " .. line)
                            else
                                print("[LucyLog] Failed to send error line (status " .. status .. "): " .. line)
                            end
                        end, "POST", payload, { ["Content-Type"] = "application/json" })
                    end
                end
            end
            lastSize = size
            file:close()
        else
            print("[LucyLog] Unable to open log file at " .. fullPath)
        end
    end
end)
