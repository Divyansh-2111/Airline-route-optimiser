#!/usr/bin/env python3
"""
Airline Route Optimizer - integration layer (Neo4j + MongoDB).

Flow:
  1. Neo4j  : enumerate candidate airport paths (<= max_layovers) ranked by the static weight
              that matches the preference (fare / duration / hops / distance).
  2. MongoDB: for each candidate path, pick real flights on the requested date that connect
              in time, have seats in the requested cabin and are not cancelled.
  3. Rank the realised itineraries by the preference and return the top-k.

Usage:
    python app/route_optimizer.py MAA JFK --date 2026-11-01 --pref cheapest --top 3
"""
import argparse
import json
import uuid
import random
from datetime import datetime, timedelta, timezone

from neo4j import GraphDatabase
from pymongo import MongoClient, ReturnDocument

import config

# preference -> (relationship property used by Neo4j to pre-rank, sort key on realised itinerary)
PREFERENCES = {
    "cheapest":          ("baseFare",   lambda i: (i["totalPrice"], i["totalMinutes"])),
    "fastest":           ("durationMin", lambda i: (i["totalMinutes"], i["totalPrice"])),
    "fewest_stops":      (None,         lambda i: (i["stops"], i["totalPrice"])),
    "shortest_distance": ("distanceKm", lambda i: (i["totalDistanceKm"], i["totalPrice"])),
}


class RouteOptimizer:
    def __init__(self):
        self.driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
        self.mongo = MongoClient(config.MONGO_URI, tz_aware=True)
        self.db = self.mongo[config.MONGO_DB]

    def close(self):
        self.driver.close()
        self.mongo.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------ Neo4j
    def candidate_paths(self, src, dst, pref, max_layovers=3, limit=30):
        prop = PREFERENCES[pref][0]
        weight = f"reduce(w = 0, r IN relationships(p) | w + r.{prop})" if prop else "length(p)"
        query = f"""
            MATCH p = (s:Airport {{code: $src}})-[:FLIGHT_ROUTE*1..{int(max_layovers) + 1}]->(d:Airport {{code: $dst}})
            WHERE ALL(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
            WITH p, {weight} AS weight
            RETURN [n IN nodes(p) | n.code] AS airports, weight
            ORDER BY weight ASC, length(p) ASC
            LIMIT $limit
        """
        with self.driver.session(database=config.NEO4J_DATABASE) as s:
            return [(r["airports"], r["weight"]) for r in s.run(query, src=src, dst=dst, limit=limit)]

    # ---------------------------------------------------------------- MongoDB
    def realise(self, airports, date, cabin="ECONOMY", min_connection=60, window_days=3):
        day_start = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        window_end = day_start + timedelta(days=window_days)
        ready_at, legs, layovers = day_start, [], []
        for a, b in zip(airports, airports[1:]):
            earliest = ready_at + (timedelta(minutes=min_connection) if legs else timedelta(0))
            flight = self.db.flights.find_one(
                {"origin": a, "destination": b,
                 "departureTime": {"$gte": earliest, "$lt": window_end},
                 "status": {"$ne": "CANCELLED"},
                 "fares": {"$elemMatch": {"class": cabin, "seatsAvailable": {"$gt": 0}}}},
                sort=[("departureTime", 1)])
            if flight is None:
                return None  # no feasible connection on this path
            fare = next(f for f in flight["fares"] if f["class"] == cabin)
            eff_arrival = flight["arrivalTime"] + timedelta(minutes=flight.get("delayMin", 0))
            if legs:
                layovers.append({"airport": a, "minutes": int((flight["departureTime"] - ready_at).total_seconds() // 60)})
            legs.append({
                "flightId": flight["_id"], "flightNo": flight["flightNo"], "from": a, "to": b,
                "departure": flight["departureTime"].isoformat(), "arrival": eff_arrival.isoformat(),
                "status": flight["status"], "delayMin": flight.get("delayMin", 0),
                "distanceKm": flight["distanceKm"], "price": fare["price"], "class": cabin,
            })
            ready_at = eff_arrival
        first_dep = datetime.fromisoformat(legs[0]["departure"])
        return {
            "airports": airports, "stops": len(legs) - 1, "legs": legs, "layovers": layovers,
            "totalPrice": round(sum(l["price"] for l in legs), 2),
            "totalDistanceKm": sum(l["distanceKm"] for l in legs),
            "totalMinutes": int((ready_at - first_dep).total_seconds() // 60),
        }

    # ---------------------------------------------------------------- public API
    def find_routes(self, src, dst, date, pref="cheapest", cabin="ECONOMY",
                    max_layovers=3, top=5, min_connection=60):
        if pref not in PREFERENCES:
            raise ValueError(f"pref must be one of {list(PREFERENCES)}")
        itineraries = []
        for airports, _weight in self.candidate_paths(src, dst, pref, max_layovers):
            it = self.realise(airports, date, cabin, min_connection)
            if it:
                itineraries.append(it)
        itineraries.sort(key=PREFERENCES[pref][1])
        for rank, it in enumerate(itineraries[:top], 1):
            it["rank"] = rank
        return itineraries[:top]

    def book_flight(self, user_id, flight_id, cabin="ECONOMY"):
        """Atomically decrement seats and insert a booking (multi-document transaction; needs a replica set)."""
        def txn(session):
            flights = self.db.flights
            flight = flights.find_one_and_update(
                {"_id": flight_id, "status": {"$ne": "CANCELLED"},
                 "fares": {"$elemMatch": {"class": cabin, "seatsAvailable": {"$gt": 0}}}},
                {"$inc": {"fares.$.seatsAvailable": -1}},
                return_document=ReturnDocument.BEFORE, session=session)
            if flight is None:
                raise ValueError("No seats left in that cabin (or flight cancelled)")
            price = next(f for f in flight["fares"] if f["class"] == cabin)["price"]
            booking = {
                "_id": "BK" + uuid.uuid4().hex[:8].upper(), "userId": user_id, "flightId": flight_id,
                "class": cabin, "seatNo": f"{random.randint(1, 40)}{random.choice('ABCDEF')}",
                "farePaid": price, "bookingDate": datetime.now(timezone.utc), "status": "CONFIRMED",
            }
            booking["bookingId"] = booking["_id"]
            self.db.bookings.insert_one(booking, session=session)
            return booking
        with self.mongo.start_session() as session:
            return session.with_transaction(txn)


def print_itinerary(it):
    print(f"\n#{it['rank']}  {' -> '.join(it['airports'])}   "
          f"(stops: {it['stops']}, price: ${it['totalPrice']}, time: {it['totalMinutes'] // 60}h{it['totalMinutes'] % 60:02d}m, "
          f"distance: {it['totalDistanceKm']} km)")
    for i, l in enumerate(it["legs"]):
        delay = f"  [DELAYED {l['delayMin']} min]" if l["status"] == "DELAYED" else ""
        print(f"   {l['flightNo']:<7}{l['from']}->{l['to']}  dep {l['departure'][:16]}  arr {l['arrival'][:16]}  ${l['price']}{delay}")
        if i < len(it["layovers"]):
            print(f"           layover at {it['layovers'][i]['airport']}: {it['layovers'][i]['minutes']} min")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Airline Route Optimizer")
    ap.add_argument("source")
    ap.add_argument("destination")
    ap.add_argument("--date", default="2026-11-01", help="YYYY-MM-DD (sample data covers 2026-11-01..03)")
    ap.add_argument("--pref", choices=list(PREFERENCES), default="cheapest")
    ap.add_argument("--cabin", default="ECONOMY")
    ap.add_argument("--max-layovers", type=int, default=3)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    with RouteOptimizer() as opt:
        results = opt.find_routes(a.source.upper(), a.destination.upper(), a.date, a.pref,
                                  a.cabin.upper(), a.max_layovers, a.top)
    if a.json:
        print(json.dumps(results, indent=2))
    elif not results:
        print("No feasible itinerary found.")
    else:
        for it in results:
            print_itinerary(it)
