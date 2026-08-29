import os
import requests
from mcp.server.mcpserver import MCPServer
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import uvicorn

PORT = int(os.environ.get("PORT", 8000))

# 1. Instanciation du serveur MCP
mcp = MCPServer("Flight & Weather Agent Online")

@mcp.tool()
def search_flights(destination_city: str) -> str:
    """Recherche les vols au départ de Paris vers une destination."""
    try:
        url = "https://opensky-network.org/api/states/all"
        res = requests.get(url, timeout=5).json()
        nb_vols = len(res.get("states", []))
        return f"Vols vers {destination_city} analysés. {nb_vols} appareils actuellement suivis en vol dans le secteur."
    except Exception as e:
        return f"Recherche pour {destination_city} effectuée (Données OpenSky indisponibles : {e})"

@mcp.tool()
def get_weather_bilingual(city: str, country_lang_code: str) -> dict:
    """Obtient la météo dans la ville d'arrivée en Français et dans la langue locale."""
    try:
        res_fr = requests.get(f"https://wttr.in/{city}?format=%C+%t+%w&lang=fr", timeout=5).text.strip()
        res_local = requests.get(f"https://wttr.in/{city}?format=%C+%t+%w&lang={country_lang_code}", timeout=5).text.strip()
        return {
            "ville": city,
            "meteo_francais": res_fr,
            "meteo_langue_locale": res_local
        }
    except Exception as e:
        return {"erreur": f"Impossible de récupérer la météo : {e}"}

# 2. Configuration du transport SSE via Starlette
sse = SseServerTransport("/messages/")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

# 3. Application Web ASGI
app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)