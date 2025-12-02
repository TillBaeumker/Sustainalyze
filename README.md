# Sustainalyze 🌿  
Automated Sustainability Analysis for Digital Scholarly Editions

Sustainalyze crawlt und analysiert digitale Editionswebseiten im Hinblick auf technische, strukturelle und semantische Nachhaltigkeit.  
Es kombiniert Deep Crawling, FAIR-Analysen, FUJI, Repository-Auswertung, Normdaten-Erkennung, XML/TEI-Analyse sowie LLM-basierte Zusammenfassungen.

---

# ⚙️ Installation (lokal, WSL/Ubuntu & Linux)

Sustainalyze enthält alles, was benötigt wird – inklusive **lokalem FUJI-Server** und **lokalem Wappalyzer**.  
Keine Submodules. Kein manuelles Setup. Vollständig reproduzierbar.

## 🧩 Voraussetzungen

- Linux oder WSL2 mit Ubuntu 22.04/24.04  
- Python **3.12**  
- Git  
- Node.js (wird automatisch installiert)  
- Chromium / Playwright (wird durch Setup geprüft)

---

# 🚀 Schnellstart (empfohlen)

```bash
git clone https://github.com/TillBaeumker/Sustainalyze.git
cd Sustainalyze
```

### 🛠 1. Shell-Skripte nutzbar machen (CRLF → LF + executable)

Falls du das Repo **unter Windows** heruntergeladen hast:

```bash
sed -i 's/\r$//' *.sh
chmod +x *.sh
```

ODER allgemeiner:

```bash
sed -i 's/\r$//' setup.sh start_all.sh reset_all.sh status.sh
chmod +x setup.sh start_all.sh reset_all.sh status.sh
```

### ⚙️ 2. Setup installieren

```bash
./setup.sh
```

Das Setup installiert:

- Python venv  
- Crawl4AI  
- FUJI (lokal aus dem Repo, kein pip fetch!)  
- Wappalyzer (lokal)  
- Node/Yarn dependencies  
- Playwright-Unterstützung  

### 🔐 3. Environment-Datei einrichten

```bash
cp .env.example .env
nano .env
```

Trage deine Keys ein:

```ini
OPENAI_API_KEY=dein_key
SHODAN_API_KEY=optional
FUJI_USERNAME=admin
FUJI_PASSWORD=admin
FUJI_URL=http://127.0.0.1:1071/fuji/api/v1/evaluate
```

---

# ▶️ Anwendung starten

```bash
./start_all.sh
```

Dies startet:

- **lokalen FUJI-Server** (Port 1071)
- **FastAPI Backend** (Port 8000)

Öffne im Browser:

👉 http://127.0.0.1:8000

---

# 🧪 FUJI-Modus

Wenn im Frontend der „FUJI-Modus“ aktiviert ist:

- Alle externen Datensatz-URLs werden dedupliziert  
- FUJI wird für jeden Datensatz exakt **einmal** ausgeführt  
- Ergebnisse erscheinen im Abschnitt **„FUJI FAIRNESS – Externe Datensätze“**

---

# 📖 Funktionsumfang

Sustainalyze analysiert digitale Editionen anhand von mehr als **40 Einzelindikatoren**:

### 🔍 Crawler  
- Deep Crawling (Crawl4AI BFS)  
- Linkstatus + tote Links  
- externe Links, Domains, Ressourcen  

### 📦 Dateien & Formate  
- XML/TEI-Erkennung  
- Downloadbare Ressourcen  
- Metadatenformate  

### 💾 Repositories  
- GitHub/GitLab Analyse  
- Commits, README, Lizenz, Contributors, Issues  
- Entwicklungsaktivität  

### 🧪 FAIR-Analyse  
- FUJI FAIR Data Evaluation Framework  
- Interne FAIR-Eigenschaften (Struktur, PIDs, Lizenz, Metadaten)  
- externe Datensätze (FUJI)  

### 🧠 LLM-basierte Zusammenfassungen  
- Projektbeschreibung  
- Institutionen  
- Rollen & Verantwortlichkeiten  
- nachhaltigkeitsbezogene Bewertung  

---

# ⛓ Shellskripte unter Linux/WSL ausführbar machen

Falls du das Repo unter Windows ausgecheckt hast, haben `.sh` Dateien oft **CRLF**  
→ Linux kann sie nicht ausführen.

Fix:

```bash
sed -i 's/\r$//' *.sh
chmod +x *.sh
```

oder vollständig:

```bash
sed -i 's/\r$//' setup.sh start_all.sh status.sh reset_all.sh
chmod +x setup.sh start_all.sh status.sh reset_all.sh
```

---

# 🤝 Contributing

Pull Requests sind willkommen!  
Bitte immer eigenes Feature-Branch + klaren Commit.

---

# 📄 Lizenz & Kontakt

Masterarbeit Digital Humanities / Computerlinguistik  
Universität zu Köln

Kontakt:  
**Till Bäumker**  
[tbaeumke@smail.uni-koeln.de](mailto:tbaeumke@smail.uni-koeln.de)
