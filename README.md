# auto-sns-poster

Dieses Projekt erstellt automatisch TikTok-News-Drafts aus aktuellen Meldungen
deutschsprachiger RSS-Quellen.

Der aktuelle Workflow:

1. Aktuelle Meldungen aus mehreren deutschen RSS-Quellen abrufen
2. Ein OpenAI-Agent entscheidet zwischen einer Top-5-Digest-Karte und Carousel-Video
3. Mit der OpenAI API kurze deutsche News-Texte generieren
4. Ein zweiter OpenAI-Agent prueft Faktennaehe, Sprache, Laenge und Duplikate
5. Aus HTML-Templates PNG-Slides rendern
6. Die Slides zu einem MP4-Video zusammenfuegen
7. Das Video in den TikTok-Inbox-/Bearbeitungsfluss hochladen
8. Musik und KI-Label manuell in der TikTok-App setzen und posten

Das Projekt veroeffentlicht nicht direkt. Die TikTok API kann die App nicht
automatisch auf der Bearbeitungsseite oeffnen; sie sendet eine Inbox-
Benachrichtigung, aus der der Bearbeitungsfluss manuell gestartet wird.

## Ergebnis

Bei jedem Lauf entstehen diese Dateien:

```text
output/carousel/slide_01.png   Cover
output/carousel/slide_02.png   News 1
output/carousel/slide_03.png   News 2
output/carousel/slide_04.png   News 3
output/carousel/slide_05.png   News 4
output/carousel/slide_06.png   News 5
output/carousel/slide_07.png   Outro
output/carousel_video.mp4      fertiges TikTok-Video
```

Wenn der Agent `digest` waehlt, entstehen fuenf News auf einer einzigen Slide
plus Video. Wenn er `carousel` waehlt, entsteht der gewohnte Ablauf mit Cover,
fuenf einzelnen News-Slides und Outro.

Alle sichtbaren Texte auf den Bildern sind auf Deutsch.

## Projektstruktur

```text
app/
  agent_runner.py             kompletter Agent-Workflow: RSS, Entscheidung, Slides, Video, Upload
  create_carousel.py          RSS abrufen, KI-Inhalt erzeugen, PNG-Slides rendern
  slides_to_video.py          PNG-Slides in ein MP4-Video umwandeln
  upload_to_tiktok_draft.py   Video an den TikTok-Inbox-Flow senden
  tiktok_token.py             access token per refresh token erneuern
  print_tiktok_auth_url.py    TikTok-OAuth-URL ausgeben
  get_token_direct.py         OAuth-code in access/refresh token umwandeln
  check_tiktok_info.py        pruefen, zu welchem TikTok-Konto der token gehoert

templates/
  heise_cover.html            Cover-Template
  news_digest.html            Template fuer fuenf News auf einer Slide
  single_news.html            Template fuer einzelne News-Slides im Carousel
  heise_outro.html            Outro-Template

assets/
  agent_plan.json             Entscheidung des Format-Agenten
  carousel_content.json       generierter Inhalt fuer Caption und Slides
  content_review.json         Ergebnis des Inhalt-Review-Agenten

output/
  carousel/                   generierte PNG-Slides
  carousel_video.mp4          generiertes Video
```

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

Fuer GitHub Actions werden die gleichen Zugangsdaten als GitHub Secrets benoetigt.

## Lokale .env

Fuer lokale Tests wird eine `.env` im Projektordner verwendet.

```env
OPENAI_API_KEY=sk-...

CLIENT_KEY=...
CLIENT_SECRET=...
CODE=...
TIKTOK_REFRESH_TOKEN=...
TIKTOK_ACCESS_TOKEN=...  # optional, nur fuer kurze lokale Tests

TIKTOK_ACCOUNT_NAME=german.news69
TIKTOK_REDIRECT_URI=https://ikayou.github.io/tiktok-api-legal/
TIKTOK_SCOPES=user.info.basic,video.upload,video.publish

NEWS_COUNT=5
SECONDS_PER_SLIDE=8.0
AGENT_MODEL=gpt-4o-mini
REVIEW_AGENT_MODEL=gpt-4o-mini
UPLOAD_TO_TIKTOK=true

# Optional: RSS-Quellen ueberschreiben
# Format: Name|URL;Name|URL
RSS_FEEDS=heise online|https://www.heise.de/newsticker/heise-atom.xml;Golem.de|https://rss.golem.de/rss.php?feed=RSS2.0
```

Wichtig: `TIKTOK_ACCOUNT_NAME` ist nur der Name, der auf den Slides angezeigt wird. An welches TikTok-Konto der Draft wirklich gesendet wird, entscheidet der TikTok OAuth token.

## TikTok-Authentifizierung

Wenn Drafts an `german.news69` gehen sollen, muss die OAuth-Freigabe im normalen TikTok-Konto `german.news69` erfolgen.

1. Im Browser bei TikTok als `german.news69` einloggen.
2. Die Auth-URL ausgeben:

```bash
python app/print_tiktok_auth_url.py
```

3. Die angezeigte URL oeffnen und die Berechtigungen erlauben.
4. Nach der Weiterleitung den Wert aus `code=...` in `.env` als `CODE=...` speichern.
5. Den code sofort in einen token umwandeln:

```bash
python app/get_token_direct.py
```

6. Den ausgegebenen refresh token in `.env` als `TIKTOK_REFRESH_TOKEN=...` speichern.
7. Das verknuepfte Konto pruefen:

```bash
python app/check_tiktok_info.py
```

Wenn `creator_username` `german.news69` ist, landet der Draft beim richtigen Konto.

Der access token laeuft schnell ab. Fuer automatische Laeufe wird deshalb der refresh token gespeichert; der Code erstellt bei jedem Lauf selbst einen frischen access token.

## Manueller Lauf

Einen kompletten lokalen Lauf mit Agent startest du so:

```bash
python app/agent_runner.py
```

Danach die TikTok-App oeffnen, die Inbox-Benachrichtigung auswaehlen, Musik hinzufuegen, das KI-generiert-Label aktivieren und den Beitrag posten.

## Automatischer Lauf mit GitHub Actions

Der Workflow liegt hier:

```text
.github/workflows/daily_post.yml
```

Zielzeiten in Deutschland:

```text
08:30-09:00 Europe/Berlin
17:00-17:30 Europe/Berlin
```

GitHub Actions verwendet UTC. Deshalb startet der Workflow zu mehreren UTC-Zeiten und prueft im Job selbst, ob die aktuelle Zeit in `Europe/Berlin` im erlaubten Zeitfenster liegt. So funktioniert der Zeitplan auch mit Sommerzeit und Winterzeit.

Manuell kann der Workflow weiterhin ueber `workflow_dispatch` in GitHub Actions gestartet werden.

## GitHub Secrets

Diese Secrets muessen im Repository gesetzt sein:

```text
OPENAI_API_KEY
TIKTOK_REFRESH_TOKEN
TIKTOK_CLIENT_KEY
TIKTOK_CLIENT_SECRET
TIKTOK_ACCOUNT_NAME
```

`TIKTOK_ACCOUNT_NAME` sollte aktuell so gesetzt sein:

```text
german.news69
```

Die lokale `.env` wird von GitHub Actions nicht gelesen. Werte, die im automatischen Workflow gebraucht werden, muessen einzeln als GitHub Secret eingetragen werden.

## Hinweise zu TikTok

- Der aktuelle Upload nutzt `FILE_UPLOAD` fuer ein MP4-Video.
- Es wird kein Foto-Karussell direkt gepostet.
- Der API-Upload sendet eine Inbox-Benachrichtigung. Die Bearbeitungsseite wird
  nicht automatisch auf dem Handy geoeffnet.
- Musik kann nicht per API aus der TikTok-Musikbibliothek ausgewaehlt werden.
- Das KI-generiert-Label wird manuell in der TikTok-App aktiviert.
- Wenn Drafts beim falschen Konto ankommen, wurde der token mit dem falschen TikTok-Konto erstellt.

## Nicht versionierte Dateien

Generierte Dateien werden nicht ins Git-Repository aufgenommen:

```text
assets/*
output/*
```

`.env` darf ebenfalls nie committet werden.

## Nuetzliche Befehle

TikTok-Konto des tokens pruefen:

```bash
python app/check_tiktok_info.py
```

Slides neu erzeugen:

```bash
python app/create_carousel.py
```

Kompletten Agent-Lauf starten:

```bash
python app/agent_runner.py
```

Video aus Slides erzeugen:

```bash
python app/slides_to_video.py
```

Video an TikTok-Draft-Flow senden:

```bash
python app/upload_to_tiktok_draft.py
```
