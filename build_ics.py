#!/usr/bin/env python3
"""Convertit un export du planning Auriga (id|debut|fin|titre|type|desc|salles|profs|statut|examen) en ICS."""
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
VTIMEZONE = [
    "BEGIN:VTIMEZONE", "TZID:Europe/Paris",
    "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "TZNAME:CEST",
    "DTSTART:19700329T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
    "BEGIN:STANDARD", "TZOFFSETFROM:+0200", "TZOFFSETTO:+0100", "TZNAME:CET",
    "DTSTART:19701025T030000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
    "END:VTIMEZONE",
]

SHORT = {
    "Swarm Robotics algorithms and application in control and design of dynamical system": "Swarm Robotics",
    "Automatique : Conception des systèmes linéaires et continus": "Automatique",
    "Ingénierie des Systèmes - Innovation et créativité": "Ingénierie des Systèmes",
    "English for recruitment (pour les étudiants français)": "English",
    "Outils mathématiques avancés pour la science des données et la prise de décision - Projet de science": "Outils mathématiques",
    "Soft Skills et Gestion de projet - Conduite et gestion de projet complexe": "Soft Skills & Gestion de projet",
    "Aérodynamique : Dynamique des fluides incompressibles": "Aérodynamique",
    "Psychosociologie du travail et droit social": "Psychosociologie & droit social",
    "Introduction à la fabrication additive": "Fabrication additive",
    "Microcontrôleurs et leurs applications": "Microcontrôleurs",
    "Contrôle des Système Digitaux": "Contrôle des systèmes digitaux",
}
TENTATIVE = {"PREPLANIF", "SUPERPOSABLE_A_PLANIFIE", "SUPERPOSABLE_INTERVENANT_A_PLANIFIE"}


def esc(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):
    """Replie une ligne à 75 octets sans couper un caractère UTF-8."""
    out, cur, size = [], "", 0
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > 75:
            out.append(cur)
            cur, size = " ", 1
        cur += ch
        size += n
    out.append(cur)
    return "\r\n".join(out)


def local(iso):
    """Heure UTC d'Auriga convertie en heure de Paris."""
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(PARIS)


def hm(dt):
    return dt.strftime("%Hh%M")


def event(row, now, with_teachers):
    id_, start, end, title, typ, desc, rooms, teachers, status, exam = row
    name = SHORT.get(title, title) or desc
    if exam == "1":
        summary = f"Partiel · {name}"
    elif typ == "TOEIC":
        summary = "TOEIC"
    elif title:
        summary = f"{typ} · {name}"
    else:
        summary = name
    s, e = local(start), local(end)
    details = [title, desc]
    if with_teachers and teachers:
        details.append(teachers.replace(" + ", ", "))
    details = "\n".join(d for d in details if d)
    lines = [
        "BEGIN:VEVENT",
        f"UID:auriga-{id_}@ipsa-planning",
        f"DTSTAMP:{now}",
        f"DTSTART;TZID=Europe/Paris:{s.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/Paris:{e.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{esc(summary)}",
        f"LOCATION:{esc(rooms.replace(' + ', ', '))}",
        f"DESCRIPTION:{esc(details)}",
        f"STATUS:{'TENTATIVE' if status in TENTATIVE else 'CONFIRMED'}",
        "END:VEVENT",
    ]
    return lines


def main(src, dst, with_teachers):
    rows = [l.rstrip("\n").split("|") for l in open(src, encoding="utf-8") if l.strip()]
    bad = [r for r in rows if len(r) != 10]
    if bad or len({r[0] for r in rows}) != len(rows):
        sys.exit(f"Export invalide : {len(bad)} ligne(s) mal formée(s) ou id en double")
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Planning IPSA//Auriga ICS//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Cours IPSA",
        "X-WR-TIMEZONE:Europe/Paris",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
        "X-PUBLISHED-TTL:PT6H",
    ] + VTIMEZONE
    for r in rows:
        lines += event(r, now, with_teachers)
    lines.append("END:VCALENDAR")
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(fold(l) for l in lines) + "\r\n")
    print(f"{len(rows)} événements écrits dans {dst}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--teachers"]
    main(args[0], args[1], "--teachers" in sys.argv)
