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
RE_BUCHUNG = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+(-?[\d.]+,\d{2})$")
# Zeile 2: Valutadatum + erste Zeile Verwendungszweck
RE_VALUTA = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s*(.*)$")
# Ende der Umsatzliste auf einer Seite
RE_ENDE = re.compile(r"^(Neuer Saldo|Übertrag|Kunden-Information)\b")
RE_START = re.compile(r"^Valuta$")


def iso(datum: str) -> str:
    return datetime.strptime(datum, "%d.%m.%Y").strftime("%Y-%m-%d")


def betrag(s: str) -> str:
    # "1.234,56" -> "1234.56"
    return s.replace(".", "").replace(",", ".")


def umsaetze(pdf_path: str):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # x_tolerance klein, sonst gehen Leerzeichen verloren
            text = page.extract_text(x_tolerance=1) or ""
            aktiv, cur = False, None
            for line in (l.strip() for l in text.splitlines()):
                if RE_START.match(line):
                    aktiv = True
                    continue
                if not aktiv:
                    continue
                if RE_ENDE.match(line):
                    break
                m = RE_BUCHUNG.match(line)
                if m:
                    if cur:
                        yield cur
                    cur = {"datum": iso(m[1]), "betrag": betrag(m[3]),
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


def dateien(muster):
    """Löst Wildcards auf (sortiert, ohne Dubletten). Nicht passende Muster
    bleiben stehen, damit später eine Fehlermeldung kommt."""
    gesehen, ergebnis = set(), []
    for m in muster:
        treffer = sorted(glob.glob(m, recursive=True)) if glob.has_magic(m) else [m]
        if not treffer:
            print(f"{m}: keine passenden Dateien", file=sys.stderr)
        for t in treffer:
            key = os.path.normcase(os.path.abspath(t))
            if key not in gesehen:
                gesehen.add(key)
                ergebnis.append(t)
    return ergebnis


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", nargs="+", help="PDF-Dateien oder Wildcards, z.B. \".\\input\\*.pdf\"")
    ap.add_argument("-a", "--append", metavar="DATEI",
                    help="An Ausgabedatei anhängen (Default: stdout)")
    ap.add_argument("--sep", default="\t", help="Trennzeichen (Default: Tab)")
    ap.add_argument("--no-header", action='store_true', help="Kopfzeile unterdrücken")
    ap.add_argument("-f", "--fields", help="Feldauswahl und -reihenfolge, z.B. '<empty>,datum,buchung,betrag' (verfügbar: datum, betrag, buchung, zweck)")
    args = ap.parse_args()

    if args.append:
        neu = not os.path.exists(args.append) or os.path.getsize(args.append) == 0
        out = open(args.append, "a", encoding="utf-8")
    else:
        neu, out = True, sys.stdout

    # Feldkonfiguration verarbeiten
    if args.fields:
        felder = [f.strip() for f in args.fields.split(",")]
        header_namen = []
        for feld in felder:
            if feld == "empty":
                header_namen.append("")
            elif feld == "datum":
                header_namen.append("Datum")
            elif feld == "betrag":
                header_namen.append("Betrag")
            elif feld == "buchung":
                header_namen.append("Buchung")
            elif feld == "zweck":
                header_namen.append("Verwendungszweck")
            else:
                print(f"Unbekanntes Feld: {feld}", file=sys.stderr)
                sys.exit(1)
    else:
        felder = ["datum", "betrag", "buchung", "zweck"]
        header_namen = ["Datum", "Betrag", "Buchung", "Verwendungszweck"]

    pdfs = dateien(args.pdf)
    fehler = 0 if pdfs else 1
    try:
        if neu and not args.no_header:
            print(args.sep.join(header_namen), file=out)
        for path in pdfs:
            try:
                n = 0
                for u in umsaetze(path):
                    werte = []
                    for feld in felder:
                        if feld == "empty":
                            werte.append("")
                        elif feld == "datum":
                            werte.append(u["datum"])
                        elif feld == "betrag":
                            werte.append(u["betrag"])
                        elif feld == "buchung":
                            werte.append(u["buchung"])
                        elif feld == "zweck":
                            werte.append(u["zweck"][0] if u["zweck"] else "")
                    print(args.sep.join(werte), file=out)
                    n += 1
                print(f"{path}: {n} Umsätze", file=sys.stderr)
            except Exception as e:  # eine kaputte Datei bricht nicht alles ab
                fehler += 1
                print(f"{path}: FEHLER {e}", file=sys.stderr)
    finally:
        if out is not sys.stdout:
            out.close()
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
