#!/usr/bin/env python3
"""Extrahiert Umsätze aus ING-Kontoauszügen (PDF) als Text.

Ausgabe je Umsatz (Tab-getrennt):
    Datum (yyyy-mm-dd)  Betrag  Buchung  Verwendungszweck

Aufruf:
    python ing-pdf-kontoauszug-zu-text.py auszug1.pdf [auszug2.pdf ...] [-a umsaetze.tsv]
    python .\\ing-pdf-kontoauszug-zu-text.py ".\\input\\*.pdf" -a umsaetze.tsv

Wildcards (*, ?, [..], **) werden vom Script selbst aufgelöst, damit das
auch unter Windows/PowerShell funktioniert (dort expandiert die Shell nicht).

Ohne -a geht die Ausgabe nach stdout. Mit -a wird an die Datei angehängt;
die Kopfzeile wird nur geschrieben, wenn die Datei neu oder leer ist.

Abhängigkeit: pip install pdfplumber
"""
import argparse
import glob
import os
import re
import sys
from datetime import datetime

import pdfplumber

# Zeile 1 eines Umsatzes: Buchungsdatum, Buchungstext, Betrag
RE_BUCHUNG = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+\(?(-?[\d.]+,\d{2})\)?$")
# Zeile 2: Valutadatum + erste Zeile Verwendungszweck
RE_VALUTA = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s*(.*)$")
# Ende der Umsatzliste auf einer Seite
RE_ENDE = re.compile(r"^(Neuer Saldo|Übertrag|Kunden-Information)\b")
RE_START = re.compile(r"^Valuta$")


def iso(date: str) -> str:
    return datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")


def amount(s: str) -> str:
    # "1.234,56" -> "1234,56"
    return s.replace(".", "")


def transactions(pdf_path: str, verbose: bool = False):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # x_tolerance klein, sonst gehen Leerzeichen verloren
            text = page.extract_text(x_tolerance=1) or ""

            if verbose:
                print(f"=== DEBUG: Seite aus {pdf_path} ===", file=sys.stderr)
                print(text, file=sys.stderr)
                print("=== ENDE DEBUG ===", file=sys.stderr)

            active, cur = False, None
            for line in (l.strip() for l in text.splitlines()):
                
                if RE_START.match(line):
                    active = True
                    continue
                
                if not active:
                    continue
                
                if RE_ENDE.match(line):
                    break

                m = RE_BUCHUNG.match(line)

                if m:
                    
                    if cur:
                        yield cur
                    
                    cur = {"datum": iso(m[1]), "betrag": amount(m[3]),
                           "buchung": m[2], "zweck": [], "valuta": False}
                    continue
                
                if cur is None:
                    continue
                
                m = RE_VALUTA.match(line)
                
                if m and not cur["valuta"]:
                    cur["valuta"] = True
                    
                    if m[2]:
                        cur["zweck"].append(m[2])
                
                else:
                    cur["zweck"].append(line)

            if cur:
                yield cur


def files(patterns):
    """Löst Wildcards auf (sortiert, ohne Dubletten). Nicht passende Muster
    bleiben stehen, damit später eine Fehlermeldung kommt."""
    seen, result = set(), []
    
    for pattern in patterns:
        matches = sorted(glob.glob(pattern, recursive=True)) if glob.has_magic(pattern) else [pattern]
        
        if not matches:
            print(f"{pattern}: keine passenden Dateien", file=sys.stderr)
        
        for match in matches:
            key = os.path.normcase(os.path.abspath(match))
            
            if key not in seen:
                seen.add(key)
                result.append(match)
    
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", nargs="+", help="PDF-Dateien oder Wildcards, z.B. \".\\input\\*.pdf\"")
    ap.add_argument("-a", "--append", metavar="DATEI",
                    help="An Ausgabedatei anhängen (Default: stdout)")
    ap.add_argument("--sep", default="\t", help="Trennzeichen (Default: Tab)")
    ap.add_argument("-f", "--fields", help="Feldauswahl und -reihenfolge, z.B. '<empty>,datum,buchung,betrag' (verfügbar: datum, betrag, buchung, zweck)")
    ap.add_argument("-v", "--verbose", action="store_true", help="Debug-Ausgabe aktivieren")
    args = ap.parse_args()

    if args.append:
        new = not os.path.exists(args.append) or os.path.getsize(args.append) == 0
        out = open(args.append, "a", encoding="utf-8")
    
    else:
        new, out = True, sys.stdout

    # Feldkonfiguration verarbeiten
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",")]
        
        for field in fields:
            
            if field not in ["empty", "datum", "betrag", "buchung", "zweck"]:
                print(f"Unbekanntes Feld: {field}", file=sys.stderr)
                sys.exit(1)
    
    else:
        fields = ["datum", "betrag", "buchung", "zweck"]

    pdfs = files(args.pdf)
    errors = 0 if pdfs else 1
    
    try:
        
        for path in pdfs:
            
            try:
                n = 0
                
                for transaction in transactions(path, args.verbose):
                    values = []
                    
                    for field in fields:
                        
                        if field == "empty":
                            values.append("")
                        
                        elif field == "datum":
                            values.append(transaction["datum"])
                        
                        elif field == "betrag":
                            values.append(transaction["betrag"])
                        
                        elif field == "buchung":
                            values.append(transaction["buchung"])
                        
                        elif field == "zweck":
                            values.append(transaction["zweck"][0] if transaction["zweck"] else "")
                    
                    print(args.sep.join(values), file=out)
                    n += 1
                
                print(f"{path}: {n} Umsätze", file=sys.stderr)
            
            except Exception as e:  # eine kaputte Datei bricht nicht alles ab
                errors += 1
                print(f"{path}: FEHLER {e}", file=sys.stderr)
    
    finally:
        
        if out is not sys.stdout:
            out.close()
    
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
