-- server.lua: Gathers world state and entity data, sends to Lucy backend

local function getPlayerData()
    local players = {}
    for _, playerId in ipairs(GetPlayers()) do
        local ped = GetPlayerPed(playerId)
        local coords = GetEntityCoords(ped)
        local health = GetEntityHealth(ped)
        table.insert(players, {
            id = playerId,
            name = GetPlayerName(playerId),
            ping = GetPlayerPing(playerId),
            coords = {x = coords.x, y = coords.y, z = coords.z},
            health = health
        })
    end
    return players
end

local function getVehicleData()
    local vehicles = {}
    for _, veh in ipairs(GetAllVehicles()) do
        local coords = GetEntityCoords(veh)
        table.insert(vehicles, {
            net_id = NetworkGetNetworkIdFromEntity(veh),
            model = GetEntityModel(veh),
            coords = {x = coords.x, y = coords.y, z = coords.z},
            health = GetEntityHealth(veh),
            engine_health = GetVehicleEngineHealth(veh)
        })
    end
    return vehicles
end

local function getNPCData()
    local npcs = {}
    for _, ped in ipairs(GetAllPeds()) do
        if not IsPedAPlayer(ped) then
            local coords = GetEntityCoords(ped)
            table.insert(npcs, {
                net_id = NetworkGetNetworkIdFromEntity(ped),
                model = GetEntityModel(ped),
                coords = {x = coords.x, y = coords.y, z = coords.z},
                health = GetEntityHealth(ped)
            })
        end
    end
    return npcs
end

local clientTelemetry = {}

RegisterNetEvent('lucy_sensors:updateClientTelemetry')
AddEventHandler('lucy_sensors:updateClientTelemetry', function(data)
    clientTelemetry[tostring(source)] = data
end)

Citizen.CreateThread(function()
    while true do
        Citizen.Wait(SENSOR_POLL_INTERVAL)
        
        local payload = json.encode({
            timestamp = os.date("!%Y-%m-%dT%H:%M:%SZ"),
            world_state = {
                players = getPlayerData(),
                vehicles = getVehicleData(),
                npcs = getNPCData()
            },
            client_telemetry = clientTelemetry
        })
        
        PerformHttpRequest(LUCKY_SENSORS_ENDPOINT, function(status, response)
            -- Handled silently unless debugging
        end, "POST", payload, { ["Content-Type"] = "application/json" })
    end
end)
