-- client.lua: Client-side spatial and raycast telemetry sensor for Lucy

local SENSOR_POLL_INTERVAL = 1000 -- Poll every 1 second
local lastPosition = nil
local stuckCounter = 0

-- Helper to run a raycast in front of the ped
local function runForwardRaycast(ped, distance)
    local coords = GetEntityCoords(ped)
    local heading = GetEntityHeading(ped)
    local rad = math.rad(heading + 90.0)
    
    -- Calculate target coords based on heading
    local targetX = coords.x + (distance * math.cos(rad))
    local targetY = coords.y + (distance * math.sin(rad))
    local targetZ = coords.z
    
    -- Run raycast (1 = Map, 2 = Peds, 4 = Vehicles, 16 = Objects)
    local ray = StartShapeTestRay(coords.x, coords.y, coords.z, targetX, targetY, targetZ, 1 + 2 + 4 + 16, ped, 0)
    local _, hit, endCoords, surfaceNormal, entityHit = GetShapeTestResult(ray)
    
    local entityType = 0
    local desc = "No Collision"
    if hit then
        if entityHit > 0 then
            entityType = GetEntityType(entityHit)
            if entityType == 1 then desc = "Ped"
            elseif entityType == 2 then desc = "Vehicle"
            elseif entityType == 3 then desc = "Object"
            end
        else
            desc = "World Collision"
        end
    end
    
    return {
        hit = hit == 1,
        entity_type = entityType,
        surface_normal = { surfaceNormal.x, surfaceNormal.y, surfaceNormal.z },
        desc = desc,
        distance = hit == 1 and #(coords - endCoords) or distance
    }
end

Citizen.CreateThread(function()
    while true do
        Citizen.Wait(SENSOR_POLL_INTERVAL)
        
        local playerPed = PlayerPedId()
        if DoesEntityExist(playerPed) then
            local coords = GetEntityCoords(playerPed)
            local heading = GetEntityHeading(playerPed)
            local speed = GetEntitySpeed(playerPed)
            
            -- Stuck detection logic
            local isStuck = false
            if lastPosition then
                local dist = #(coords - lastPosition)
                if dist < 0.1 and speed > 0.1 then
                    stuckCounter = stuckCounter + 1
                    if stuckCounter > 3 then -- 3 seconds of being stuck
                        isStuck = true
                    end
                else
                    stuckCounter = 0
                end
            end
            lastPosition = coords
            
            -- Pack client telemetry
            local clientTelemetry = {
                xyz = { coords.x, coords.y, coords.z },
                heading = heading,
                speed = speed,
                is_stuck = isStuck,
                raycast_collisions = {
                    forward_5m = runForwardRaycast(playerPed, 5.0),
                    forward_15m = runForwardRaycast(playerPed, 15.0)
                }
            }
            
            TriggerServerEvent('lucy_sensors:updateClientTelemetry', clientTelemetry)
        end
    end
end)
