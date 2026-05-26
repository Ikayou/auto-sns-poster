# auto-sns-poster

Automatische tägliche Generierung und Veröffentlichung von Kurzvideos und Karussell-Beiträgen für TikTok.

## Übersicht

Dieses Projekt sammelt täglich aktuelle Nachrichtenartikel über RSS-Feeds, erstellt mithilfe der OpenAI API ansprechende Inhalte und veröffentlicht diese automatisch als Foto-Karussell auf TikTok. Die Slide-Bilder werden mit Canva erstellt und über GitHub Pages gehostet.

## Projektstruktur

```
app/
  create_canva_carousel.py   # Schritt 1: RSS → KI-Inhalt → JSON speichern
  canva_auth.py              # Canva Connect API OAuth-Authentifizierung
  create_carousel.py         # Alternativ: HTML-Vorlagen → PNG (Playwright)
  post_tiktok_carousel.py    # TikTok-Veröffentlichung (GitHub Pages → TikTok API)
  fetch_content.py           # RSS-Feeds abrufen
  create_video.py            # Klassische Video-Pipeline (MP4)
  post_to_sns.py             # Instagram Reels Veröffentlichung
  get_token_direct.py        # TikTok OAuth-Token abrufen
  run_daily.py               # Täglicher Scheduler (07:00 Uhr)
templates/
  slide_title.html           # Titelfolie
  slide_content.html         # Inhaltsfolien
  slide_cta.html             # Abschlussfolie (Call to Action)
assets/
  NotoSansJP-Bold.ttf        # Japanische Schriftart für Untertitel
output/
  carousel/                  # Erzeugte Slide-PNGs
```

## Täglicher Arbeitsablauf

### Schritt 1 — Nachrichtenartikel abrufen & KI-Inhalt generieren

```powershell
python app/create_canva_carousel.py
```

Ruft RSS-Feeds ab, wählt den viralsten Artikel aus und speichert die Slide-Struktur unter `assets/carousel_content.json`.

### Schritt 2 — Slides in Canva erstellen

In Claude Code eingeben:

```
/make-canva-slides
```

Erstellt automatisch alle Slides mit den Canva-Vorlagen und speichert die PNGs unter `output/carousel/`.

### Schritt 3 — Auf TikTok veröffentlichen

```powershell
python app/post_tiktok_carousel.py
```

Lädt die PNGs auf GitHub Pages hoch und veröffentlicht das Karussell über die TikTok Content Posting API.

## Einrichtung

### Voraussetzungen

- Python 3.12+
- Git
- Ein GitHub-Repository mit aktivierten GitHub Pages
- OpenAI API-Schlüssel
- TikTok Developer-App mit `video.upload`-Berechtigung
- Canva-Konto (für Canva MCP in Claude Code)

### Installation

```powershell
pip install -r requirements.txt
playwright install chromium
```

### Umgebungsvariablen (`.env`)

Erstelle eine `.env`-Datei im Projektverzeichnis:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# TikTok
TIKTOK_ACCESS_TOKEN=act....
CLIENT_KEY=...
CLIENT_SECRET=...

# GitHub Pages (Bild-Hosting für TikTok)
GITHUB_SLIDES_DIR=/pfad/zum/lokalen/tiktok-slides-repo
GITHUB_PAGES_BASE_URL=https://dein-benutzername.github.io/tiktok-slides

# TikTok-Kontoname (für CTA-Folie)
TIKTOK_ACCOUNT_NAME=dein_tiktok
```

### GitHub Pages einrichten (einmalig)

1. Repository erstellen (z. B. `dein-benutzername/tiktok-slides`) und GitHub Pages aktivieren
2. Repository lokal klonen:
   ```bash
   git clone https://github.com/dein-benutzername/tiktok-slides ~/tiktok-slides
   ```
3. Im TikTok Developer Portal unter **URL properties** den Prefix `https://dein-benutzername.github.io/tiktok-slides/` registrieren und verifizieren

### Canva-Vorlagen einrichten (einmalig)

Drei Vorlagen wurden bereits erstellt und sind in Claude Code verfügbar:

| Folie | Design-ID |
|-------|-----------|
| Titelfolie | `DAHKwLcEEmA` |
| Inhaltsfolie | `DAHKwGZP6uw` |
| CTA-Folie | `DAHKwHaO_so` |

## Abhängigkeiten

```
openai        # KI-Generierung (Text, Bild, Audio)
moviepy       # Videozusammenstellung
pillow        # Bildbearbeitung
python-dotenv
requests
feedparser    # RSS-Abruf
playwright    # HTML → PNG (Fallback)
```

## Hinweise

- `.env` **niemals** in Git einchecken — alle Geheimnisse bleiben lokal
- `assets/` und `output/` sind in `.gitignore` eingetragen
- TikTok Access Token läuft ab — regelmäßig mit `get_token_direct.py` erneuern
- Für den automatischen Tagesbetrieb `run_daily.py` als Dienst einrichten
