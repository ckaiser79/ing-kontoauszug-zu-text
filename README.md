# ING Diba Kontoauszug PDF Export

Dieses Tool extrahiert Umsätze aus ING-Kontoauszügen im PDF-Format und gibt sie als TSV aus. Die Ausgabe erfolgt als Tab-getrennte Werte mit Datum, Betrag, Buchungstext und Verwendungszweck.

Zweck ist es, die Werte in Excel oder eine Buchhaltungssoftware zu importieren.

## Setup

```powershell
md .venv
python -m venv .venv
pip install -r requirements.txt

Unblock-File -Path .\.venv\Scripts\*ps1

```

## Run

```powershell
# korrekte python version
.venv/Scripts/activate.ps1

python .\ing-pdf-kontoauszug-zu-text.py .\testdata\Kontoauszug.pdf
```
