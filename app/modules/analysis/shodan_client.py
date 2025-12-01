"""
shodan_client.py
=================

Dieses Modul integriert die Shodan-API.
Es löst Hostnamen in IP-Adressen auf, ruft die Shodan-Daten für diese Adresse ab
und bereitet die Ergebnisse in zwei Formen auf:

1) get_shodan_info(url)
   - Vollständige Abfrage aller verfügbaren Banner, Ports, SSL-Daten,
     HTTP-Service-Informationen, Organisation, ISP usw.
   - Liefert strukturierte Rohdaten + normalisierte Darstellung der Services.
   - Starkt debug-orientiert (viele print-Ausgaben).

2) get_shodan_overview(info)
   - Kompakte Übersicht auf Basis der Shodan-Rohdaten
   - Ideal für Frontend & LLM-Zusammenfassung
"""

# --------------------------------------------------------------
# Imports
# --------------------------------------------------------------
import socket
import shodan
from urllib.parse import urlparse
from app.core.config import settings


# --------------------------------------------------------------
# Vollständige Analyse eines Hosts mit Shodan
# --------------------------------------------------------------
def get_shodan_info(url: str) -> dict:
    """
    Ruft Shodan-Informationen für eine URL ab.
    Ablauf:
    1. API-Key prüfen
    2. Hostname extrahieren
    3. IP-Adresse auflösen
    4. Shodan-API abfragen
    5. Alle Services/Banner normalisieren

    Rückgabe (vereinfachtes Format):
        {
            "ip": "...",
            "isp": "...",
            "org": "...",
            "ports": [...],
            "services": [...],
            "raw_json": {...}
        }
    """

    print(f"🔎 [SHODAN] Starte Analyse für URL: {url}")

    # API-Key aus .env
    api_key = settings.SHODAN_API_KEY
    if not api_key:
        print("⚠️  [SHODAN] Kein SHODAN_API_KEY gesetzt!")
        return {"error": "Kein SHODAN_API_KEY gesetzt"}

    api = shodan.Shodan(api_key)

    # ----------------------------------------------------------
    # Hostname extrahieren
    # ----------------------------------------------------------
    hostname = urlparse(url).hostname
    print(f"✅ [SHODAN] Hostname extrahiert: {hostname}")

    if not hostname:
        print("❌ [SHODAN] Hostname ist None oder leer!")
        return {"error": "Ungültiger Hostname"}

    # ----------------------------------------------------------
    # DNS-Resolve → IP-Adresse
    # ----------------------------------------------------------
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ [SHODAN] IP aufgelöst: {ip}")
    except Exception as e:
        print(f"❌ [SHODAN] Fehler beim IP-Resolve: {e}")
        return {"error": f"IP-Resolve fehlgeschlagen: {e}"}

    # ----------------------------------------------------------
    # Shodan API-Abfrage
    # ----------------------------------------------------------
    try:
        result = api.host(ip)
        print("📡 [SHODAN] API-Ergebnisse empfangen.")
    except Exception as e:
        print("❌ [SHODAN] Fehler während der Analyse:", str(e))
        return {"error": str(e)}

    services = []
    data_entries = result.get("data", [])
    print(f"🧾 [SHODAN] Anzahl Banner-Einträge: {len(data_entries)}")

    # ----------------------------------------------------------
    # Services normalisieren
    # ----------------------------------------------------------
    for idx, banner in enumerate(data_entries, start=1):
        print(f"\n🔸 [SHODAN] Service #{idx}")
        print("  ↪ Port:", banner.get("port"))

        service_info = {
            "port": banner.get("port"),
            "transport": banner.get("transport"),
            "product": banner.get("product"),
            "version": banner.get("version"),
            "cpe": banner.get("cpe"),
            "os": banner.get("os"),
            "ssl": None,
            "http": None
        }

        # --------------------------
        # SSL-Informationen
        # --------------------------
        if "ssl" in banner:
            ssl_info = {"versions": banner["ssl"].get("versions"), "cert": None}

            # Zertifikat extrahieren
            if "cert" in banner["ssl"]:
                cert = banner["ssl"]["cert"]
                ssl_info["cert"] = {
                    "subject": cert.get("subject"),
                    "issuer": cert.get("issuer"),
                    "fingerprint": cert.get("fingerprint"),
                    "expired": cert.get("expired")
                }

            service_info["ssl"] = ssl_info

        # --------------------------
        # HTTP-Service-Infos
        # --------------------------
        if "http" in banner:
            http_info = {
                "title": banner["http"].get("title"),
                "server": banner["http"].get("server"),
                "components": banner["http"].get("components")
            }
            service_info["http"] = http_info

        services.append(service_info)

    # ----------------------------------------------------------
    # Endgültige strukturierte Ausgabe
    # ----------------------------------------------------------
    return {
        "ip": ip,
        "isp": result.get("isp"),
        "org": result.get("org"),
        "os": result.get("os"),
        "ports": result.get("ports") or [],
        "tags": result.get("tags") or [],
        "location": result.get("country_name"),
        "services": services,
        "raw_json": result
    }


# --------------------------------------------------------------
# Kompakte Shodan-Zusammenfassung
# --------------------------------------------------------------
def get_shodan_overview(shodan_info: dict) -> dict:
    """
    Gibt eine Übersicht zu den Shodan-Daten zurück.
    Wird im Frontend und bei der LLM-Zusammenfassung genutzt.
    """
    raw = shodan_info.get("raw_json", {}) or {}

    return {
        "ip": shodan_info.get("ip", "-"),
        "isp": shodan_info.get("isp", "-"),
        "org": shodan_info.get("org", "-"),
        "city": raw.get("city", "-"),
        "country": raw.get("country_name", "-"),
        "asn": raw.get("asn", "-"),
        "domains": raw.get("domains", []),
        "hostnames": raw.get("hostnames", []),
        "ports": shodan_info.get("ports", []),
        "tags": shodan_info.get("tags", []),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "last_update": raw.get("last_update", "-"),
        "raw_json": raw,
    }
