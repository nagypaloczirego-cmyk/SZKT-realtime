import aiohttp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# =======================
# BEÁLLÍTÁSOK
# =======================

API_BASE = "https://pan-kruger-brooks-trigger.trycloudflare.com"

STOP_API = API_BASE + "/stop?stopId={stop_id}"
VEHICLE_API = API_BASE + "/vehicle?route={route}&id={dep_id}"

WATCH_STOPS = {
    "166","289","346","391","725","792","1008","1112","1247","1333",
    "1346","1800","1935","1994","2185","2225","2228","2360","2391",
    "2432","2502","2503","2544","2549","2587","2588","2900","2901",
    "2902","1989"
}

TROLLEY_LINES = {"1E","5","6","8","9","10","19","X8","X9","X10","X19"}


# =======================
# SEGÉD FÜGGVÉNYEK
# =======================

def is_15tr(reg):
    if not isinstance(reg, str):
        return False
    if not reg.startswith("T"):
        return False
    if not reg[1:].isdigit():
        return False
    return 600 <= int(reg[1:]) <= 630

async def fetch_json(session, url):
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as r:
            if r.status != 200:
                return None
            return await r.json()
    except:
        return None

def get_last_vehicle_reg(veh):
    """
    Ha az API több járművet ad vissza,
    mindig az UTOLSÓ rendszámot használjuk.
    """
    if not isinstance(veh, list) or not veh:
        return None

    last = veh[-1]
    if not isinstance(last, dict):
        return None

    return last.get("VehicleRegistrationNumber")

# =======================
# KÖZÖS LOGIKA
# =======================

async def get_active_trolleys(only_skoda=False):
    active = {}

    async with aiohttp.ClientSession() as session:
        for stop_id in WATCH_STOPS:
            stop_data = await fetch_json(
                session,
                STOP_API.format(stop_id=stop_id)
            )

            if not isinstance(stop_data, list):
                continue

            for dep in stop_data:
                if not dep.get("realTime"):
                    continue

                line = str(dep.get("line"))
                if line not in TROLLEY_LINES:
                    continue

                dep_id = dep.get("id")
                if not dep_id:
                    continue

                dest = dep.get("dest", "Ismeretlen")
                dep_time = dep.get("departure", 0)

                veh = await fetch_json(
                    session,
                    VEHICLE_API.format(route=line, dep_id=dep_id)
                )

                reg = get_last_vehicle_reg(veh)
                if not reg:
                    continue

                if only_skoda and not is_15tr(reg):
                    continue

                if reg not in active or dep_time < active[reg]["dep"]:
                    active[reg] = {
                        "reg": reg,
                        "line": line,
                        "dest": dest,
                        "stop": stop_id,
                        "dep": dep_time
                    }

    return list(active.values())

# =======================
# FASTAPI APP
# =======================

app = FastAPI(title="Troli Web")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# statikus fájlok (CSS, JS, stb.)
app.mount("/static", StaticFiles(directory="."), name="static")

# frontend
@app.get("/")
async def index():
    return FileResponse("index.html")

# =======================
# API ENDPOINTOK
# =======================

@app.get("/api/alltroli")
async def api_alltroli():
    return await get_active_trolleys(False)

@app.get("/api/allskoda")
async def api_allskoda():
    return await get_active_trolleys(True)
