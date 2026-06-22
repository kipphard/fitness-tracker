"""One-time importer: free-exercise-db -> our vendored exercise library.

Run manually to (re)generate ``backend/workouts/data/exercises.json`` from the
public-domain `yuhonas/free-exercise-db` dump. Not imported at runtime.

    # fetch the source once:
    curl -sSL https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json \
        -o /tmp/exercises.src.json
    python -m backend.workouts.import_library /tmp/exercises.src.json

German names are produced by a deterministic, compositional translator (best-effort —
exercise names are mostly "equipment + movement + modifier" so token replacement covers
the long tail). The English ``name`` stays canonical; ``name_de`` is the display name for
German and is hand-correctable in the committed JSON afterwards.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "exercises.json"

# Full-name overrides where compositional translation reads awkwardly. Checked first.
NAME_OVERRIDES: dict[str, str] = {
    "Pullups": "Klimmzüge",
    "Pull-up": "Klimmzug",
    "Chin-Up": "Klimmzug (Untergriff)",
    "Pushups": "Liegestütze",
    "Push-Up": "Liegestütz",
    "Plank": "Unterarmstütz",
    "Side Plank": "Seitlicher Unterarmstütz",
    "Burpee": "Burpee",
    "Mountain Climber": "Bergsteiger",
    "Russian Twist": "Russischer Twist",
    "Good Morning": "Good Morning",
    "Farmers Walk": "Farmer's Walk",
    "Superman": "Superman",
    "Crunch": "Crunch",
    "Bicycle Crunch": "Fahrrad-Crunch",
}

# Multi-word phrases, longest first. Applied before single-word tokens.
PHRASES: dict[str, str] = {
    "smith machine": "Smith-Maschine",
    "bench press": "Bankdrücken",
    "incline bench press": "Schrägbankdrücken",
    "decline bench press": "Negativ-Bankdrücken",
    "close-grip": "enger Griff",
    "close grip": "enger Griff",
    "wide-grip": "weiter Griff",
    "wide grip": "weiter Griff",
    "reverse grip": "Untergriff",
    "neutral grip": "neutraler Griff",
    "bent over": "vorgebeugt",
    "bent-over": "vorgebeugt",
    "single leg": "einbeinig",
    "single-leg": "einbeinig",
    "single arm": "einarmig",
    "single-arm": "einarmig",
    "one arm": "einarmig",
    "one-arm": "einarmig",
    "one leg": "einbeinig",
    "lateral raise": "Seitheben",
    "front raise": "Frontheben",
    "rear delt": "hintere Schulter",
    "leg press": "Beinpresse",
    "leg curl": "Beinbeuger",
    "leg extension": "Beinstrecker",
    "leg raise": "Beinheben",
    "calf raise": "Wadenheben",
    "lat pulldown": "Latzug",
    "pull down": "Latzug",
    "pull-down": "Latzug",
    "tricep pushdown": "Trizepsdrücken (Kabel)",
    "triceps pushdown": "Trizepsdrücken (Kabel)",
    "push down": "drücken",
    "push-down": "drücken",
    "face pull": "Face Pull",
    "hip thrust": "Hüftstoß",
    "good morning": "Good Morning",
    "romanian deadlift": "Rumänisches Kreuzheben",
    "sumo deadlift": "Sumo-Kreuzheben",
    "stiff leg deadlift": "Gestrecktes Kreuzheben",
    "stiff-legged deadlift": "Gestrecktes Kreuzheben",
    "overhead press": "Überkopfdrücken",
    "shoulder press": "Schulterdrücken",
    "military press": "Military Press",
    "preacher curl": "Scott-Curl",
    "hammer curl": "Hammercurl",
    "concentration curl": "Konzentrationscurl",
    "wrist curl": "Handgelenkcurl",
    "skull crusher": "French Press",
    "tricep extension": "Trizepsstrecken",
    "triceps extension": "Trizepsstrecken",
    "upright row": "aufrechtes Rudern",
    "seated row": "Rudern sitzend",
    "cable row": "Kabelrudern",
    "t-bar row": "T-Bar-Rudern",
    "pull ups": "Klimmzüge",
    "pull-ups": "Klimmzüge",
    "pullups": "Klimmzüge",
    "pull up": "Klimmzug",
    "pull-up": "Klimmzug",
    "chin ups": "Klimmzüge (Untergriff)",
    "chin-ups": "Klimmzüge (Untergriff)",
    "chin up": "Klimmzug (Untergriff)",
    "chin-up": "Klimmzug (Untergriff)",
    "push ups": "Liegestütze",
    "push-ups": "Liegestütze",
    "pushups": "Liegestütze",
    "push up": "Liegestütz",
    "push-up": "Liegestütz",
    "sit ups": "Sit-ups",
    "sit-ups": "Sit-ups",
    "sit up": "Sit-up",
    "sit-up": "Sit-up",
    "step ups": "Step-ups",
    "step-ups": "Step-ups",
    "step up": "Step-up",
    "step-up": "Step-up",
    "box jump": "Box Jump",
    "power clean": "Power Clean",
    "clean and jerk": "Umsetzen und Stoßen",
    "clean and press": "Umsetzen und Drücken",
    "front squat": "Frontkniebeuge",
    "back squat": "Kniebeuge",
    "split squat": "Split-Kniebeuge",
    "goblet squat": "Goblet-Kniebeuge",
    "hack squat": "Hackenschmidt-Kniebeuge",
    "walking lunge": "ausschreitender Ausfallschritt",
    "shoulder raise": "Schulterheben",
}

# Single-word tokens.
WORDS: dict[str, str] = {
    # equipment
    "barbell": "Langhantel",
    "dumbbell": "Kurzhantel",
    "dumbbells": "Kurzhanteln",
    "cable": "Kabel",
    "machine": "Maschine",
    "kettlebell": "Kettlebell",
    "kettlebells": "Kettlebells",
    "band": "Band",
    "bands": "Bänder",
    "lever": "Hebel",
    "sled": "Schlitten",
    "weighted": "gewichtet",
    "bodyweight": "Körpergewicht",
    "ez-bar": "SZ-Stange",
    "ez": "SZ",
    # movements
    "press": "Drücken",
    "bench": "Bank",
    "squat": "Kniebeuge",
    "squats": "Kniebeugen",
    "deadlift": "Kreuzheben",
    "row": "Rudern",
    "rows": "Rudern",
    "curl": "Curl",
    "curls": "Curls",
    "extension": "Strecken",
    "extensions": "Strecken",
    "raise": "Heben",
    "raises": "Heben",
    "lunge": "Ausfallschritt",
    "lunges": "Ausfallschritte",
    "fly": "Fliegende",
    "flye": "Fliegende",
    "flyes": "Fliegende",
    "flys": "Fliegende",
    "dip": "Dip",
    "dips": "Dips",
    "shrug": "Schulterheben",
    "shrugs": "Schulterheben",
    "kickback": "Kickback",
    "kickbacks": "Kickbacks",
    "pulldown": "Latzug",
    "pushdown": "Drücken",
    "pullover": "Überzug",
    "thrust": "Stoß",
    "hold": "Halten",
    "carry": "Tragen",
    "twist": "Drehung",
    "bridge": "Brücke",
    "crunch": "Crunch",
    "crunches": "Crunches",
    "stretch": "Dehnung",
    "jump": "Sprung",
    "clean": "Umsetzen",
    "jerk": "Stoßen",
    "snatch": "Reißen",
    "swing": "Schwung",
    "pushup": "Liegestütz",
    "pushups": "Liegestütze",
    "pullup": "Klimmzug",
    "pullups": "Klimmzüge",
    "chinup": "Klimmzug",
    "situp": "Sit-up",
    "situps": "Sit-ups",
    "rotation": "Rotation",
    "circles": "Kreisen",
    "walk": "Gang",
    "march": "Marsch",
    "bend": "Beuge",
    "bends": "Beugen",
    "hops": "Hüpfer",
    "hop": "Hüpfer",
    "hang": "hängend",
    "hanging": "hängend",
    "presses": "Drücken",
    "lift": "Heben",
    "lifts": "Heben",
    "treadmill": "Laufband",
    "throw": "Wurf",
    "slam": "Slam",
    "drive": "Drive",
    "pump": "Pump",
    "flutter": "Flatter",
    "scissor": "Schere",
    "scissors": "Schere",
    # modifiers / positions
    "incline": "Schräg",
    "decline": "Negativ",
    "flat": "Flach",
    "seated": "sitzend",
    "standing": "stehend",
    "lying": "liegend",
    "kneeling": "kniend",
    "reverse": "umgekehrt",
    "overhead": "Überkopf",
    "front": "Front",
    "rear": "hinter",
    "side": "seitlich",
    "lateral": "seitlich",
    "alternating": "alternierend",
    "alternate": "alternierend",
    "hammer": "Hammer",
    "preacher": "Scott",
    "concentration": "Konzentration",
    "romanian": "rumänisch",
    "bulgarian": "bulgarisch",
    "goblet": "Goblet",
    "hack": "Hack",
    "sumo": "Sumo",
    "wide": "weit",
    "narrow": "eng",
    "close": "eng",
    "neutral": "neutral",
    "assisted": "unterstützt",
    "explosive": "explosiv",
    "isometric": "isometrisch",
    # body parts
    "leg": "Bein",
    "legs": "Beine",
    "calf": "Waden",
    "calves": "Waden",
    "chest": "Brust",
    "shoulder": "Schulter",
    "shoulders": "Schultern",
    "triceps": "Trizeps",
    "tricep": "Trizeps",
    "biceps": "Bizeps",
    "bicep": "Bizeps",
    "ab": "Bauch",
    "abs": "Bauch",
    "abdominal": "Bauch",
    "glute": "Gesäß",
    "glutes": "Gesäß",
    "hamstring": "Beinbizeps",
    "hamstrings": "Beinbizeps",
    "quad": "Quadrizeps",
    "quads": "Quadrizeps",
    "back": "Rücken",
    "hip": "Hüfte",
    "hips": "Hüfte",
    "wrist": "Handgelenk",
    "neck": "Nacken",
    "forearm": "Unterarm",
    "forearms": "Unterarme",
    "trap": "Trapez",
    "traps": "Trapez",
    "lat": "Latissimus",
    "lats": "Latissimus",
    # generic terms
    "behind": "hinter",
    "groin": "Leiste",
    "head": "Kopf",
    "low": "tief",
    "high": "hoch",
    "rope": "Seil",
    "pulley": "Zug",
    "chains": "Ketten",
    "chain": "Kette",
    "resistance": "Widerstand",
    "cone": "Hütchen",
    "upward": "aufwärts",
    "no": "ohne",
    "knee": "Knie",
    "knees": "Knie",
    "ankle": "Knöchel",
    "spine": "Wirbelsäule",
    # connectors
    "with": "mit",
    "and": "und",
    "to": "zum",
    "the": "",
    "on": "auf",
    "of": "von",
}


def _translate_token(tok: str) -> str:
    low = tok.lower()
    if low in WORDS:
        return WORDS[low]
    return tok


def translate_name(name: str) -> str:
    if name in NAME_OVERRIDES:
        return NAME_OVERRIDES[name]
    text = name
    # Phrase substitutions (case-insensitive, longest first). Word boundaries so a
    # singular phrase ("calf raise") doesn't match inside a plural ("calf raises").
    for phrase in sorted(PHRASES, key=len, reverse=True):
        text = re.sub(
            r"\b" + re.escape(phrase) + r"\b", PHRASES[phrase], text, flags=re.IGNORECASE
        )
    # Word-by-word for the remainder.
    out: list[str] = []
    for raw in text.split():
        # keep already-translated multiword fragments intact (they contain non-ascii / known)
        out.append(_translate_token(raw))
    de = " ".join(w for w in out if w).strip()
    de = re.sub(r"\s+", " ", de)
    de = de[:1].upper() + de[1:] if de else name
    return de or name


def _instructions(steps: list[str] | None) -> str | None:
    if not steps:
        return None
    return "\n".join(s.strip() for s in steps if s.strip()) or None


def build(src: Path) -> list[dict]:
    raw = json.loads(src.read_text())
    records: list[dict] = []
    for ex in raw:
        name = ex["name"].strip()
        images = ex.get("images") or []
        records.append(
            {
                "name": name,
                "name_de": translate_name(name),
                "category": ex.get("category"),
                "equipment": ex.get("equipment"),
                "primary_muscles": ex.get("primaryMuscles") or [],
                "secondary_muscles": ex.get("secondaryMuscles") or [],
                "instructions": _instructions(ex.get("instructions")),
                "image_url": images[0] if images else None,
            }
        )
    records.sort(key=lambda r: r["name"].lower())
    return records


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/exercises.src.json")
    records = build(src)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} exercises -> {DATA_FILE}")


if __name__ == "__main__":
    main()
