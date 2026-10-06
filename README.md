# ING Diba Kontoauszug PDF Export

## Setup

```powershell
md .venv
python -m venv .venv
pip install -r requirements.txt

# one time
playwright install

Unblock-File -Path .\.venv\Scripts\*ps1

```

## Run

```powershell
# korrekte python version
.venv/Scripts/activate.ps1

cp -r posts/01-dry posts/02-mein-thema
python build.py posts/02-mein-thema [--png]                    # --png = Vorschaubilder
```

## Beitragsordner
```
posts/02-mein-thema/
  post.yaml            Texte, Verweise auf Codedateien
  post.txt.j2          Template um Text zu überschreiben
  Beispiel.java        Seite 2 (code.file)
  Beispiel_detail.java Seite 4 (detail.file, optional)
```

Sprache fürs Highlighting kommt aus der Dateiendung, abweichend über `language:`. Highlight-Zeilen: `[3, 4]` oder `["3-5", 9]`.

