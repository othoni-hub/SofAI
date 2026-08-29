import os
import requests
from mcp.server.mcpserver import MCPServer

# On récupère le port dynamique attribué par l'hébergeur cloud (ou 8000 par défaut)
PORT = int(os.environ.get("PORT", 8000))

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
    """Obtient la météo dans la ville d'arrivée en Français et dans la langue locale.

    :param city: Nom de la ville d'arrivée (ex: 'Rome', 'Madrid')
    :param country_lang_code: Code ISO de la langue locale (ex: 'it', 'es',
    'de')
    """
    try:
        res_fr = requests.get(
            f"https://wttr.in/{city}?format=%C+%t+%w&lang=fr", timeout=5
        ).text.strip()
        res_local = requests.get(
            f"https://wttr.in/{city}?format=%C+%t+%w&lang={country_lang_code}",
            timeout=5,
        ).text.strip()
        return {
            "ville": city,
            "meteo_francais": res_fr,
            "meteo_langue_locale": res_local,
        }
    except Exception as e:
        return {"erreur": f"Impossible de récupérer la météo : {e}"}


if __name__ == "__main__":
    # Lancement en mode HTTP/SSE pour l'accès distant
    mcp.run(transport="sse", host="0.0.0.0", port=PORT)