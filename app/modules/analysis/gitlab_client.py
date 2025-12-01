"""
gitlab_client.py
==============================

GitLab-Repository-Analyse über die GitLab REST API v4
----------------------------------------------------

Dieses Modul ruft strukturierte Metadaten aus öffentlichen und privaten
GitLab-Repositories ab. Die Ergebnisstruktur ist kompatibel zum
`github_client.py`, damit die Frontend-Auswertung und dein
Nachhaltigkeits-Scoring einheitlich bleiben.

Erfasste Informationen:
-----------------------
- Lizenz des Repositories
- README vorhanden? (mehrere mögliche Pfade)
- CONTRIBUTING vorhanden?
- Sichtbarkeit (public/private/internal)
- Letzte Aktivitäten / Default-Branch
- Sterne, Forks, offene Issues
- Anzahl der Contributors (Pagination über X-Next-Page)
- Diskussionen/Issues aktiviert?

"""
import aiohttp
from typing import Optional, Tuple, List
from urllib.parse import urlparse, quote, quote_plus
from app.core.config import settings


def parse_gitlab_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrahiert owner und repo aus einer GitLab-URL.

    GitLab-Struktur:
        https://gitlab.com/<owner>/<repo>(/optional/weitere/pfade)

    Rückgabe:
        (owner, repo) oder (None, None) bei ungültigen URLs.
    """
    p = urlparse(url)
    if p.netloc != "gitlab.com":
        print(f"⚠️  Keine gültige GitLab-Domain: {url}")
        return None, None

    parts = p.path.strip("/").split("/")
    if len(parts) < 2:
        print(f"⚠️  Ungültiger GitLab-Pfad: {p.path}")
        return None, None

    # Bei GitLab kann die owner-Struktur mehrere Ebenen haben,
    # z. B. group/subgroup/project → owner = group/subgroup
    return "/".join(parts[:-1]), parts[-1]


async def analyze_gitlab_repo(url: str) -> dict:
    """
    Holt Repository-Informationen über die GitLab REST API v4.

    Ablauf:
    - Projektdetails (inkl. Lizenz, Visibility, Default-Branch)
    - README/CONTRIBUTING in mehreren Varianten prüfen
    - Mitwirkende über Pagination zählen (per_page=100)
    - Fehler robust abfangen (404, Token fehlt, Netzwerkfehler)
    """
    print(f"🔍 Starte Analyse des GitLab-Repos: {url}")

    token = settings.GITLAB_API_TOKEN
    if not token:
        print("❌ Kein GITLAB_API_TOKEN gesetzt!")
        return {"url": url, "error": "Kein GITLAB_API_TOKEN gesetzt"}

    owner, repo = parse_gitlab_url(url)
    if not owner or not repo:
        print("❌ Fehler beim Parsen der GitLab-URL.")
        return {"url": url, "error": "Ungültige GitLab-URL"}

    project_path = f"{owner}/{repo}"
    project_path_encoded = quote_plus(project_path)

    # GitLab nutzt PRIVATE-TOKEN im Header
    headers = {"PRIVATE-TOKEN": token}
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        try:
            # ------------------------------------------------------
            # Projekt-Metadaten abrufen
            # ------------------------------------------------------
            api_url = f"https://gitlab.com/api/v4/projects/{project_path_encoded}?license=true"
            print(f"🌐 Abruf von Projekt-Metadaten: {api_url}")

            resp = await session.get(api_url)
            if resp.status != 200:
                print(f"❌ Repo nicht gefunden – Status {resp.status}")
                return {"url": url, "error": f"Repo nicht gefunden (Status {resp.status})"}

            data = await resp.json()

            license_name = (data.get("license") or {}).get("name")
            open_issues = data.get("open_issues_count")
            issues_enabled = bool(data.get("issues_enabled", False))
            default_branch = data.get("default_branch") or "main"

            # ------------------------------------------------------
            # Hilfsfunktion: Prüfe, ob Datei existiert
            # ------------------------------------------------------
            async def file_exists(path: str) -> bool:
                file_api = (
                    f"https://gitlab.com/api/v4/projects/{project_path_encoded}"
                    f"/repository/files/{quote(path, safe='')}"
                    f"?ref={quote(default_branch, safe='')}"
                )
                r = await session.get(file_api)
                return r.status == 200

            # ------------------------------------------------------
            # README prüfen
            # ------------------------------------------------------
            readme_candidates: List[str] = [
                "README.md", "Readme.md", "readme.md",
                "README.rst", "README", "docs/README.md",
            ]

            has_readme = False
            for pth in readme_candidates:
                if await file_exists(pth):
                    has_readme = True
                    break

            # ------------------------------------------------------
            # CONTRIBUTING prüfen
            # ------------------------------------------------------
            contrib_candidates: List[str] = [
                "CONTRIBUTING.md", "contributing.md",
                ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
            ]

            has_contributing_guide = False
            for pth in contrib_candidates:
                if await file_exists(pth):
                    has_contributing_guide = True
                    break

            # ------------------------------------------------------
            # Contributors mit Pagination zählen
            # GitLab gibt JSON-Listen aus.
            # X-Next-Page = "0" oder leer => Ende
            # ------------------------------------------------------
            contributors_count: Optional[int] = 0
            page = 1

            while True:
                c_url = (
                    f"https://gitlab.com/api/v4/projects/{project_path_encoded}"
                    f"/repository/contributors?per_page=100&page={page}"
                )
                cr = await session.get(c_url)

                # Leere Repos können 404 zurückgeben → Count=None bei erster Seite
                if cr.status != 200:
                    contributors_count = None if page == 1 else contributors_count
                    break

                chunk = await cr.json()
                if not chunk:
                    break

                contributors_count += len(chunk)

                nxt = cr.headers.get("X-Next-Page")
                if not nxt or nxt == "0":
                    break

                page += 1

            # ------------------------------------------------------
            # Ergebnisstruktur im gleichen Format wie GitHub
            # ------------------------------------------------------
            return {
                "url": url,
                "name": data.get("name"),
                "description": data.get("description"),
                "stars": data.get("star_count"),
                "forks": data.get("forks_count"),
                "visibility": data.get("visibility"),
                "last_activity": data.get("last_activity_at"),
                "license": license_name,
                "open_issues": open_issues,
                "has_readme": has_readme,
                "has_contributing_guide": has_contributing_guide,
                "contributors_count": contributors_count,
                "has_discussions": issues_enabled,  # FE-kompatibel
            }

        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Repo-Daten: {str(e)}")
            return {"url": url, "error": f"Fehler beim Abrufen der Repo-Daten: {str(e)}"}
