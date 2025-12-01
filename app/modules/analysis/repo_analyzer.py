# -*- coding: utf-8 -*-
"""
repo_analyzer.py
=================

Analyse externer GitHub- und GitLab-Links
-----------------------------------------

Dieses Modul identifiziert aus einer Menge externer Links
GitHub- und GitLab-Repository-URLs und analysiert diese anschließend
über ihre offiziellen REST-APIs (GitHub v3, GitLab v4).

Der Ablauf:
-----------
1. Schleife über alle externen Links
2. Erkennen von GitHub/GitLab-URLs
3. Parsen von Owner + Repo
4. API-Analyse über github_client / gitlab_client
5. Sammeln strukturierter Metadaten
6. Ausgabe in einem standardisierten Format

Zusatzfunktion:
---------------
collect_repositories(page_data)
    Aggregiert die bereits pro Seite gesammelten Repo-Daten
    (im Gesamtcrawler genutzt für die Frontend-Anzeige).
"""

# --------------------------------------------------------------
# Imports
# --------------------------------------------------------------
from app.modules.analysis.github_client import parse_github_url, analyze_github_repo
from app.modules.analysis.gitlab_client import parse_gitlab_url, analyze_gitlab_repo


# --------------------------------------------------------------
# Farbige Debug-Ausgabe für Terminal/Logs
# --------------------------------------------------------------
def c(msg, color):
    """Hilfsfunktion für farbige CLI-Ausgabe (Debug)."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "end": "\033[0m"
    }
    return f"{colors.get(color, '')}{msg}{colors['end']}"


# --------------------------------------------------------------
# Hauptfunktion: Analyse externer Links auf Repositories
# --------------------------------------------------------------
async def analyze_repos(external_links: set) -> dict:
    """
    Analysiert alle externen Links einer Seite.
    Erkennt GitHub/GitLab-Repositories und führt API-Abfragen aus.

    Rückgabe:
        {
            "github_repos": [...],
            "gitlab_repos": [...]
        }
    """
    print(c("[Repos] Starte Analyse externer Links auf GitHub/GitLab …", "blue"))
    print(c(f"[Repos] Anzahl externer Links: {len(external_links)}", "yellow"))

    github_repos = []
    gitlab_repos = []

    # ----------------------------------------------------------
    # Schleife über alle externen Links
    # ----------------------------------------------------------
    for link in external_links:
        print(c(f"[Repos] Prüfe Link: {link}", "blue"))

        # ------------------------------------------------------
        # GitHub-Erkennung
        # ------------------------------------------------------
        if link.startswith("https://github.com/"):
            print(c(f"🔍 GitHub-Link erkannt: {link}", "yellow"))

            owner, repo = parse_github_url(link)
            if not owner or not repo:
                print(c(f"⚠️ Ungültige GitHub-URL: {link}", "red"))
                continue

            print(c(f"→ Analysiere GitHub-Repo: {owner}/{repo}", "blue"))
            data = await analyze_github_repo(link)

            if data:
                github_repos.append(data)
                print(c("✅ GitHub-Analyse erfolgreich", "green"))
            else:
                print(c("⚠️ Keine Daten von GitHub zurückgegeben", "red"))

        # ------------------------------------------------------
        # GitLab-Erkennung
        # ------------------------------------------------------
        elif link.startswith("https://gitlab.com/"):
            print(c(f"🔍 GitLab-Link erkannt: {link}", "yellow"))

            owner, repo = parse_gitlab_url(link)
            if not owner or not repo:
                print(c(f"⚠️ Ungültige GitLab-URL: {link}", "red"))
                continue

            print(c(f"→ Analysiere GitLab-Repo: {owner}/{repo}", "blue"))
            data = await analyze_gitlab_repo(link)

            if data:
                gitlab_repos.append(data)
                print(c("✅ GitLab-Analyse erfolgreich", "green"))
            else:
                print(c("⚠️ Keine Daten von GitLab zurückgegeben", "red"))

        else:
            # Kein GitHub/GitLab-Link
            print(c(f"[Repos] → Kein Repository-Link: {link}", "yellow"))

    # ----------------------------------------------------------
    # Abschluss & Zusammenfassung
    # ----------------------------------------------------------
    print(c("[Repos] Analyse abgeschlossen.", "blue"))
    print(c(f"  → GitHub-Repos gefunden: {len(github_repos)}", "green"))
    print(c(f"  → GitLab-Repos gefunden: {len(gitlab_repos)}", "green"))

    return {
        "github_repos": github_repos,
        "gitlab_repos": gitlab_repos,
    }


# --------------------------------------------------------------
# Aggregation für Frontend/LLM-Auswertung
# --------------------------------------------------------------
def collect_repositories(page_data: list) -> tuple[list, list]:
    """
    Aggregiert GitHub- und GitLab-Repos aus allen Seiten,
    die der Crawler analysiert hat.

    Rückgabe:
        (github_list, gitlab_list)
    """
    print(c("[Repos] Sammle Repository-Ergebnisse aus allen Seiten …", "blue"))

    github_results = []
    gitlab_results = []

    for page in page_data:
        gh = page.get("github_repos", [])
        gl = page.get("gitlab_repos", [])

        print(c(
            f" → Seite {page.get('url', '(unknown)')} "
            f"| GitHub: {len(gh)} | GitLab: {len(gl)}",
            "yellow"
        ))

        github_results.extend(gh)
        gitlab_results.extend(gl)

    print(c("[Repos] Sammlung abgeschlossen.", "blue"))
    print(c(f"Gesamt GitHub-Repos: {len(github_results)}", "green"))
    print(c(f"Gesamt GitLab-Repos: {len(gitlab_results)}", "green"))

    return github_results, gitlab_results
