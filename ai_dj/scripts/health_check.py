import asyncio
import aiohttp
import sys
from datetime import datetime

ICECAST_STATUS_URL = "http://localhost:8000/status-json.xsl"
NAVIDROME_PING_URL = "http://localhost:4533/api/ping"
LIQUIDSOAP_TELNET_HOST = "localhost"
LIQUIDSOAP_TELNET_PORT = 1234

async def check_icecast(session):
    try:
        async with session.get(ICECAST_STATUS_URL, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                return True, data.get('icestats', {}).get('server_name', 'Icecast')
    except Exception as e:
        return False, str(e)
    return False, "Unknown"

async def check_navidrome(session):
    try:
        async with session.get(NAVIDROME_PING_URL, timeout=5) as resp:
            if resp.status == 200:
                return True, await resp.text()
    except Exception as e:
        return False, str(e)
    return False, "Unknown"

async def check_liquidsoap():
    try:
        reader, writer = await asyncio.open_connection(LIQUIDSOAP_TELNET_HOST, LIQUIDSOAP_TELNET_PORT)
        # Simple ping command – Liquidsoap telnet supports "status"
        writer.write(b"status\n")
        await writer.drain()
        data = await reader.read(1024)
        writer.close()
        await writer.wait_closed()
        if data:
            return True, data.decode(errors='ignore')
    except Exception as e:
        return False, str(e)
    return False, "Unknown"

async def main():
    async with aiohttp.ClientSession() as session:
        ice_ok, ice_info = await check_icecast(session)
        nav_ok, nav_info = await check_navidrome(session)
        ls_ok, ls_info = await check_liquidsoap()
        timestamp = datetime.utcnow().isoformat()
        report = {
            "timestamp": timestamp,
            "icecast": {"healthy": ice_ok, "info": ice_info},
            "navidrome": {"healthy": nav_ok, "info": nav_info},
            "liquidsoap": {"healthy": ls_ok, "info": ls_info},
        }
        print(report)
        # Could also write to a log file
        if not (ice_ok and nav_ok and ls_ok):
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
