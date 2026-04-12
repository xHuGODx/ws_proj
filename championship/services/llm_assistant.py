from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.request

from .graphdb import GraphDBClient


def _gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _gemini_api_key() -> str:
    return os.getenv("GEMINI_KEY", "").strip()


def _gemini_request_timeout() -> int:
    return int(os.getenv("GEMINI_REQUEST_TIMEOUT", "180"))


MAX_RESULT_ROWS = 25
SPARQL_CONTEXT = """You answer questions about a Formula 1 RDF knowledge graph.

The GraphDB client already injects these prefixes:
- PREFIX f1: <http://example.org/f1/>
- PREFIX res: <http://example.org/resource/>
- PREFIX rdf:
- PREFIX rdfs:
- PREFIX xsd:

Use only SELECT queries.
Never generate INSERT, DELETE, DROP, CLEAR, CREATE, LOAD, COPY, MOVE, ADD, or SERVICE.
Prefer exact predicates that already exist in the graph.

Common entity identifiers:
- Drivers: ?driver f1:driverId ?driverId ; rdfs:label ?driverLabel .
- Constructors: ?constructor f1:constructorId ?constructorId ; rdfs:label ?constructorLabel .
- Circuits: ?circuit f1:circuitId ?circuitId ; rdfs:label ?circuitLabel .
- Races: ?race f1:raceId ?raceId ; rdfs:label ?raceLabel ; f1:year ?year ; f1:round ?round .
- Results: ?res f1:resultId ?resultId ; f1:race ?race ; f1:driver ?driver ; f1:constructor ?constructor .

Useful result predicates:
- f1:positionOrder
- f1:position
- f1:positionText
- f1:points
- f1:grid
- f1:laps
- f1:time
- f1:milliseconds
- f1:fastestLap
- f1:fastestLapTime
- f1:fastestLapSpeed
- f1:statusId

Useful entity predicates:
- Drivers: f1:forename, f1:surname, f1:nationality, f1:dob, f1:code, f1:number
- Constructors: f1:name, f1:nationality
- Races: f1:name, f1:year, f1:round, f1:date, f1:circuit
- Circuits: f1:name, f1:location, f1:country, f1:lat, f1:lng
- Status entities: ?statusEnt f1:statusId ?statusId ; f1:status ?statusText .

Patterns:
- Winner of a race: filter result row with f1:positionOrder 1.
- Race by year/name:
  ?race f1:year ?year ; rdfs:label ?raceLabel .
- Constructor for a result:
  ?res f1:constructor ?constructor .
- Driver for a result:
  ?res f1:driver ?driver .

Return compact JSON with one key:
{ "sparql": "SELECT ..." }
Include JSON only.
"""

DISALLOWED_SPARQL_RE = re.compile(
    r"\b(INSERT|DELETE|DROP|CLEAR|CREATE|LOAD|COPY|MOVE|ADD|SERVICE|WITH|USING)\b",
    re.IGNORECASE,
)


class LLMAssistantError(Exception):
    pass


def answer_question(question: str, db: GraphDBClient | None = None) -> dict[str, object]:
    if not _gemini_api_key():
        raise LLMAssistantError("Missing GEMINI_KEY.")

    graphdb = db or GraphDBClient()
    sparql = generate_sparql(question)
    rows = graphdb.query(sparql)
    answer = generate_answer(question, rows)
    return {
        "question": question,
        "sparql": sparql,
        "rows": rows,
        "answer": answer,
    }


def generate_sparql(question: str) -> str:
    prompt = (
        "Return valid JSON only. The JSON must contain the key sparql.\n\n"
        f"{SPARQL_CONTEXT}\n\n"
        f"User question:\n{question}\n"
    )
    payload = _gemini_request(
        system_text=(
            "You generate safe read-only SPARQL queries for a Formula 1 RDF graph. "
            "Output JSON only."
        ),
        prompt=prompt,
        response_mime_type="application/json",
    )
    parsed = _parse_json_response(payload)
    sparql = str(parsed.get("sparql", "")).strip()
    return _validate_sparql(sparql)


def generate_answer(question: str, rows: list[dict[str, str]]) -> str:
    result_json = json.dumps(rows[:MAX_RESULT_ROWS], ensure_ascii=True, indent=2)
    payload = _gemini_request(
        system_text=(
            "You are a helpful Formula 1 assistant. "
            "Answer using only the SPARQL result rows provided. "
            "Do not mention SPARQL unless the user asks. "
            "If the result set is empty, say you could not find matching data in the graph."
        ),
        prompt=(
            f"Question:\n{question}\n\n"
            f"SPARQL result rows:\n{result_json}\n"
        ),
        response_mime_type="text/plain",
    )
    text = _extract_text_response(payload).strip()
    if not text:
        raise LLMAssistantError("The model returned an empty answer.")
    return text


def _gemini_request(*, system_text: str, prompt: str, response_mime_type: str) -> dict:
    body = {
        "systemInstruction": {
            "parts": [{"text": system_text}],
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": response_mime_type,
        },
    }
    request = urllib.request.Request(
        url=(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{_gemini_model()}:generateContent?key={_gemini_api_key()}"
        ),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_gemini_request_timeout()) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMAssistantError(f"Gemini API HTTP error: {exc.code} {detail}") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise LLMAssistantError(f"Gemini API request failed: {exc}") from exc


def _parse_json_response(payload: dict) -> dict:
    text = _clean_response(_extract_text_response(payload))
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMAssistantError(f"Model returned invalid JSON: {text}") from exc


def _extract_text_response(payload: dict) -> str:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMAssistantError(f"Unexpected Gemini response payload: {json.dumps(payload)}") from exc
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text:
        raise LLMAssistantError(f"Unexpected Gemini response payload: {json.dumps(payload)}")
    return text


def _clean_response(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_break = cleaned.find("\n")
        cleaned = cleaned[first_break + 1:] if first_break != -1 else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[: cleaned.rfind("```")]
    return cleaned.strip()


def _validate_sparql(sparql: str) -> str:
    if not sparql:
        raise LLMAssistantError("The model did not generate a SPARQL query.")
    if not re.match(r"^\s*SELECT\b", sparql, flags=re.IGNORECASE):
        raise LLMAssistantError("The model generated a non-SELECT SPARQL query.")
    if DISALLOWED_SPARQL_RE.search(sparql):
        raise LLMAssistantError("The model generated an unsafe SPARQL query.")
    if "LIMIT" not in sparql.upper():
        sparql = sparql.rstrip().rstrip(";") + f"\nLIMIT {MAX_RESULT_ROWS}"
    return sparql
