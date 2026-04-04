#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

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
    "results": "results.csv",
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


def read_csvs(input_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name, filename in EXPECTED_FILES.items():
        path = input_dir / filename
        if path.exists():
            frames[name] = pd.read_csv(path)
    return frames


def convert(frames: dict[str, pd.DataFrame]) -> Graph:
    graph = Graph()
    graph.bind("f1", F1)
    graph.bind("rdfs", RDFS)

    seasons = frames.get("seasons")
    if seasons is not None:
        for row in seasons.itertuples(index=False):
            season_uri = build_uri("season", row.year)
            graph.add((season_uri, RDF.type, F1.Season))
            add_literal(graph, season_uri, F1.year, row.year, XSD.gYear)
            add_literal(graph, season_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    circuits = frames.get("circuits")
    if circuits is not None:
        for row in circuits.itertuples(index=False):
            circuit_uri = build_uri("circuit", row.circuitId)
            graph.add((circuit_uri, RDF.type, F1.Circuit))
            add_literal(graph, circuit_uri, F1.reference, row.circuitRef)
            add_literal(graph, circuit_uri, F1.name, row.name)
            add_literal(graph, circuit_uri, F1.location, row.location)
            add_literal(graph, circuit_uri, F1.country, row.country)
            add_literal(graph, circuit_uri, F1.latitude, row.lat, XSD.decimal)
            add_literal(graph, circuit_uri, F1.longitude, row.lng, XSD.decimal)
            add_literal(graph, circuit_uri, F1.altitude, row.alt, XSD.integer)
            add_literal(graph, circuit_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    constructors = frames.get("constructors")
    if constructors is not None:
        for row in constructors.itertuples(index=False):
            constructor_uri = build_uri("constructor", row.constructorId)
            graph.add((constructor_uri, RDF.type, F1.Constructor))
            add_literal(graph, constructor_uri, F1.reference, row.constructorRef)
            add_literal(graph, constructor_uri, F1.name, row.name)
            add_literal(graph, constructor_uri, F1.nationality, row.nationality)
            add_literal(graph, constructor_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    drivers = frames.get("drivers")
    if drivers is not None:
        for row in drivers.itertuples(index=False):
            driver_uri = build_uri("driver", row.driverId)
            graph.add((driver_uri, RDF.type, F1.Driver))
            add_literal(graph, driver_uri, F1.reference, row.driverRef)
            add_literal(graph, driver_uri, F1.permanentNumber, row.number, XSD.integer)
            add_literal(graph, driver_uri, F1.code, row.code)
            add_literal(graph, driver_uri, F1.forename, row.forename)
            add_literal(graph, driver_uri, F1.surname, row.surname)
            add_literal(graph, driver_uri, F1.dateOfBirth, row.dob, XSD.date)
            add_literal(graph, driver_uri, F1.nationality, row.nationality)
            add_literal(graph, driver_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    status = frames.get("status")
    if status is not None:
        for row in status.itertuples(index=False):
            status_uri = build_uri("status", row.statusId)
            graph.add((status_uri, RDF.type, F1.Status))
            add_literal(graph, status_uri, F1.label, row.status)

    races = frames.get("races")
    if races is not None:
        for row in races.itertuples(index=False):
            race_uri = build_uri("race", row.raceId)
            season_uri = build_uri("season", row.year)
            circuit_uri = build_uri("circuit", row.circuitId)
            graph.add((race_uri, RDF.type, F1.Race))
            graph.add((race_uri, F1.season, season_uri))
            graph.add((race_uri, F1.circuit, circuit_uri))
            add_literal(graph, race_uri, F1.round, row.round, XSD.integer)
            add_literal(graph, race_uri, F1.name, row.name)
            add_literal(graph, race_uri, F1.date, row.date, XSD.date)
            add_literal(graph, race_uri, F1.time, row.time)
            add_literal(graph, race_uri, RDFS.seeAlso, row.url, XSD.anyURI)

    results = frames.get("results")
    if results is not None:
        for row in results.itertuples(index=False):
            result_uri = build_uri("result", row.resultId)
            race_uri = build_uri("race", row.raceId)
            driver_uri = build_uri("driver", row.driverId)
            constructor_uri = build_uri("constructor", row.constructorId)
            status_uri = build_uri("status", row.statusId)
            graph.add((result_uri, RDF.type, F1.Result))
            graph.add((result_uri, F1.race, race_uri))
            graph.add((result_uri, F1.driver, driver_uri))
            graph.add((result_uri, F1.constructor, constructor_uri))
            graph.add((result_uri, F1.status, status_uri))
            add_literal(graph, result_uri, F1.grid, row.grid, XSD.integer)
            add_literal(graph, result_uri, F1.positionOrder, row.positionOrder, XSD.integer)
            add_literal(graph, result_uri, F1.points, row.points, XSD.decimal)
            add_literal(graph, result_uri, F1.laps, row.laps, XSD.integer)
            add_literal(graph, result_uri, F1.finishText, row.positionText)
            add_literal(graph, result_uri, F1.fastestLap, row.fastestLap, XSD.integer)
            add_literal(graph, result_uri, F1.fastestLapTime, row.fastestLapTime)
            add_literal(graph, result_uri, F1.fastestLapSpeed, row.fastestLapSpeed, XSD.decimal)

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
        expected = ", ".join(EXPECTED_FILES.values())
        print(f"No expected CSV files were found in {args.input_dir}. Expected one or more of: {expected}")
        return 1

    graph = convert(frames)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=args.output, format="turtle")
    print(f"Wrote {len(graph)} triples to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

