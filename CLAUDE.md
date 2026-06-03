# auto-sns-poster

Dieses Projekt erstellt automatisch TikTok-News-Drafts aus aktuellen Meldungen
deutschsprachiger RSS-Quellen.

## Aktueller Workflow

1. Mehrere deutsche RSS-Feeds abrufen
2. Ein Format-Agent entscheidet zwischen `digest` und `carousel`
3. OpenAI generiert kurze deutsche News-Texte
4. Ein Review-Agent prueft Faktennaehe, Sprache, Laenge und Duplikate
5. Playwright rendert HTML-Templates als PNG-Slides
6. MoviePy erzeugt aus den Slides ein MP4-Video
7. Das Video wird an den TikTok-Inbox-/Bearbeitungsfluss gesendet
8. Musik und KI-Label werden manuell in der TikTok-App gesetzt

Das Projekt postet nicht direkt. Die TikTok API kann die Bearbeitungsseite in
der App nicht automatisch oeffnen; sie sendet eine Inbox-Benachrichtigung.

## Agenten

### Format-Agent

Datei: `app/agent_runner.py`

Der Format-Agent liest die RSS-Artikel und entscheidet:

- `digest`: fuenf News auf einer einzigen Slide
- `carousel`: fuenf News auf fuenf einzelnen News-Slides, plus Cover und Outro

Der Agent darf nicht skippen. Es muss immer ein Beitrag erzeugt werden.

### Review-Agent

Datei: `app/agent_runner.py`

Der Review-Agent laeuft nach der Content-Generierung und vor dem Rendern der
Slides. Er prueft:

- keine erfundenen Fakten
- keine uebertriebene oder spekulative Sprache
- natuerliches Deutsch
- kurze Texte, besonders fuer `digest`
- keine doppelten News

Wenn er Probleme findet, stoppt er den Lauf nicht. Er korrigiert die sichtbaren
Texte und der Workflow geht weiter.

## Projektstruktur

```text
app/
  agent_runner.py                      kompletter Agent-Workflow
  fetch_content.py                     RSS-Feeds abrufen
  fetch_news.py                        kleines Hilfsskript fuer Top-News
  create_carousel.py                   Content erzeugen und PNG-Slides rendern
  slides_to_video.py                   PNG-Slides in MP4 umwandeln
  upload_to_tiktok_draft.py            Video an TikTok-Inbox-Flow senden
  tiktok_token.py                      access token per refresh token erneuern
  print_tiktok_auth_url.py             TikTok-OAuth-URL ausgeben
  get_token_direct.py                  OAuth-code in access/refresh token umwandeln
  check_tiktok_info.py                 verknuepftes TikTok-Konto pruefen

templates/
  news_digest.html                     fuenf News auf einer Slide
  single_news.html                     eine News pro Slide im Carousel
  heise_cover.html                     Cover-Template
  heise_outro.html                     Outro-Template

assets/
  agent_plan.json                      Entscheidung des Format-Agenten
  carousel_content.json                finaler Inhalt fuer Caption und Slides
  content_review.json                  Ergebnis des Review-Agenten
  NotoSansJP-Bold.ttf                  Font fuer gerenderte Slides

output/
  carousel/                            generierte PNG-Slides
  carousel_video.mp4                   fertiges TikTok-Video
```

## Wichtige Befehle

Kompletter lokaler Lauf:

```bash
python app/agent_runner.py
```

Nur Slides erzeugen:

```bash
python app/create_carousel.py
```

Slides in Video umwandeln:

```bash
python app/slides_to_video.py
```

Video an TikTok-Inbox-Flow senden:

```bash
python app/upload_to_tiktok_draft.py
```

TikTok-Konto des Tokens pruefen:

```bash
python app/check_tiktok_info.py
```

## GitHub Actions

Der automatische Lauf liegt in:

```text
.github/workflows/daily_post.yml
```

Der Workflow fuehrt den Agent-Runner aus:

```bash
python app/agent_runner.py
```

Feste UTC-Zeiten:

```text
07:30 UTC
16:00 UTC
```

Es gibt keine zusaetzliche Berlin-Zeitpruefung mehr. Jeder geplante Workflow-
Start fuehrt den Agent-Runner aus. In Deutschland verschieben sich diese Zeiten
zwischen CET und CEST um eine Stunde.

## RSS-Quellen

Die Default-Feeds stehen in `app/fetch_content.py`.

Aktuell sind mehrere deutschsprachige Quellen hinterlegt, darunter:

- heise online
- Golem.de
- Tagesschau
- DER SPIEGEL
- ZEIT Online
- Deutsche Welle

Die Feeds koennen per `.env` ueberschrieben werden:

```env
RSS_FEEDS=Name|https://example.com/rss;Andere Quelle|https://example.com/feed.xml
```

## Umgebung

Lokale `.env`:

```env
OPENAI_API_KEY=sk-...

TIKTOK_REFRESH_TOKEN=...
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
TIKTOK_ACCOUNT_NAME=german.news69

NEWS_COUNT=5
SECONDS_PER_SLIDE=8.0
AGENT_MODEL=gpt-4o-mini
REVIEW_AGENT_MODEL=gpt-4o-mini
UPLOAD_TO_TIKTOK=true
UPLOAD_TO_INSTAGRAM=false
INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_USER_ID=...
GITHUB_SLIDES_REPO=https://github.com/user/slides-repo.git
GITHUB_PAGES_BASE_URL=https://user.github.io/slides-repo
```

Fuer GitHub Actions muessen die Werte als GitHub Secrets gesetzt werden:

```text
OPENAI_API_KEY
TIKTOK_REFRESH_TOKEN
TIKTOK_CLIENT_KEY
TIKTOK_CLIENT_SECRET
TIKTOK_ACCOUNT_NAME
INSTAGRAM_ACCESS_TOKEN
INSTAGRAM_USER_ID
GITHUB_SLIDES_REPO
```

Instagram Secrets sind nur noetig, wenn `UPLOAD_TO_INSTAGRAM=true` gesetzt ist.
`GITHUB_PAGES_BASE_URL` ist dann als Repository Variable erforderlich.

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Hinweise

- Canva wird nicht mehr verwendet.
- Instagram Carousels werden optional mit `UPLOAD_TO_INSTAGRAM=true` veroeffentlicht.
- Der aktuelle Upload nutzt `FILE_UPLOAD` fuer ein MP4-Video.
- TikTok wird weiterhin als Video-Draft gesendet, nicht als Foto-Karussell.
- TikTok schickt eine Inbox-Benachrichtigung; die Bearbeitung passiert manuell
  in der TikTok-App.
- Musik kann nicht per API aus der TikTok-Musikbibliothek ausgewaehlt werden.
- Das KI-generiert-Label wird manuell in der TikTok-App aktiviert.
- Generierte Dateien in `assets/` und `output/` gehoeren nicht ins Repository.
