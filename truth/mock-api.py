"""A stand-in for the assumptions API, for developing the web client without the real service.

It answers exactly the endpoints the real API offers and nothing else, in exactly the shapes it
answers them in - the same offset/limit listings, the same bare arrays, the same split between a
listed assumption and a read one, and the same two quirks: constraints go in under "constrains"
and come back out under "constraints", and a schema's industries are numbers it never hands out.

The data lives in memory, so restarting it puts the register back the way it started.

    python3 truth/mock-api.py        # serves on http://localhost:8000
"""
import json, re, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

def now(): return datetime.now(timezone.utc).isoformat()

IND = [{"id": str(uuid.uuid4()), "name": n} for n in
       ["Telemetry", "Aviation", "Maritime", "Energy", "Logistics"]]

def scheme(fields, constraints=None):
    return {"fields": fields, "constraints": constraints or []}

SCHEMAS = [
    {"id": str(uuid.uuid4()), "name": "Flight Performance", "revision": 2, "creator": "dana",
     "created_at": now(), "description": "Attributes of a flight performance assumption.",
     "revision_reason": "added cruise altitude", "latest_revision": True, "archived": False, "deleted": False,
     "industries": [IND[1]],
     "scheme": scheme([
        {"key": "cruise_speed", "label": "Cruise speed", "type": "number", "unit": "kn", "required": True},
        {"key": "cruise_altitude", "label": "Cruise altitude", "type": "integer", "unit": "ft"},
        {"key": "fuel_burn", "label": "Fuel burn", "type": "number", "unit": "kg/h"},
        {"key": "confidence", "label": "Confidence", "type": "enum",
         "options": ["High", "Medium", "Low"], "required": True},
        {"key": "verified", "label": "Verified", "type": "boolean"},
        {"key": "sources", "label": "Sources", "type": "list[str]"},
     ], [{"field": "cruise_speed", "rule": "min", "value": 0, "message": "Cruise speed cannot be negative"},
         {"field": "confidence", "rule": "one_of", "value": ["High", "Medium", "Low"]}])},
    {"id": str(uuid.uuid4()), "name": "Sensor Baseline", "revision": 1, "creator": "yossi",
     "created_at": now(), "description": "What a telemetry sensor is assumed to report.",
     "revision_reason": "", "latest_revision": True, "archived": False, "deleted": False,
     "industries": [IND[0]],
     "scheme": scheme([
        {"key": "sample_rate", "label": "Sample rate", "type": "number", "unit": "Hz", "required": True},
        {"key": "drift", "label": "Drift", "type": "number", "unit": "%/h"},
        {"key": "sensor_class", "label": "Sensor class", "type": "enum", "options": ["A", "B", "C"]},
        {"key": "commissioned", "label": "Commissioned", "type": "date"},
     ])},
    # a schema written by hand in the shortest way anybody would - one entry per field
    {"id": str(uuid.uuid4()), "name": "Port Throughput", "revision": 1, "creator": "script",
     "created_at": now(), "description": "", "revision_reason": "", "latest_revision": True,
     "archived": False, "deleted": False, "industries": [],
     "scheme": scheme([{"berth_count": "int"}, {"tonnes_per_day": "float"}, {"operator": "string"}])},
]

PARTIES = ["Engineering", "Operations", "Finance", "Safety"]
ASSUMPTIONS = []
for i in range(37):
    s = SCHEMAS[i % 3]
    vals = {}
    if s["name"] == "Flight Performance":
        vals = {"cruise_speed": 430 + i, "cruise_altitude": 35000, "fuel_burn": 2400.5,
                "confidence": ["High", "Medium", "Low"][i % 3], "verified": i % 2 == 0,
                "sources": ["manual", "flight-test"]}
    elif s["name"] == "Sensor Baseline":
        vals = {"sample_rate": 50 + i, "drift": 0.02, "sensor_class": "ABC"[i % 3],
                "commissioned": "2024-03-11"}
    else:
        vals = {"berth_count": 4 + (i % 3), "tonnes_per_day": 18000.0, "operator": "Harbour Co"}
    ASSUMPTIONS.append({
        "id": str(uuid.uuid4()), "name": f"Assumption {i + 1}",
        "assumption_text": f"The system is planned on the basis that condition {i + 1} holds throughout.",
        "proposing_party": PARTIES[i % 4], "tags": [["baseline", "draft", "reviewed"][i % 3]],
        "validation_responsible_parties": [PARTIES[(i + 1) % 4]], "revision": 1 + (i % 3),
        "creator": ["dana", "yossi", "amit"][i % 3], "created_at": now(),
        "schemas": [s], "values": vals, "revision_reason": "initial",
        "aggregated_scheme": s["scheme"]["fields"], "archived": False, "deleted": False,
        "industries": [IND[i % 5]] + ([IND[(i + 2) % 5]] if i % 4 == 0 else []),
    })

def summary(a): return {k: a[k] for k in ("id","name","assumption_text","proposing_party","tags",
    "validation_responsible_parties","revision","creator","created_at","schemas")}
def s_summary(s): return {k: s[k] for k in ("id","name","revision","creator","created_at")}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, code=200):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]
        q = dict(re.findall(r"(\w+)=([^&]*)", self.path.split("?")[1] if "?" in self.path else ""))
        off, lim = int(q.get("offset", 0)), int(q.get("limit", 100))
        if path == "/industry": return self._send(IND[off:off+lim])
        if path == "/schema": return self._send([s_summary(s) for s in SCHEMAS][off:off+lim])
        if path == "/assumption": return self._send([summary(a) for a in ASSUMPTIONS][off:off+lim])
        m = re.match(r"^/(industry|schema|assumption)/(?:name/)?([^/]+)(?:/latest)?$", path)
        if m:
            kind, key = m.group(1), m.group(2)
            pool = {"industry": IND, "schema": SCHEMAS, "assumption": ASSUMPTIONS}[kind]
            for item in pool:
                if item["id"] == key or item.get("name") == key: return self._send(item)
            return self._send({"detail": f"No such {kind}"}, 404)
        self._send({"detail": "Not found"}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        new_id = str(uuid.uuid4())
        if self.path == "/industry":
            IND.append({"id": new_id, "name": body["name"]})
        elif self.path == "/schema":
            SCHEMAS.append({"id": new_id, "name": body["name"], "revision": 1,
                "creator": body.get("creator", ""), "created_at": now(),
                "description": body.get("description", ""), "revision_reason": "",
                "latest_revision": True, "archived": False, "deleted": False, "industries": [],
                "scheme": {"fields": body["scheme"].get("fields", []),
                           "constraints": body["scheme"].get("constrains", [])}})
        elif self.path == "/assumption":
            picked = [s for s in SCHEMAS if s["id"] in body.get("schemas", [])]
            inds = [i for i in IND if i["id"] in body.get("industries", []) or i["name"] in body.get("industries", [])]
            ASSUMPTIONS.insert(0, {"id": new_id, "name": body["name"],
                "assumption_text": body["assumption_text"], "proposing_party": body["proposing_party"],
                "tags": body.get("tags", []), "validation_responsible_parties": body.get("validation_responsible_parties", []),
                "revision": 1, "creator": body.get("creator", ""), "created_at": now(),
                "schemas": picked, "values": body.get("values", {}), "revision_reason": "created",
                "aggregated_scheme": [f for s in picked for f in s["scheme"]["fields"]],
                "archived": False, "deleted": False, "industries": inds})
        self._send({"id": new_id}, 201)

if __name__ == "__main__":
    print("The mock assumptions API is listening on http://localhost:8000")
    HTTPServer(("127.0.0.1", 8000), H).serve_forever()
