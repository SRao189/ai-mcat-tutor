"""Open Notebook adapter integration proof.

Run: python -m tests.test_open_notebook_integration
No real Open Notebook or NVIDIA service is contacted. The HTTP server below
mocks only the Open Notebook REST boundary used by the vendored APIClient.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from council.config import CouncilConfig  # noqa: E402
from council.phase1 import answer_question  # noqa: E402
from council.schema import ResponseStatus  # noqa: E402
from integrations.open_notebook_adapter import OpenNotebookAdapter  # noqa: E402


MOCK_CONFIG = CouncilConfig(
    base_url="",
    api_key=None,
    tutor_model="mock",
    embed_model=None,
    rerank_model=None,
    safety_model=None,
    mock_mode=True,
)

NOW = "2026-07-01T12:00:00Z"
SOURCE_TEXT = (
    "Gibbs free energy (Delta G) determines reaction spontaneity. "
    "Delta G less than 0 means a reaction is spontaneous and exergonic."
)


class OpenNotebookBoundary(BaseHTTPRequestHandler):
    notebooks: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    calls: list[tuple[str, str, dict]] = []

    def log_message(self, *_args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        self.calls.append(("GET", parsed.path, query))

        if parsed.path == "/api/notebooks":
            self._json(list(self.notebooks.values()))
            return

        if parsed.path == "/api/sources":
            notebook_id = query.get("notebook_id", [None])[0]
            sources = list(self.sources.values())
            if notebook_id:
                sources = [
                    source
                    for source in sources
                    if notebook_id in (source.get("notebooks") or [])
                ]
            self._json(
                [
                    {
                        "id": source["id"],
                        "title": source["title"],
                        "topics": source["topics"],
                        "asset": source["asset"],
                        "embedded": source["embedded"],
                        "embedded_chunks": source["embedded_chunks"],
                        "insights_count": 0,
                        "created": source["created"],
                        "updated": source["updated"],
                    }
                    for source in sources
                ]
            )
            return

        if parsed.path.startswith("/api/sources/"):
            source_id = parsed.path.removeprefix("/api/sources/")
            source = self.sources.get(source_id)
            if source:
                self._json(source)
            else:
                self._json({"detail": "Source not found"}, status=404)
            return

        self._json({"detail": "Not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        payload = self._read_json()
        self.calls.append(("POST", parsed.path, payload))

        if parsed.path == "/api/notebooks":
            notebook_id = "notebook:mcat"
            notebook = {
                "id": notebook_id,
                "name": payload["name"],
                "description": payload.get("description", ""),
                "archived": False,
                "created": NOW,
                "updated": NOW,
                "source_count": 0,
                "note_count": 0,
            }
            self.notebooks[notebook_id] = notebook
            self._json(notebook)
            return

        if parsed.path == "/api/sources/json":
            source_id = "source:on-src-thermo"
            source = {
                "id": source_id,
                "title": payload.get("title") or "Untitled source",
                "topics": ["thermodynamics"],
                "asset": None,
                "full_text": payload.get("content") or "",
                "embedded": True,
                "embedded_chunks": 1,
                "file_available": None,
                "created": NOW,
                "updated": NOW,
                "command_id": None,
                "status": None,
                "processing_info": None,
                "notebooks": payload.get("notebooks") or [],
            }
            self.sources[source_id] = source
            self._json(source)
            return

        if parsed.path == "/api/search":
            result = {
                "id": "source_embedding:on-chunk-thermo-1",
                "title": "MCAT Thermodynamics Note",
                "content": SOURCE_TEXT,
                "parent_id": "source:on-src-thermo",
                "relevance": 0.93,
            }
            self._json(
                {
                    "results": [result],
                    "total_count": 1,
                    "search_type": payload.get("type", "text"),
                }
            )
            return

        if parsed.path == "/api/transformations/execute":
            self._json(
                {
                    "output": f"Transformed: {payload['input_text']}",
                    "transformation_id": payload["transformation_id"],
                    "model_id": payload["model_id"],
                }
            )
            return

        self._json({"detail": "Not found"}, status=404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(body)

    def _json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class BoundaryServer:
    def __enter__(self):
        OpenNotebookBoundary.notebooks = {}
        OpenNotebookBoundary.sources = {}
        OpenNotebookBoundary.calls = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), OpenNotebookBoundary)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        os.environ["API_BASE_URL"] = self.base_url
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def test_open_notebook_to_council_traceable_chain():
    with BoundaryServer() as boundary:
        adapter = OpenNotebookAdapter(base_url=boundary.base_url)

        notebook = adapter.create_or_select_mcat_notebook()
        source = adapter.ingest_source(
            notebook_id=notebook.id,
            title="MCAT Thermodynamics Note",
            text=SOURCE_TEXT,
            metadata={"publisher": "adapter-test"},
        )
        passages = adapter.retrieve_passages(
            "What determines reaction spontaneity?",
            notebook_id=notebook.id,
            limit=3,
        )
        stored_passages = adapter.passage_store(passages).load()
        citation_candidates = adapter.citation_candidates(passages)
        concept_map = adapter.map_to_concept_nodes(passages)

        response = answer_question(
            "What determines reaction spontaneity?",
            section_id="7.1",
            config=MOCK_CONFIG,
            retriever=adapter.retriever(passages),
            verifier=adapter.verifier(passages),
        )

    assert notebook.id == "notebook:mcat"
    assert source.source_id == "source:on-src-thermo"
    assert len(passages) == 1
    assert passages[0].source_id == source.source_id
    assert passages[0].passage_id == "source_embedding:on-chunk-thermo-1"
    assert citation_candidates == stored_passages
    assert "article:thermodynamics" in concept_map[passages[0].citation_id]
    assert response.status == ResponseStatus.VERIFIED, response.to_dict()
    assert response.cited_sources
    cited = response.cited_sources[0]
    assert cited["openNotebookSourceId"] == "source:on-src-thermo"
    assert cited["openNotebookPassageId"] == "source_embedding:on-chunk-thermo-1"
    assert cited["sourceId"] == passages[0].citation_id
    assert any(call[:2] == ("POST", "/api/sources/json") for call in OpenNotebookBoundary.calls)
    assert any(call[:2] == ("POST", "/api/search") for call in OpenNotebookBoundary.calls)
    print(
        "TRACE",
        {
            "source_id": source.source_id,
            "passage_ids": [passage.passage_id for passage in passages],
            "concept_node_ids": concept_map[passages[0].citation_id],
            "council_status": response.status.value,
            "final_citation_ids": [item["sourceId"] for item in response.cited_sources],
        },
    )


def test_open_notebook_transformation_execute_round_trips_response():
    with BoundaryServer() as boundary:
        adapter = OpenNotebookAdapter(base_url=boundary.base_url)

        result = adapter.request_transformation(
            transformation_id="transformation:condense",
            input_text="Gibbs free energy determines spontaneity.",
            model_id="model:nvidia-test",
        )

    assert result["transformation_id"] == "transformation:condense"
    assert result["model_id"] == "model:nvidia-test"
    assert "Gibbs free energy determines spontaneity." in result["output"]
    assert any(
        call[:2] == ("POST", "/api/transformations/execute")
        for call in OpenNotebookBoundary.calls
    )


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    _run_all()
