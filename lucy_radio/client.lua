-- client.lua: Controls the NUI Radio player for Lucy

local isRadioOn = false
local radioVolume = 0.5 -- 0.0 to 1.0

-- Command to toggle the radio
RegisterCommand("lucyradio", function()
    isRadioOn = not isRadioOn
    
    if isRadioOn then
        -- Play stream
        SendNUIMessage({
            type = "PLAY",
            volume = radioVolume
        })
        TriggerEvent("chat:addMessage", { args = { "Lucy", "Tuning into Lucy Radio..." } })
    else
        -- Stop stream
        SendNUIMessage({
            type = "STOP"
        })
        TriggerEvent("chat:addMessage", { args = { "Lucy", "Turned off Lucy Radio." } })
    end
end, false)

-- Command to change volume (/vol 0-100)
RegisterCommand("lucyvol", function(source, args)
    if args[1] then
        local vol = tonumber(args[1])
        if vol and vol >= 0 and vol <= 100 then
            radioVolume = vol / 100.0
            SendNUIMessage({
                type = "VOLUME",
                volume = radioVolume
            })
            TriggerEvent("chat:addMessage", { args = { "System", "Lucy Radio volume set to " .. vol .. "%" } })
        else
            TriggerEvent("chat:addMessage", { args = { "System", "Invalid volume. Use 0-100." } })
        end
    end
end, false)

-- Event from server to force radio state (e.g. for forced DJ announcements)
RegisterNetEvent("lucy:radio:setState")
AddEventHandler("lucy:radio:setState", function(state, streamUrl)
    if state == "ON" then
        isRadioOn = true
        SendNUIMessage({
            type = "PLAY",
            url = streamUrl, -- Optional dynamic URL override
            volume = radioVolume
        })
    elseif state == "OFF" then
        isRadioOn = false
        SendNUIMessage({
            type = "STOP"
        })
    end
end)
