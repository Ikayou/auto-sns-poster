# auto-sns-poster

Dieses Projekt erstellt automatisch TikTok-News-Drafts aus aktuellen heise.de-Meldungen.

Der aktuelle Workflow:

1. Aktuelle Tech-News per heise.de-RSS abrufen
2. Mit der OpenAI API kurze deutsche News-Texte generieren
3. Aus HTML-Templates sieben PNG-Slides rendern
4. Die Slides zu einem MP4-Video zusammenfuegen
5. Das Video in den TikTok-Inbox-/Bearbeitungsfluss hochladen
6. Musik und KI-Label manuell in der TikTok-App setzen und posten

Das Projekt veroeffentlicht nicht direkt. Der letzte Schritt passiert bewusst in der TikTok-App.

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

Alle sichtbaren Texte auf den Bildern sind auf Deutsch.

## Projektstruktur

```text
app/
  create_carousel.py          heise.de abrufen, KI-Inhalt erzeugen, PNG-Slides rendern
  slides_to_video.py          PNG-Slides in ein MP4-Video umwandeln
  upload_to_tiktok_draft.py   Video an den TikTok-Inbox-Flow senden
  print_tiktok_auth_url.py    TikTok-OAuth-URL ausgeben
  get_token_direct.py         OAuth-code in access token umwandeln
  check_tiktok_info.py        pruefen, zu welchem TikTok-Konto der token gehoert

templates/
  heise_cover.html            Cover-Template
  single_news.html            Template fuer einzelne News-Slides
  heise_outro.html            Outro-Template

assets/
  carousel_content.json       generierter Inhalt fuer Caption und Slides

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
TIKTOK_ACCESS_TOKEN=...

TIKTOK_ACCOUNT_NAME=german.news69
TIKTOK_REDIRECT_URI=https://ikayou.github.io/tiktok-api-legal/
TIKTOK_SCOPES=user.info.basic,video.upload,video.publish

NEWS_COUNT=5
SECONDS_PER_SLIDE=8.0
```

Wichtig: `TIKTOK_ACCOUNT_NAME` ist nur der Name, der auf den Slides angezeigt wird. An welches TikTok-Konto der Draft wirklich gesendet wird, entscheidet der `TIKTOK_ACCESS_TOKEN`.

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

6. Den ausgegebenen access token in `.env` als `TIKTOK_ACCESS_TOKEN=...` speichern.
7. Das verknuepfte Konto pruefen:

```bash
python app/check_tiktok_info.py
```

Wenn `creator_username` `german.news69` ist, landet der Draft beim richtigen Konto.

## Manueller Lauf

Einen kompletten lokalen Lauf startest du so:

```bash
python app/create_carousel.py
python app/slides_to_video.py
python app/upload_to_tiktok_draft.py
```

Danach die TikTok-App oeffnen, die Inbox-Benachrichtigung auswaehlen, Musik hinzufuegen, das KI-generiert-Label aktivieren und den Beitrag posten.

## Automatischer Lauf mit GitHub Actions

Der Workflow liegt hier:

```text
.github/workflows/daily_post.yml
```

Zielzeiten in Deutschland:

```text
08:30 Europe/Berlin
17:00 Europe/Berlin
```

GitHub Actions verwendet UTC. Deshalb startet der Workflow zu mehreren UTC-Zeiten und prueft im Job selbst, ob die aktuelle Zeit in `Europe/Berlin` wirklich `08:30` oder `17:00` ist. So funktioniert der Zeitplan auch mit Sommerzeit und Winterzeit.

Manuell kann der Workflow weiterhin ueber `workflow_dispatch` in GitHub Actions gestartet werden.

## GitHub Secrets

Diese Secrets muessen im Repository gesetzt sein:

```text
OPENAI_API_KEY
TIKTOK_ACCESS_TOKEN
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

Video aus Slides erzeugen:

```bash
python app/slides_to_video.py
```

Video an TikTok-Draft-Flow senden:

```bash
python app/upload_to_tiktok_draft.py
```
