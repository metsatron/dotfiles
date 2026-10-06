-- Evaluated as one global admin-shell chunk, with only registry fields as input.
local json = require "prosody.util.json";
local array = require "prosody.util.array";
local request = json.decode(request_json);
local current_index, phase = 0, "preflight";
local function fail(code)
    error({ code = code; room = current_index; phase = phase }, 0);
end
local settings = {
    { "persistent", true }; { "hidden", true }; { "whois", "moderators" };
    { "allow_member_invites", false }; { "members_only", true };
};
local methods = { "each_affiliation", "get_affiliation", "set_affiliation",
                  "each_occupant", "get_role", "set_role", "save" };
local function compatible(room)
    if type(room._data) ~= "table" or room._data.destroyed or room._data.locked then
        fail("room-protected");
    end
    for _, name in ipairs(methods) do
        if type(room[name]) ~= "function" then fail("api-unavailable"); end
    end
    for _, item in ipairs(settings) do
        if type(room["get_" .. item[1]]) ~= "function"
        or type(room["set_" .. item[1]]) ~= "function" then fail("api-unavailable"); end
    end
end
local function inspect(room, desired, index)
    local row = { index = index; created = room == nil; verified = false;
        settings = array(); grant_owner = 0; grant_admin = 0; clear_affiliations = 0;
        repair_moderators = 0; remove_occupants = 0; };
    local allowed, grants, removals = {}, {}, {};
    -- Owner-first union: an overlapping seat cannot downgrade the human.
    for _, kind in ipairs({ { "owner", desired.owners }; { "admin", desired.admins } }) do
        for _, jid in ipairs(kind[2]) do
            if not allowed[jid] then
                allowed[jid] = kind[1];
                if not room or room:get_affiliation(jid) ~= kind[1] then
                    local count = "grant_" .. kind[1];
                    row[count] = row[count] + 1;
                    table.insert(grants, { jid = jid; affiliation = kind[1] });
                end
            end
        end
    end
    for _, item in ipairs(settings) do
        if not room or room["get_" .. item[1]](room) ~= item[2] then
            table.insert(row.settings, item[1]);
        end
    end
    if room then
        for jid in room:each_affiliation() do
            if not allowed[jid] then
                row.clear_affiliations = row.clear_affiliations + 1;
                table.insert(removals, jid);
            end
        end
        for _, occupant in room:each_occupant() do
            if not allowed[occupant.bare_jid] then
                row.remove_occupants = row.remove_occupants + 1;
            elseif occupant.role ~= "moderator" then
                row.repair_moderators = row.repair_moderators + 1;
            end
        end
    end
    table.sort(grants, function(a, b)
        if a.affiliation ~= b.affiliation then return a.affiliation == "owner"; end
        return a.jid < b.jid;
    end);
    table.sort(removals);
    return row, allowed, grants, removals;
end
local function work()
    local plans, rows = {}, array();
    for index, desired in ipairs(request.rooms) do
        current_index = index;
        local host = desired.jid:match("@(.+)$");
        local host_session = prosody.hosts[host];
        local muc = host_session and host_session.modules and host_session.modules.muc;
        if not muc then fail("host-unavailable"); end
        if type(muc.get_room_from_jid) ~= "function" or type(muc.create_room) ~= "function" then
            fail("api-unavailable");
        end
        local room = muc.get_room_from_jid(desired.jid);
        if room == false then fail("lookup-failed"); end
        if room then compatible(room); end
        local row, allowed, grants, removals = inspect(room, desired, index);
        table.insert(rows, row);
        table.insert(plans, { room = room; muc = muc; desired = desired; row = row;
                             allowed = allowed; grants = grants; removals = removals });
    end
    if request.dry_run then return { ok = true; dry_run = true; rooms = rows }; end
    phase = "apply";
    for index, plan in ipairs(plans) do
        current_index = index;
        local room = plan.room;
        if not room then
            -- Config skips module defaults; new room is private and persistent immediately.
            room = plan.muc.create_room(plan.desired.jid, {
                persistent = true; hidden = true; whois = "moderators";
                allow_member_invites = false; members_only = true;
            });
            if not room then fail("create-failed"); end
            compatible(room);
        end
        -- Persist first: tightening membership may empty a room and fire destruction hooks.
        for _, item in ipairs(settings) do
            if item[1] ~= "members_only" then
                if room["get_" .. item[1]](room) ~= item[2] then
                    room["set_" .. item[1]](room, item[2]);
                end
                if room["get_" .. item[1]](room) ~= item[2] then fail("setting-failed"); end
            end
        end
        -- Admit human and seats before tightening membership; retain their occupants.
        for _, grant in ipairs(plan.grants) do
            if not room:set_affiliation(true, grant.jid, grant.affiliation) then
                fail("affiliation-failed");
            end
        end
        if room:get_members_only() ~= true then room:set_members_only(true); end
        if room:get_members_only() ~= true then fail("setting-failed"); end
        for _, jid in ipairs(plan.removals) do
            if not room:set_affiliation(true, jid, "none") then fail("affiliation-failed"); end
        end
        local occupants = {};
        for nick, occupant in room:each_occupant() do
            table.insert(occupants, { nick = nick; bare_jid = occupant.bare_jid; role = occupant.role });
        end
        for _, occupant in ipairs(occupants) do
            if not plan.allowed[occupant.bare_jid] then
                if not room:set_role(true, occupant.nick, nil) then fail("role-failed"); end
            elseif occupant.role ~= "moderator" then
                if not room:set_role(true, occupant.nick, "moderator") then fail("role-failed"); end
            end
        end
        local check = inspect(room, plan.desired, index);
        if #check.settings ~= 0 or check.grant_owner ~= 0 or check.grant_admin ~= 0
        or check.clear_affiliations ~= 0
        or check.repair_moderators ~= 0 or check.remove_occupants ~= 0 then fail("verify-failed"); end
        -- set_affiliation internally saves but ignores save failure; always check final save.
        if not room:save(true) then fail("save-failed"); end
        plan.row.verified = true;
    end
    return { ok = true; dry_run = false; rooms = rows };
end
local ok, result = pcall(work);
if not ok then
    if type(result) ~= "table" or type(result.code) ~= "string" then
        result = { code = "operation-failed"; room = current_index; phase = phase };
    end
    result = { ok = false; code = result.code; room = current_index; phase = phase };
end
return response_marker .. json.encode(result);
