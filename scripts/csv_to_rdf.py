#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import re

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

BASE = Namespace("http://example.org/resource/")
F1 = Namespace("http://example.org/f1/")

EXPECTED_FILES = {
    "seasons": "seasons.csv",
    "circuits": "circuits.csv",
    "constructors": "constructors.csv",
    "drivers": "drivers.csv",
    "races": "races.csv",
    "results": ("results.csv", "race_results.csv"),
    "status": "status.csv",
}


def build_uri(kind: str, identifier: object) -> URIRef:
    return URIRef(f"{BASE}{kind}/{identifier}")


def has_value(value: object) -> bool:
    return pd.notna(value) and str(value).strip() not in {"", "\\N", "nan"}


def add_literal(graph: Graph, subject: URIRef, predicate: URIRef, value: object, datatype=None) -> None:
    if not has_value(value):
        return
    if datatype is None:
        graph.add((subject, predicate, Literal(value)))
        return
    graph.add((subject, predicate, Literal(value, datatype=datatype)))


def slugify(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def read_csvs(input_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name, candidates in EXPECTED_FILES.items():
        filenames = candidates if isinstance(candidates, tuple) else (candidates,)
        for filename in filenames:
            path = input_dir / filename
            if path.exists():
                frames[name] = pd.read_csv(path)
                break
    return frames


def convert(frames: dict[str, pd.DataFrame]) -> Graph:
    graph = Graph()
    graph.bind("f1", F1)
    graph.bind("rdfs", RDFS)

    seasons = frames.get("seasons")
    if seasons is not None:
        for row in seasons.itertuples(index=False):
            season_value = getattr(row, "year", getattr(row, "season"))
            season_uri = build_uri("season", season_value)
            graph.add((season_uri, RDF.type, F1.Season))
            add_literal(graph, season_uri, F1.year, season_value, XSD.gYear)
            add_literal(graph, season_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    circuits = frames.get("circuits")
    if circuits is not None:
        for row in circuits.itertuples(index=False):
            circuit_id = getattr(row, "circuitId")
            circuit_uri = build_uri("circuit", circuit_id)
            graph.add((circuit_uri, RDF.type, F1.Circuit))
            add_literal(graph, circuit_uri, F1.reference, circuit_id)
            add_literal(graph, circuit_uri, F1.name, getattr(row, "name", getattr(row, "circuitName", None)))
            add_literal(graph, circuit_uri, F1.location, getattr(row, "location", getattr(row, "locality", None)))
            add_literal(graph, circuit_uri, F1.country, row.country)
            add_literal(graph, circuit_uri, F1.latitude, getattr(row, "lat", None), XSD.decimal)
            add_literal(graph, circuit_uri, F1.longitude, getattr(row, "lng", getattr(row, "long", None)), XSD.decimal)
            add_literal(graph, circuit_uri, F1.altitude, getattr(row, "alt", None), XSD.integer)
            add_literal(graph, circuit_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    constructors = frames.get("constructors")
    if constructors is not None:
        for row in constructors.itertuples(index=False):
            constructor_id = row.constructorId
            constructor_uri = build_uri("constructor", constructor_id)
            graph.add((constructor_uri, RDF.type, F1.Constructor))
            add_literal(graph, constructor_uri, F1.reference, constructor_id)
            add_literal(graph, constructor_uri, F1.name, getattr(row, "name", getattr(row, "constructorName", None)))
            add_literal(graph, constructor_uri, F1.nationality, row.nationality)
            add_literal(graph, constructor_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    drivers = frames.get("drivers")
    if drivers is not None:
        for row in drivers.itertuples(index=False):
            driver_uri = build_uri("driver", row.driverId)
            graph.add((driver_uri, RDF.type, F1.Driver))
            add_literal(graph, driver_uri, F1.reference, row.driverId)
            add_literal(graph, driver_uri, F1.permanentNumber, getattr(row, "number", getattr(row, "permanentNumber", None)), XSD.integer)
            add_literal(graph, driver_uri, F1.code, row.code)
            add_literal(graph, driver_uri, F1.forename, getattr(row, "forename", getattr(row, "givenName", None)))
            add_literal(graph, driver_uri, F1.surname, getattr(row, "surname", getattr(row, "familyName", None)))
            add_literal(graph, driver_uri, F1.dateOfBirth, getattr(row, "dob", getattr(row, "dateOfBirth", None)), XSD.date)
            add_literal(graph, driver_uri, F1.nationality, row.nationality)
            add_literal(graph, driver_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    status = frames.get("status")
    if status is not None:
        for row in status.itertuples(index=False):
            status_key = slugify(row.status)
            status_uri = build_uri("status", status_key)
            graph.add((status_uri, RDF.type, F1.Status))
            add_literal(graph, status_uri, F1.label, row.status)
            add_literal(graph, status_uri, F1.statusId, getattr(row, "statusId", None), XSD.integer)
            add_literal(graph, status_uri, F1.occurrences, getattr(row, "count", None), XSD.integer)

    races = frames.get("races")
    if races is not None:
        for row in races.itertuples(index=False):
            race_uri = build_uri("race", f"{row.season}-{row.round}")
            season_uri = build_uri("season", row.season)
            circuit_uri = build_uri("circuit", row.circuitId)
            graph.add((race_uri, RDF.type, F1.Race))
            graph.add((race_uri, F1.season, season_uri))
            graph.add((race_uri, F1.circuit, circuit_uri))
            add_literal(graph, race_uri, F1.round, row.round, XSD.integer)
            add_literal(graph, race_uri, F1.name, getattr(row, "name", getattr(row, "raceName", None)))
            add_literal(graph, race_uri, F1.date, row.date, XSD.date)
            add_literal(graph, race_uri, F1.time, row.time)
            add_literal(graph, race_uri, F1.firstPractice, getattr(row, "firstPractice", None))
            add_literal(graph, race_uri, F1.secondPractice, getattr(row, "secondPractice", None))
            add_literal(graph, race_uri, F1.thirdPractice, getattr(row, "thirdPractice", None))
            add_literal(graph, race_uri, F1.qualifying, getattr(row, "qualifying", None))
            add_literal(graph, race_uri, F1.sprint, getattr(row, "sprint", None))
            add_literal(graph, race_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    results = frames.get("results")
    if results is not None:
        for row in results.itertuples(index=False):
            result_uri = build_uri("result", f"{row.season}-{row.round}-{row.driverId}")
            race_uri = build_uri("race", f"{row.season}-{row.round}")
            driver_uri = build_uri("driver", row.driverId)
            constructor_uri = build_uri("constructor", row.constructorId)
            status_uri = build_uri("status", slugify(row.status))
            graph.add((result_uri, RDF.type, F1.Result))
            graph.add((result_uri, F1.race, race_uri))
            graph.add((result_uri, F1.driver, driver_uri))
            graph.add((result_uri, F1.constructor, constructor_uri))
            graph.add((result_uri, F1.status, status_uri))
            add_literal(graph, result_uri, F1.driverName, getattr(row, "driverName", None))
            add_literal(graph, result_uri, F1.constructorName, getattr(row, "constructorName", None))
            add_literal(graph, result_uri, F1.carNumber, getattr(row, "number", None), XSD.integer)
            add_literal(graph, result_uri, F1.grid, row.grid, XSD.integer)
            add_literal(graph, result_uri, F1.positionOrder, getattr(row, "positionOrder", getattr(row, "position", None)), XSD.integer)
            add_literal(graph, result_uri, F1.points, row.points, XSD.decimal)
            add_literal(graph, result_uri, F1.laps, row.laps, XSD.integer)
            add_literal(graph, result_uri, F1.finishText, row.positionText)
            add_literal(graph, result_uri, F1.resultTime, getattr(row, "time", None))
            add_literal(graph, result_uri, F1.fastestLapRank, getattr(row, "fastestLapRank", None), XSD.integer)
            add_literal(graph, result_uri, F1.fastestLap, getattr(row, "fastestLap", getattr(row, "fastestLap_lap", None)), XSD.integer)
            add_literal(graph, result_uri, F1.fastestLapTime, row.fastestLapTime)
            add_literal(graph, result_uri, F1.fastestLapSpeed, getattr(row, "fastestLapSpeed", getattr(row, "averageSpeed", None)), XSD.decimal)

    return graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Formula 1 CSV files into RDF.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/rdf/formula1.ttl"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frames = read_csvs(args.input_dir)
    if not frames:
        expected = ", ".join(
            filename
            for candidates in EXPECTED_FILES.values()
            for filename in (candidates if isinstance(candidates, tuple) else (candidates,))
        )
        print(f"No expected CSV files were found in {args.input_dir}. Expected one or more of: {expected}")
        return 1

    graph = convert(frames)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=args.output, format="turtle")
    print(f"Wrote {len(graph)} triples to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
