# ING Diba Kontoauszug PDF Export

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
