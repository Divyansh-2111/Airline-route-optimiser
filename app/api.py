"""
Minimal REST layer (Flask).
    python app/api.py
    GET  /health
    GET  /airports
    GET  /routes?src=MAA&dst=JFK&date=2026-11-01&pref=cheapest&cabin=ECONOMY&top=3&max_layovers=3
    POST /book   {"userId": "U001", "flightId": "EK540_2026-11-01", "cabin": "ECONOMY"}
"""
from flask import Flask, jsonify, request

import config
from route_optimizer import PREFERENCES, RouteOptimizer

app = Flask(__name__)
opt = RouteOptimizer()


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/airports")
def airports():
    with opt.driver.session(database=config.NEO4J_DATABASE) as s:
        rows = s.run("MATCH (a:Airport) RETURN a.code AS code, a.name AS name, a.city AS city, a.country AS country ORDER BY code")
        return jsonify([dict(r) for r in rows])


@app.get("/routes")
def routes():
    src, dst = request.args.get("src", "").upper(), request.args.get("dst", "").upper()
    pref = request.args.get("pref", "cheapest")
    if not src or not dst:
        return jsonify(error="src and dst are required"), 400
    if pref not in PREFERENCES:
        return jsonify(error=f"pref must be one of {list(PREFERENCES)}"), 400
    result = opt.find_routes(src, dst, request.args.get("date", "2026-11-01"), pref,
                             request.args.get("cabin", "ECONOMY").upper(),
                             int(request.args.get("max_layovers", 3)), int(request.args.get("top", 3)))
    return jsonify(result)


@app.post("/book")
def book():
    body = request.get_json(force=True)
    try:
        booking = opt.book_flight(body["userId"], body["flightId"], body.get("cabin", "ECONOMY").upper())
        booking["bookingDate"] = booking["bookingDate"].isoformat()
        return jsonify(booking), 201
    except (KeyError, ValueError) as e:
        return jsonify(error=str(e)), 400


if __name__ == "__main__":
    app.run(port=5000, debug=True)
