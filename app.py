from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import aiohttp

app = FastAPI()

API_BASE = "https://trim-republicans-alive-gregory.trycloudflare.com"
STOP_API = API_BASE + "/stop?stopId={stop_id}"
VEHICLE_API = API_BASE + "/vehicle?route={route}&id={dep_id}"

WATCH_STOPS = {
    "166","289","346","391","725","792","1008","1112","1247","1333",
    "1346","1800","1935","1994","2185","2225","2228","2360","2391",
    "2432","2502","2503","2544","2549","2587","2588","2900","2901",
    "2902","1989"
}

TROLLEY_LINES = {"5","6","8","9","10","19"}

def is_15tr(reg):
    return isinstance(reg, str) and reg.startswith("T") and reg[1:].isdigit() and 600 <= int(reg[1:]) <= 630

async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=5) as r:
            return await r.json() if r.status == 200 else None
    except:
        return None

async def get_data(only_skoda=False):
    active = {}
    async with aiohttp.ClientSession() as session:
        for stop in WATCH_STOPS:
            data = await fetch_json(session, STOP_API.format(stop_id=stop))
            if not isinstance(data, list):
                continue
            for dep in data:
                if not dep.get("realTime"):
                    continue
                line = str(dep.get("line"))
                if line not in TROLLEY_LINES:
                    continue
                veh = await fetch_json(session, VEHICLE_API.format(
                    route=line, dep_id=dep.get("id")
                ))
                if not veh:
                    continue
                reg = veh[0].get("VehicleRegistrationNumber")
                if only_skoda and not is_15tr(reg):
                    continue
                active[reg] = {
                    "reg": reg,
                    "line": line,
                    "dest": dep.get("dest"),
                    "stop": stop,
                    "trip_id": dep.get("id")
                }
    return list(active.values())

@app.get("/api/alltroli")
async def alltroli():
    return await get_data(False)

@app.get("/api/allskoda")
async def allskoda():
    return await get_data(True)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
