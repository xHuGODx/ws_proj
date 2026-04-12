from __future__ import annotations

import os
import urllib.request

from SPARQLWrapper import JSON, POST, SPARQLWrapper

# Common prefixes prepended to every SPARQL query automatically.
PREFIXES = """\
PREFIX f1: <http://example.org/f1/>
PREFIX res: <http://example.org/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


class GraphDBClient:
    def __init__(self) -> None:
        base_url = os.getenv("GRAPHDB_BASE_URL", "http://localhost:7200").rstrip("/")
        repository = os.getenv("GRAPHDB_REPOSITORY", "ws-formula1")
        self.query_endpoint = f"{base_url}/repositories/{repository}"
        self.update_endpoint = f"{self.query_endpoint}/statements"
        self.username = os.getenv("GRAPHDB_USERNAME", "")
        self.password = os.getenv("GRAPHDB_PASSWORD", "")

    def _wrapper(self, endpoint: str) -> SPARQLWrapper:
        wrapper = SPARQLWrapper(endpoint)
        if self.username and self.password:
            wrapper.setCredentials(self.username, self.password)
        return wrapper

    def query(self, sparql: str) -> list[dict[str, str]]:
        """Run a SELECT query and return a flat list of row dicts {var: value}."""
        bindings = self.query_bindings(sparql)
        return [
            {var: cell["value"] for var, cell in row.items()}
            for row in bindings
        ]

    def query_bindings(self, sparql: str) -> list[dict[str, dict[str, str]]]:
        """Run a SELECT query and return raw SPARQL JSON bindings."""
        wrapper = self._wrapper(self.query_endpoint)
        wrapper.setReturnFormat(JSON)
        wrapper.setQuery(PREFIXES + sparql)
        response = wrapper.queryAndConvert()
        return response.get("results", {}).get("bindings", [])

    def healthcheck(self) -> dict[str, object]:
        # Use GraphDB's REST size endpoint — returns a plain integer, very fast.
        try:
            req = urllib.request.Request(
                f"{self.query_endpoint}/size",
                headers={"Accept": "text/plain"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                triple_count = f"{int(resp.read().decode().strip()):,}"
            return {"ok": True, "triple_count": triple_count, "endpoint": self.query_endpoint}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "endpoint": self.query_endpoint}

    def run_update(self, update_query: str) -> None:
        """Run a SPARQL UPDATE (INSERT/DELETE) query."""
        wrapper = self._wrapper(self.update_endpoint)
        wrapper.setMethod(POST)
        wrapper.setQuery(PREFIXES + update_query)
        wrapper.query()
