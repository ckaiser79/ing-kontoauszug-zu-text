#!/usr/bin/env python3
"""Extrahiert Umsätze aus ING-Kontoauszügen (PDF) als Text.

Ausgabe je Umsatz (Tab-getrennt):
    Datum (yyyy-mm-dd)  Betrag  Buchung  Verwendungszweck

Aufruf:
    python ing_umsaetze.py auszug1.pdf [auszug2.pdf ...] [-o out.tsv]

Abhängigkeit: pip install pdfplumber
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", nargs="+")
    ap.add_argument("-o", "--output", help="Ausgabedatei (Default: stdout)")
    ap.add_argument("--sep", default="\t", help="Trennzeichen (Default: Tab)")
    ap.add_argument("--header", action='store_true')
    args = ap.parse_args()

    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        if(args.header):
            print(args.sep.join(["Datum", "Betrag", "Buchung", "Verwendungszweck"]), file=out)
            
        for path in args.pdf:
            for u in umsaetze(path):
                print(args.sep.join([u["datum"], u["betrag"], u["buchung"],
                                     u["zweck"][0] if u["zweck"] else ""]), file=out)
    finally:
        if out is not sys.stdout:
            out.close()


if __name__ == "__main__":
    main()
