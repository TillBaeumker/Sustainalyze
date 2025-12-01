# Sustainalyze 🌿

Automated Sustainability Analysis for Digital Scholarly Editions

Sustainalyze crawlt und analysiert digitale Editionswebseiten im Hinblick auf technische und semantische Nachhaltigkeit. Es kombiniert Deep Crawling, FAIR-Analysen, FUJI, Repository-Auswertung, Normdaten-Erkennung, XML/TEI-Analyse sowie LLM-basierte Zusammenfassungen.

---

## ⚙️ Installation (lokal)

### Voraussetzungen

- Python 3.8+
- Git

### Schritt-für-Schritt Installation

1. **Repository klonen (mit Submodules)**

```bash
git clone --recurse-submodules https://github.com/TillBaeumker/Sustainalyze.git
cd Sustainalyze
```

2. **Virtuelle Umgebung erstellen**

```bash
python3 -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate
```

3. **Dependencies installieren**

```bash
pip install -r requirements.txt
```

### 🔐 Environment Variables

Erstelle eine `.env`-Datei im Projektverzeichnis:

```bash
cp .env.example .env
```

Füge folgende Variablen ein:

```ini
OPENAI_API_KEY=your_key_here
SHODAN_API_KEY=your_key_here
WAPPALYZER_API_KEY=your_key_here
FUJI_USERNAME=your_username
FUJI_PASSWORD=your_password
FUJI_URL=http://127.0.0.1:1071/fuji/api/v1/evaluate
```

### ▶️ Anwendung starten (lokal)

```bash
uvicorn app.main:app --reload --port 8000
```

Öffne dann im Browser: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🚀 Deployment (Server / CCeH)

### 1. Repository klonen

```bash
git clone --recurse-submodules https://github.com/TillBaeumker/Sustainalyze.git
cd Sustainalyze
```

### 2. Environment konfigurieren

```bash
cp .env.example .env
# .env-Datei mit deinen API-Keys editieren
```

### 3. Setup ausführen

```bash
bash setup.sh
```

### 4. Mit systemd starten (optional)

```bash
systemctl start sustainalyze
systemctl enable sustainalyze  # Auto-Start beim Booten
```

---

## 🧪 FUJI-Modus

Wenn im Frontend der "FUJI-Modus" aktiviert ist:

- Alle Datensatz-Links werden global dedupliziert
- FUJI wird nur einmal pro Datensatz ausgeführt
- Ergebnisse erscheinen im Abschnitt "FUJI FAIRNESS – Externe Datensätze"

---

## 📖 Funktionalität

Sustainalyze bietet folgende Analyse-Features:

- **Deep Crawling**: Umfassende Website-Analyse
- **FAIR-Bewertung**: Findability, Accessibility, Interoperability, Reusability
- **FUJI-Integration**: Externe Fairness-Evaluierung
- **Repository-Analyse**: Datenquellen und Verfügbarkeit
- **Normdaten-Erkennung**: Authority Files und Linked Data
- **XML/TEI-Analyse**: Struktur und Standards
- **LLM-Zusammenfassungen**: Automatische Report-Generierung

---

## 📝 Lizenz & Kontakt

Masterarbeit im Studiengang Digital Humanities / Computerlinguistik, Universität zu Köln.

**Kontakt:**

Till Bäumker  
[tbaeumke@smail.uni-koeln.de](mailto:tbaeumke@smail.uni-koeln.de)

---

## 🤝 Contributing

Contributions sind willkommen! Bitte erstelle einen Fork und öffne einen Pull Request mit deinen Verbesserungen.

---

## ⚠️ Lizenz

Bitte siehe die LICENSE-Datei für weitere Informationen.