# -*- coding: utf-8 -*-
"""
github_client.py
==============================

GitHub-Repository-Analyse über die GitHub REST API v3
-----------------------------------------------------

Dieses Modul extrahiert strukturierte Metadaten aus GitHub-Repositories
ausschließlich über die offiziell dokumentierte GitHub REST API.

Erfasste Informationen:
-----------------------
- Lizenz des Repositories
- Sichtbarkeit (public/private)
- README vorhanden?
- CONTRIBUTING vorhanden? (mehrere mögliche Pfade)
- Discussions aktiviert?
- Letzter Commit auf dem Default-Branch
- Anzahl der Mitwirkenden (robuste Pagination-Logik)
- Sterne, Forks, Offene Issues

"""




import aiohttp
from typing import Optional, Tuple, List
from urllib.parse import urlparse, quote
from app.core.config import settings
import re


def parse_github_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrahiert owner und repo aus einer GitHub-URL.
    Erwartete Struktur: https://github.com/<owner>/<repo>

    Rückgabe:
        (owner, repo) oder (None, None) bei ungültigen URLs.
    """
    p = urlparse(url)
    if p.netloc != "github.com":
        print(f"⚠️  Keine gültige GitHub-Domain: {url}")
        return None, None

    parts = p.path.strip("/").split("/")
    if len(parts) != 2:
        print(f"⚠️  Ungültiger GitHub-Pfad: {p.path}")
        return None, None

    return parts[0], parts[1]


async def analyze_github_repo(url: str) -> dict:
    """
    Analysiert ein GitHub-Repository über die REST-API.
    Die Ausgabe ist kompatibel für das Frontend und für dein Scoring-Modul.

    Besondere Logik:
    - Contributors werden *robust* gezählt über Pagination.
    - README/CONTRIBUTING werden über mehrere mögliche Pfade geprüft.
    - Fehler (z. B. 404, 403) werden klar zurückgegeben.
    """

    print(f"🔍 Starte Analyse des GitHub-Repos: {url}")

    token = settings.GITHUB_API_TOKEN
    if not token:
        print("❌ Kein GITHUB_API_TOKEN gesetzt!")
        return {"url": url, "error": "Kein GITHUB_API_TOKEN gesetzt"}

    owner, repo = parse_github_url(url)
    if not owner or not repo:
        return {"url": url, "error": "Ungültige GitHub-URL"}

    # Header mit Bearer Token nach GitHub-Vorgaben
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "SustainabilityCheckerBot/1.0",
    }

    base = f"https://api.github.com/repos/{owner}/{repo}"
    timeout = aiohttp.ClientTimeout(total=20)

    # -------------------------------------------------
    # Haupt-API-Session
    # -------------------------------------------------
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        try:
            # Repository-Metadaten
            r_repo = await session.get(base)
            if r_repo.status != 200:
                return {"url": url, "error": f"Repo nicht gefunden (Status {r_repo.status})"}

            repo_data = await r_repo.json()

            license_name = (repo_data.get("license") or {}).get("name")
            default_branch = repo_data.get("default_branch") or "main"
            has_discussions = bool(repo_data.get("has_discussions", False))

            # -------------------------------------------------
            # Letzter Commit auf Default-Branch
            # -------------------------------------------------
            last_commit: Optional[str] = None
            r_commits = await session.get(
                f"{base}/commits?sha={quote(default_branch, safe='')}&per_page=1"
            )
            if r_commits.status == 200:
                commits = await r_commits.json()
                if commits:
                    last_commit = commits[0]["commit"]["committer"]["date"]
            elif r_commits.status == 409:
                # Repo existiert, hat aber keine Commits
                last_commit = "repo empty (no commits)"

            # -------------------------------------------------
            # README vorhanden?
            # -------------------------------------------------
            r_readme = await session.get(f"{base}/readme")
            has_readme = (r_readme.status == 200)

            # -------------------------------------------------
            # CONTRIBUTING.md vorhanden?
            # mehrere mögliche Pfade
            # -------------------------------------------------
            contrib_candidates: List[str] = [
                "CONTRIBUTING.md",
                "contributing.md",
                ".github/CONTRIBUTING.md",
                "docs/CONTRIBUTING.md",
            ]
            has_contributing_guide = False

            for path in contrib_candidates:
                r_file = await session.get(
                    f"{base}/contents/{quote(path, safe='')}?ref={quote(default_branch, safe='')}"
                )
                if r_file.status == 200:
                    has_contributing_guide = True
                    break

            # -------------------------------------------------
            # Mitwirkende robust zählen
            # Vorgehen:
            # - per_page=1 → wenn GitHub paginiert, ist die Seitenzahl = Anzahl
            # - Link-Header mit rel="last" enthält page=<n>
            # -------------------------------------------------
            contributors_count: Optional[int] = None
            r_contrib = await session.get(f"{base}/contributors?per_page=1&anon=1")

            if r_contrib.status == 200:
                link = r_contrib.headers.get("Link")
                if link and 'rel="last"' in link:
                    # Beispiel:
                    # <...&page=42>; rel="last"
                    last_part = [p for p in link.split(",") if 'rel="last"' in p]
                    if last_part:
                        m = re.search(r"[?&]page=(\d+)", last_part[0])
                        if m:
                            contributors_count = int(m.group(1))
                else:
                    # Keine Pagination → Länge der ersten Seite (0 oder 1)
                    data = await r_contrib.json()
                    contributors_count = len(data) if isinstance(data, list) else 0

            elif r_contrib.status == 204:
                # No Content → keine Mitwirkenden
                contributors_count = 0

            elif r_contrib.status in (401, 403):
                # Rechteproblem → nicht bestimmbar
                contributors_count = None

            else:
                contributors_count = None

            # -------------------------------------------------
            # Ergebnisstruktur
            # -------------------------------------------------
            return {
                "url": url,
                "name": repo_data.get("name"),
                "full_name": repo_data.get("full_name"),
                "html_url": repo_data.get("html_url"),
                "description": repo_data.get("description"),
                "license": license_name,
                "visibility": ("public" if not repo_data.get("private", True) else "private"),
                "stars": repo_data.get("stargazers_count"),
                "forks": repo_data.get("forks_count"),
                "open_issues": repo_data.get("open_issues_count"),
                "default_branch": default_branch,
                "last_commit": last_commit,
                "has_readme": has_readme,
                "has_contributing_guide": has_contributing_guide,
                "has_discussions": has_discussions,
                "contributors": contributors_count,
                "contributors_count": contributors_count,
            }

        except Exception as e:
            return {"url": url, "error": str(e)}
