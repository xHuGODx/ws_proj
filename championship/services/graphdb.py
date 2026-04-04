from __future__ import annotations

import os

from SPARQLWrapper import JSON, POST, SPARQLWrapper


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

    def healthcheck(self) -> dict[str, object]:
        query = """
        SELECT (COUNT(*) AS ?triples)
        WHERE {
          ?s ?p ?o .
        }
        """
        wrapper = self._wrapper(self.query_endpoint)
        wrapper.setReturnFormat(JSON)
        wrapper.setQuery(query)
        try:
            response = wrapper.queryAndConvert()
            bindings = response.get("results", {}).get("bindings", [])
            triple_count = bindings[0]["triples"]["value"] if bindings else "0"
            return {"ok": True, "triple_count": triple_count, "endpoint": self.query_endpoint}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "endpoint": self.query_endpoint}

    def run_update(self, update_query: str) -> None:
        wrapper = self._wrapper(self.update_endpoint)
        wrapper.setMethod(POST)
        wrapper.setQuery(update_query)
        wrapper.query()

