import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from answer_verifier import verify_claim
from claim_extractor import extract_claims
from web_research import research_claim


ROOT = Path(__file__).parent
STATIC = ROOT / "dashboard"
HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("DASHBOARD_PORT", "8000"))
STATUS_SCORES = {"Verified": 100, "Potentially outdated": 50, "Conflicting": 0, "Unable to verify": 25}


def analyze_answer(answer: str) -> dict:
    claims = extract_claims(answer)
    results = []
    for claim in claims:
        try:
            research = research_claim(claim)
        except Exception as error:
            research = {"claim": claim, "sources": [], "error": str(error)}
        verification = verify_claim(claim, research)
        verification["sources"] = research.get("sources", [])
        verification["research_error"] = research.get("error")
        verification["freshness_score"] = STATUS_SCORES.get(verification.get("status"), 25)
        results.append(verification)
    score = round(sum(item["freshness_score"] for item in results) / len(results)) if results else 0
    return {"score": score, "claims_checked": len(results), "results": results}


class DashboardHandler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, content_type: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        routes = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"), "/styles.css": ("styles.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "application/javascript; charset=utf-8")}
        route = routes.get(self.path)
        if not route:
            self._send(b"Not found", "text/plain; charset=utf-8", 404)
            return
        path = STATIC / route[0]
        self._send(path.read_bytes(), route[1])

    def do_POST(self):
        if self.path != "/api/analyze":
            self._send(b"Not found", "text/plain; charset=utf-8", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            answer = str(payload.get("answer", "")).strip()
            if not answer:
                raise ValueError("Please enter an answer first.")
            result = analyze_answer(answer)
            self._send(json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
        except Exception as error:
            self._send(json.dumps({"error": str(error)}).encode("utf-8"), "application/json; charset=utf-8", 400)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"StaleAnswer dashboard running at http://{HOST}:{PORT}")
    server.serve_forever()

