-- Configuration for Lucy log monitor
-- Replace with your Lucy backend endpoint URL
LUCKY_LOG_ENDPOINT = "http://127.0.0.1:5000/lucy/log"

-- How often to check the log file (in milliseconds)
LOG_POLL_INTERVAL = 2000 -- 2 seconds

-- Path to the server log file (relative to the server root)
SERVER_LOG_PATH = "server-data/logs/txAdmin.log" -- adjust if using different log file

-- Endpoint Lucy will poll for commands (GET request)
LUCKY_CMD_ENDPOINT = "http://127.0.0.1:5000/lucy/commands"

-- How often to poll for commands (ms)
CMD_POLL_INTERVAL = 2000

-- Optional bearer token for simple auth
LUCKY_CMD_TOKEN = ""   -- leave empty if not used
