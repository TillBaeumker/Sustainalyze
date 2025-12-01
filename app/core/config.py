# app/core/config.py
#
# Lädt Konfigurationswerte aus der .env-Datei.
# BASE_DIR zeigt auf das Projektverzeichnis (drei Ebenen über dieser Datei).
# Alle externen API-Keys und Host-Konfigurationen sind hier zentral gesammelt.
# Dadurch bleibt der Code sauber und beim Deployment leicht anpassbar.

import os
from pathlib import Path
from dotenv import load_dotenv

# Basisverzeichnis des Projekts (app/core/config.py → core → app → Projektroot)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# .env-Datei laden (im Projektroot)
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path)

class Settings:
    # OpenAI-Schlüssel für GPT-Analysen
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # FUJI-Konfiguration (lokaler oder externer FUJI-Server)
    FUJI_HOST = os.getenv("FUJI_HOST")
    FUJI_USERNAME = os.getenv("FUJI_USERNAME")
    FUJI_PASSWORD = os.getenv("FUJI_PASSWORD")

    # Tokens für GitHub und GitLab API
    GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN")
    GITLAB_API_TOKEN = os.getenv("GITLAB_API_TOKEN")

    # Shodan API Key
    SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")

    # FAIR-Checker Konfiguration
    FAIR_CHECKER_BASE = os.getenv(
        "FAIR_CHECKER_BASE",
        "https://fair-checker.france-bioinformatique.fr",  # Default-Host
    )
    FAIR_CHECKER_TIMEOUT = int(os.getenv("FAIR_CHECKER_TIMEOUT", "60"))

    # TEI RNG Schema Pfad
    # Optional: Wird nur gesetzt, wenn TEI_RNG_SCHEMA in .env definiert wurde.
    TEI_RNG_SCHEMA = None
    tei_path_env = os.getenv("TEI_RNG_SCHEMA")
    if tei_path_env:
        TEI_RNG_SCHEMA = (BASE_DIR / tei_path_env).resolve()
    else:
        TEI_RNG_SCHEMA = None

# Globale Settings-Instanz
settings = Settings()
