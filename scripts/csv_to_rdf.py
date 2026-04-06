#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from typing import IO, Any
from urllib.parse import quote

import pandas as pd
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

RESOURCE = Namespace("http://example.org/resource/")
F1 = Namespace("http://example.org/f1/")

TABLE_CONFIG: dict[str, dict[str, Any]] = {
    "seasons": {
        "filename": "seasons.csv",
        "kind": "season",
        "class_name": "Season",
        "id_columns": ["year"],
        "links": {},
    },
    "circuits": {
        "filename": "circuits.csv",
        "kind": "circuit",
        "class_name": "Circuit",
        "id_columns": ["circuitId"],
        "links": {},
    },
    "constructors": {
        "filename": "constructors.csv",
        "kind": "constructor",
        "class_name": "Constructor",
        "id_columns": ["constructorId"],
        "links": {},
    },
    "drivers": {
        "filename": "drivers.csv",
        "kind": "driver",
        "class_name": "Driver",
        "id_columns": ["driverId"],
        "links": {},
    },
    "races": {
        "filename": "races.csv",
        "kind": "race",
        "class_name": "Race",
        "id_columns": ["raceId"],
        "links": {
            "year": ("season", "season"),
            "circuitId": ("circuit", "circuit"),
        },
    },
    "results": {
        "filename": "results.csv",
        "kind": "result",
        "class_name": "Result",
        "id_columns": ["resultId"],
        "links": {
            "raceId": ("race", "race"),
            "driverId": ("driver", "driver"),
            "constructorId": ("constructor", "constructor"),
            "statusId": ("status", "status"),
        },
    },
    "sprint_results": {
        "filename": "sprint_results.csv",
        "kind": "sprint-result",
        "class_name": "SprintResult",
        "id_columns": ["resultId"],
        "links": {
            "raceId": ("race", "race"),
            "driverId": ("driver", "driver"),
            "constructorId": ("constructor", "constructor"),
            "statusId": ("status", "status"),
        },
    },
    "qualifying": {
        "filename": "qualifying.csv",
        "kind": "qualifying-result",
        "class_name": "QualifyingResult",
        "id_columns": ["qualifyId"],
        "links": {
            "raceId": ("race", "race"),
            "driverId": ("driver", "driver"),
            "constructorId": ("constructor", "constructor"),
        },
    },
    "pit_stops": {
        "filename": "pit_stops.csv",
        "kind": "pit-stop",
        "class_name": "PitStop",
        "id_columns": ["raceId", "driverId", "stop"],
        "links": {
            "raceId": ("race", "race"),
            "driverId": ("driver", "driver"),
        },
    },
    "lap_times": {
        "filename": "lap_times.csv",
        "kind": "lap-time",
        "class_name": "LapTime",
        "id_columns": ["raceId", "driverId", "lap"],
        "links": {
            "raceId": ("race", "race"),
            "driverId": ("driver", "driver"),
        },
    },
    "driver_standings": {
        "filename": "driver_standings.csv",
        "kind": "driver-standing",
        "class_name": "DriverStanding",
        "id_columns": ["driverStandingsId"],
        "links": {
            "raceId": ("race", "race"),
            "driverId": ("driver", "driver"),
        },
    },
    "constructor_standings": {
        "filename": "constructor_standings.csv",
        "kind": "constructor-standing",
        "class_name": "ConstructorStanding",
        "id_columns": ["constructorStandingsId"],
        "links": {
            "raceId": ("race", "race"),
            "constructorId": ("constructor", "constructor"),
        },
    },
    "constructor_results": {
        "filename": "constructor_results.csv",
        "kind": "constructor-result",
        "class_name": "ConstructorResult",
        "id_columns": ["constructorResultsId"],
        "links": {
            "raceId": ("race", "race"),
            "constructorId": ("constructor", "constructor"),
        },
    },
    "status": {
        "filename": "status.csv",
        "kind": "status",
        "class_name": "Status",
        "id_columns": ["statusId"],
        "links": {},
    },
}

TABLE_ORDER = [
    "seasons",
    "circuits",
    "constructors",
    "drivers",
    "status",
    "races",
    "results",
    "sprint_results",
    "qualifying",
    "pit_stops",
    "lap_times",
    "driver_standings",
    "constructor_standings",
    "constructor_results",
]

INTEGER_COLUMNS = {
    "circuitId",
    "constructorId",
    "constructorResultsId",
    "constructorStandingsId",
    "driverId",
    "driverStandingsId",
    "fastestLap",
    "grid",
    "lap",
    "laps",
    "milliseconds",
    "number",
    "position",
    "positionOrder",
    "qualifyId",
    "raceId",
    "rank",
    "resultId",
    "round",
    "statusId",
    "stop",
    "wins",
    "year",
    "alt",
}
DECIMAL_COLUMNS = {
    "fastestLapSpeed",
    "lat",
    "lng",
    "points",
}
DATE_COLUMNS = {
    "date",
    "dob",
    "fp1_date",
    "fp2_date",
    "fp3_date",
    "quali_date",
    "sprint_date",
}
TIME_COLUMNS = {
    "duration",
    "fastestLapTime",
    "fp1_time",
    "fp2_time",
    "fp3_time",
    "q1",
    "q2",
    "q3",
    "quali_time",
    "sprint_time",
    "time",
}
URI_COLUMNS = {"url"}


def build_uri(kind: str, *parts: object) -> URIRef:
    encoded_parts = [quote(str(part), safe="") for part in parts]
    return URIRef(f"{RESOURCE}{kind}/{'/'.join(encoded_parts)}")


def predicate_uri(name: str) -> URIRef:
    return URIRef(f"{F1}{name}")


def class_uri(name: str) -> URIRef:
    return URIRef(f"{F1}{name}")


def has_value(value: object) -> bool:
    return pd.notna(value) and str(value).strip() not in {"", "\\N", "nan"}


def infer_datatype(column: str) -> URIRef | None:
    if column == "year":
        return XSD.gYear
    if column in DATE_COLUMNS:
        return XSD.date
    if column in INTEGER_COLUMNS or column.endswith("Id"):
        return XSD.integer
    if column in DECIMAL_COLUMNS:
        return XSD.decimal
    if column in TIME_COLUMNS:
        return None
    return None


def _nt_uri(uri: URIRef) -> str:
    return f"<{uri}>"


def _nt_literal(lit: Literal) -> str:
    escaped = str(lit).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    if lit.datatype:
        return f'"{escaped}"^^<{lit.datatype}>'
    return f'"{escaped}"'


def emit_literal(out: IO[str], subject: URIRef, column: str, value: object) -> None:
    if not has_value(value):
        return
    s = _nt_uri(subject)
    if column in URI_COLUMNS:
        out.write(f"{s} <{RDFS.seeAlso}> <{str(value).strip()}> .\n")
        return
    datatype = infer_datatype(column)
    if datatype == XSD.integer:
        value = int(float(value))
    lit = Literal(value, datatype=datatype) if datatype else Literal(value)
    out.write(f"{s} <{predicate_uri(column)}> {_nt_literal(lit)} .\n")


def build_row_uri(table_name: str, row: Any) -> URIRef:
    config = TABLE_CONFIG[table_name]
    parts = [getattr(row, column) for column in config["id_columns"]]
    return build_uri(config["kind"], *parts)


def emit_label(out: IO[str], table_name: str, subject: URIRef, row: Any) -> None:
    if table_name == "seasons":
        label = f"{row.year} Formula 1 season"
    elif table_name == "circuits":
        label = row.name
    elif table_name == "constructors":
        label = row.name
    elif table_name == "drivers":
        label = f"{row.forename} {row.surname}"
    elif table_name == "races":
        label = f"{row.year} {row.name}"
    elif table_name == "status":
        label = row.status
    else:
        return
    out.write(f"{_nt_uri(subject)} <{RDFS.label}> {_nt_literal(Literal(label))} .\n")


def read_csvs(input_dir: Path, skip: set[str]) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for table_name, config in TABLE_CONFIG.items():
        if table_name in skip:
            print(f"  Skipping {table_name} (excluded).")
            continue
        path = input_dir / config["filename"]
        if not path.exists():
            print(f"  Warning: {config['filename']} not found in {input_dir}, skipping.")
            continue
        frames[table_name] = pd.read_csv(path, na_values=["\\N"], keep_default_na=True, low_memory=False)
    return frames


def emit_row(out: IO[str], table_name: str, config: dict[str, Any], columns: list[str], row: Any) -> None:
    uri = build_row_uri(table_name, row)
    subject = _nt_uri(uri)
    out.write(f"{subject} <{RDF.type}> <{class_uri(config['class_name'])}> .\n")
    emit_label(out, table_name, uri, row)
    for column in columns:
        emit_literal(out, uri, column, getattr(row, column))
    for column, (target_kind, relation_name) in config["links"].items():
        value = getattr(row, column)
        if has_value(value):
            out.write(f"{subject} <{predicate_uri(relation_name)}> <{build_uri(target_kind, value)}> .\n")


def convert(frames: dict[str, pd.DataFrame], out: IO[str]) -> int:
    total = 0
    for table_name in TABLE_ORDER:
        frame = frames.get(table_name)
        if frame is None:
            continue
        config = TABLE_CONFIG[table_name]
        columns = list(frame.columns)
        print(f"  Converting {table_name} ({len(frame):,} rows)...")
        for row in frame.itertuples(index=False):
            emit_row(out, table_name, config, columns, row)
            total += 1
        print(f"  Done {table_name}.")
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert the Kaggle Formula 1 CSV dataset into RDF N-Triples.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/rdf/formula1.nt"))
    parser.add_argument(
        "--exclude",
        metavar="TABLE",
        nargs="*",
        default=[],
        help="Table names to skip (e.g. --exclude lap_times pit_stops)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skip = set(args.exclude)
    print(f"Reading CSVs from {args.input_dir}...")
    frames = read_csvs(args.input_dir, skip)
    if not frames:
        print(f"No CSV files found in {args.input_dir}.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Streaming triples to {args.output}...")
    with args.output.open("w", encoding="utf-8") as out:
        rows = convert(frames, out)
    print(f"Done. Converted {rows:,} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
