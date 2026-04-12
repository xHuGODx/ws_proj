from __future__ import annotations

import csv
import io
import secrets
from collections import Counter
from decimal import Decimal, InvalidOperation

from .graphdb import GraphDBClient

RESOURCE_BASE = "http://example.org/resource/"

RESULT_FIELD_SPECS = [
    {"name": "resultId", "required": True, "type": "int", "label": "Result ID"},
    {"name": "driverId", "required": True, "type": "ref", "label": "Driver ID"},
    {"name": "constructorId", "required": True, "type": "ref", "label": "Constructor ID"},
    {"name": "statusId", "required": True, "type": "ref", "label": "Status ID"},
    {"name": "positionOrder", "required": True, "type": "int", "label": "Position order"},
    {"name": "number", "required": False, "type": "int", "label": "Car number"},
    {"name": "grid", "required": False, "type": "int", "label": "Grid"},
    {"name": "position", "required": False, "type": "int", "label": "Position"},
    {"name": "positionText", "required": False, "type": "str", "label": "Position text"},
    {"name": "points", "required": False, "type": "decimal", "label": "Points"},
    {"name": "laps", "required": False, "type": "int", "label": "Laps"},
    {"name": "time", "required": False, "type": "str", "label": "Race time"},
    {"name": "milliseconds", "required": False, "type": "int", "label": "Milliseconds"},
    {"name": "fastestLap", "required": False, "type": "int", "label": "Fastest lap"},
    {"name": "rank", "required": False, "type": "int", "label": "Fastest lap rank"},
    {"name": "fastestLapTime", "required": False, "type": "str", "label": "Fastest lap time"},
    {"name": "fastestLapSpeed", "required": False, "type": "decimal", "label": "Fastest lap speed"},
]
RESULT_FIELD_NAMES = [field["name"] for field in RESULT_FIELD_SPECS]
REQUIRED_RESULT_FIELDS = [field["name"] for field in RESULT_FIELD_SPECS if field["required"]]


def race_choices(db: GraphDBClient) -> list[tuple[str, str]]:
    rows = db.query("""
        SELECT ?raceId ?label ?year ?round WHERE {
          ?r f1:raceId ?raceId ;
             rdfs:label ?label ;
             f1:year ?year ;
             f1:round ?round .
        }
        ORDER BY DESC(?year) ?round
    """)
    return [("", "— Select race —")] + [
        (row["raceId"], f'{row["year"]} · Round {row["round"]} · {row["label"]}')
        for row in rows
    ]


def serialize_result_import_preview(db: GraphDBClient, race_id: str, upload) -> dict:
    race = _load_race(db, race_id)
    csv_text = upload.read().decode("utf-8-sig")
    parsed = _parse_results_csv(csv_text)
    if not race:
        parsed["blocking_errors"].append(f"Race {race_id} does not exist.")
    parsed["race"] = race or {"raceId": race_id, "label": "", "year": "", "round": ""}

    if parsed["rows"]:
        _resolve_references(db, parsed)
        _load_existing_results(db, parsed)
        _build_statements(db, parsed, race_id)

    preview = {
        "token": secrets.token_urlsafe(16),
        "race": parsed["race"],
        "race_id": parsed["race"].get("raceId", race_id),
        "race_label": parsed["race"].get("label", ""),
        "race_year": parsed["race"].get("year", ""),
        "race_round": parsed["race"].get("round", ""),
        "csv_name": getattr(upload, "name", "results.csv"),
        "field_specs": RESULT_FIELD_SPECS,
        "rows": parsed["rows"],
        "row_count": len(parsed["rows"]),
        "required_fields": REQUIRED_RESULT_FIELDS,
        "missing_columns": parsed["missing_columns"],
        "extra_columns": parsed["extra_columns"],
        "blocking_errors": parsed["blocking_errors"],
        "warnings": parsed["warnings"],
        "duplicates": parsed["duplicates"],
        "unresolved_references": parsed["unresolved_references"],
        "replacements": parsed["replacements"],
        "new_triples": parsed["new_triples"],
        "existing_triples": parsed["existing_triples"],
        "apply_update": parsed["apply_update"],
        "rollback_update": parsed["rollback_update"],
        "can_confirm": not parsed["blocking_errors"] and not parsed["duplicates"] and not parsed["unresolved_references"],
        "sample_csv": build_results_import_sample_csv(),
    }
    return preview


def build_results_import_sample_csv() -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=RESULT_FIELD_NAMES)
    writer.writeheader()
    writer.writerow({
        "resultId": "10001",
        "driverId": "1",
        "constructorId": "1",
        "statusId": "1",
        "positionOrder": "1",
        "number": "44",
        "grid": "1",
        "position": "1",
        "positionText": "1",
        "points": "25",
        "laps": "58",
        "time": "1:24:12.345",
        "milliseconds": "5052345",
        "fastestLap": "42",
        "rank": "1",
        "fastestLapTime": "1:28.321",
        "fastestLapSpeed": "215.432",
    })
    writer.writerow({
        "resultId": "10002",
        "driverId": "2",
        "constructorId": "2",
        "statusId": "11",
        "positionOrder": "2",
        "number": "16",
        "grid": "3",
        "position": "2",
        "positionText": "2",
        "points": "18",
        "laps": "58",
        "time": "+4.201",
        "milliseconds": "5056546",
        "fastestLap": "39",
        "rank": "2",
        "fastestLapTime": "1:28.654",
        "fastestLapSpeed": "214.901",
    })
    return output.getvalue()


def result_import_template_response() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(RESULT_FIELD_NAMES)
    return output.getvalue()


def _load_race(db: GraphDBClient, race_id: str) -> dict[str, str] | None:
    rows = db.query(f"""
        SELECT ?raceId ?label ?year ?round WHERE {{
          ?r f1:raceId "{_sq(race_id)}" ;
             rdfs:label ?label ;
             f1:year ?year ;
             f1:round ?round .
        }} LIMIT 1
    """)
    if rows:
        return rows[0]
    rows = db.query(f"""
        SELECT ?raceId ?label ?year ?round WHERE {{
          ?r f1:raceId {race_id} ;
             rdfs:label ?label ;
             f1:year ?year ;
             f1:round ?round .
        }} LIMIT 1
    """)
    return rows[0] if rows else None


def _parse_results_csv(csv_text: str) -> dict:
    parsed = {
        "rows": [],
        "missing_columns": [],
        "extra_columns": [],
        "blocking_errors": [],
        "warnings": [],
        "duplicates": [],
        "unresolved_references": [],
        "replacements": [],
        "new_triples": [],
        "existing_triples": [],
        "apply_update": "",
        "rollback_update": "",
    }
    if not csv_text.strip():
        parsed["blocking_errors"].append("Upload a non-empty CSV file.")
        return parsed

    reader = csv.DictReader(io.StringIO(csv_text))
    headers = reader.fieldnames or []
    parsed["missing_columns"] = [field for field in REQUIRED_RESULT_FIELDS if field not in headers]
    parsed["extra_columns"] = [header for header in headers if header not in RESULT_FIELD_NAMES]
    if parsed["missing_columns"]:
        parsed["blocking_errors"].append(
            "Missing required columns: " + ", ".join(parsed["missing_columns"])
        )
        return parsed

    seen_rows: dict[str, dict] = {}
    duplicate_counts: Counter[str] = Counter()

    for index, row in enumerate(reader, start=2):
        normalized = {"_line": index}
        row_errors = []
        for field in RESULT_FIELD_SPECS:
            raw_value = (row.get(field["name"]) or "").strip()
            try:
                normalized[field["name"]] = _normalize_value(raw_value, field)
            except ValueError as exc:
                row_errors.append(f'Line {index}: {exc}')
        if row_errors:
            parsed["blocking_errors"].extend(row_errors)
            continue
        result_id = normalized["resultId"]
        if result_id in seen_rows:
            duplicate_counts[result_id] += 1
            parsed["duplicates"].append({
                "resultId": result_id,
                "line": index,
                "existing_line": seen_rows[result_id]["_line"],
                "conflict": any(
                    normalized.get(field) != seen_rows[result_id].get(field)
                    for field in RESULT_FIELD_NAMES
                ),
            })
            continue
        seen_rows[result_id] = normalized
        parsed["rows"].append(normalized)

    for result_id, count in duplicate_counts.items():
        parsed["blocking_errors"].append(
            f"Result ID {result_id} appears multiple times in the uploaded CSV."
        )
    return parsed


def _normalize_value(raw_value: str, field: dict) -> str:
    if raw_value == "":
        if field["required"]:
            raise ValueError(f'{field["label"]} is required.')
        return ""
    if field["type"] == "int":
        return str(int(raw_value))
    if field["type"] == "decimal":
        try:
            return format(Decimal(raw_value), "f").rstrip("0").rstrip(".") or "0"
        except InvalidOperation as exc:
            raise ValueError(f'{field["label"]} must be a valid decimal.') from exc
    return raw_value


def _resolve_references(db: GraphDBClient, parsed: dict) -> None:
    ref_ids = {
        "driverId": sorted({row["driverId"] for row in parsed["rows"] if row["driverId"]}),
        "constructorId": sorted({row["constructorId"] for row in parsed["rows"] if row["constructorId"]}),
        "statusId": sorted({row["statusId"] for row in parsed["rows"] if row["statusId"]}),
    }
    maps = {
        "driverId": _entity_map(db, "driver", "driverId", ref_ids["driverId"], "rdfs:label"),
        "constructorId": _entity_map(db, "constructor", "constructorId", ref_ids["constructorId"], "rdfs:label"),
        "statusId": _entity_map(db, "status", "statusId", ref_ids["statusId"], "f1:status"),
    }
    for row in parsed["rows"]:
        for field_name, kind in (("driverId", "driver"), ("constructorId", "constructor"), ("statusId", "status")):
            if row[field_name] not in maps[field_name]:
                parsed["unresolved_references"].append({
                    "line": row["_line"],
                    "field": field_name,
                    "value": row[field_name],
                    "kind": kind,
                })
            else:
                row[f"{field_name}_uri"] = maps[field_name][row[field_name]]["uri"]
                row[f"{field_name}_label"] = maps[field_name][row[field_name]]["label"]


def _entity_map(db: GraphDBClient, kind: str, field_name: str, ids: list[str], label_predicate: str) -> dict[str, dict[str, str]]:
    if not ids:
        return {}
    filter_values = ", ".join(f'"{_sq(value)}"' for value in ids)
    rows = db.query(f"""
        SELECT ?id ?uri ?label WHERE {{
          ?uri f1:{field_name} ?id ;
               {label_predicate} ?label .
          FILTER(STR(?id) IN ({filter_values}))
        }}
    """)
    return {row["id"]: {"uri": row["uri"], "label": row["label"]} for row in rows}


def _load_existing_results(db: GraphDBClient, parsed: dict) -> None:
    result_ids = [row["resultId"] for row in parsed["rows"]]
    if not result_ids:
        return
    filter_values = ", ".join(result_ids)
    rows = db.query(f"""
        SELECT ?resultId ?raceId ?driverId ?constructorId WHERE {{
          ?res f1:resultId ?resultId .
          FILTER(?resultId IN ({filter_values}))
          OPTIONAL {{ ?res f1:race ?race . ?race f1:raceId ?raceId }}
          OPTIONAL {{ ?res f1:driver ?driver . ?driver f1:driverId ?driverId }}
          OPTIONAL {{ ?res f1:constructor ?constructor . ?constructor f1:constructorId ?constructorId }}
        }}
    """)
    existing = {row["resultId"]: row for row in rows}
    for row in parsed["rows"]:
        if row["resultId"] in existing:
            parsed["replacements"].append({
                "resultId": row["resultId"],
                "existingRaceId": existing[row["resultId"]].get("raceId", ""),
                "existingDriverId": existing[row["resultId"]].get("driverId", ""),
                "existingConstructorId": existing[row["resultId"]].get("constructorId", ""),
            })


def _build_statements(db: GraphDBClient, parsed: dict, race_id: str) -> None:
    if parsed["blocking_errors"] or parsed["unresolved_references"]:
        return

    apply_deletes = []
    apply_inserts = []
    rollback_deletes = []
    rollback_inserts = []

    for row in parsed["rows"]:
        subject = _uri("result", row["resultId"])
        existing_body = _existing_result_body(db, row["resultId"])
        if existing_body:
            parsed["existing_triples"].append({
                "resultId": row["resultId"],
                "triples": existing_body,
            })
            apply_deletes.append(f"DELETE WHERE {{ {subject} ?p ?o }}")
            rollback_deletes.append(f"DELETE WHERE {{ {subject} ?p ?o }}")
            rollback_inserts.append(f"INSERT DATA {{ {existing_body} }}")
        else:
            rollback_deletes.append(f"DELETE WHERE {{ {subject} ?p ?o }}")

        new_body = _result_body(row, race_id)
        parsed["new_triples"].append({"resultId": row["resultId"], "triples": new_body})
        apply_inserts.append(f"INSERT DATA {{ {new_body} }}")

    parsed["apply_update"] = " ;\n".join(apply_deletes + apply_inserts)
    parsed["rollback_update"] = " ;\n".join(rollback_deletes + rollback_inserts)


def _existing_result_body(db: GraphDBClient, result_id: str) -> str:
    subject = _uri("result", result_id)
    bindings = db.query_bindings(f"SELECT ?p ?o WHERE {{ {subject} ?p ?o }}")
    if not bindings:
        return ""
    statements = [
        f"{subject} <{binding['p']['value']}> {_binding_to_sparql(binding['o'])} ."
        for binding in bindings
    ]
    return " ".join(statements)


def _binding_to_sparql(binding: dict[str, str]) -> str:
    if binding["type"] == "uri":
        return f'<{binding["value"]}>'
    value = _sq(binding["value"])
    datatype = binding.get("datatype")
    language = binding.get("xml:lang")
    if language:
        return f'"{value}"@{language}'
    if datatype:
        return f'"{value}"^^<{datatype}>'
    return f'"{value}"'


def _result_body(row: dict, race_id: str) -> str:
    subject = _uri("result", row["resultId"])
    triples = [
        f"{subject} f1:resultId {row['resultId']} .",
        f"{subject} f1:race {_uri('race', race_id)} .",
        f"{subject} f1:driver <{row['driverId_uri']}> .",
        f"{subject} f1:constructor <{row['constructorId_uri']}> .",
        f"{subject} f1:statusId {row['statusId']} .",
        f"{subject} f1:positionOrder {row['positionOrder']} .",
    ]
    for field in RESULT_FIELD_SPECS:
        if field["name"] in {"resultId", "driverId", "constructorId", "statusId", "positionOrder"}:
            continue
        value = row.get(field["name"], "")
        if value == "":
            continue
        if field["type"] == "int":
            triples.append(f"{subject} f1:{field['name']} {value} .")
        elif field["type"] == "decimal":
            triples.append(f'{subject} f1:{field["name"]} "{value}"^^xsd:decimal .')
        else:
            triples.append(f'{subject} f1:{field["name"]} "{_sq(value)}" .')
    return " ".join(triples)


def _uri(kind: str, entity_id: str) -> str:
    return f"<{RESOURCE_BASE}{kind}/{entity_id}>"


def _sq(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
