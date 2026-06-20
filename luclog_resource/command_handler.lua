-- command_handler.lua: Polls Lucy backend for commands to execute on the FiveM server

local config = LoadResourceFile(GetCurrentResourceName(), "config.lua")
-- Defaults
LUCKY_CMD_ENDPOINT = "http://127.0.0.1:5000/lucy/commands"
CMD_POLL_INTERVAL = 2000
LUCKY_CMD_TOKEN = ""

-- Load config overrides
if config then
    local func = load(config)
    if func then func() end
end

local function handleChat(p)
    TriggerClientEvent('chat:addMessage', -1, { args = { "Lucy", p.message } })
end

local function handleSpawnNpc(p)
    local model = GetHashKey(p.model)
    RequestModel(model)
    -- Important: Wait until model loads; typically in a separate thread if yielding
    Citizen.CreateThread(function()
        while not HasModelLoaded(model) do Citizen.Wait(0) end
        local ped = CreatePed(4, model, p.x, p.y, p.z, p.heading or 0.0, true, true)
        SetEntityAsMissionEntity(ped, true, true)
    end)
end

local function handleSetWeather(p)
    SetWeatherTypeNow(p.type)          -- e.g., "CLEAR", "RAIN"
end

local function handleSetTime(p)
    NetworkOverrideClockTime(p.hour, p.minute, p.second or 0)
end

local function handleAdminCmd(p)
    ExecuteCommand(p.cmd)               -- e.g., "restart my_resource"
end

Citizen.CreateThread(function()
    while true do
        Citizen.Wait(CMD_POLL_INTERVAL)
        local headers = { ["Content-Type"] = "application/json" }
        if LUCKY_CMD_TOKEN and LUCKY_CMD_TOKEN ~= "" then
            headers["Authorization"] = "Bearer " .. LUCKY_CMD_TOKEN
        end

        PerformHttpRequest(LUCKY_CMD_ENDPOINT, function(status, response)
            if status == 200 and response then
                local cmds = json.decode(response)
                if cmds then
                    for _, cmd in ipairs(cmds) do
                        if cmd.type == "CHAT" then
                            handleChat(cmd.payload)
                        elseif cmd.type == "SPAWN_NPC" then
                            handleSpawnNpc(cmd.payload)
                        elseif cmd.type == "SET_WEATHER" then
                            handleSetWeather(cmd.payload)
                        elseif cmd.type == "SET_TIME" then
                            handleSetTime(cmd.payload)
                        elseif cmd.type == "ADMIN_CMD" then
                            handleAdminCmd(cmd.payload)
                        end
                    end
                end
            elseif status ~= 0 then
                -- Status 0 usually means endpoint not reachable, avoid spamming
                -- print("[LucyCmd] Failed to fetch commands (status "..tostring(status)..")")
            end
        end, "GET", "", headers)
    end
end)
