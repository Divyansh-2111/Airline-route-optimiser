#!/usr/bin/env python3
"""
Load the sample dataset into Neo4j (graph) and MongoDB (documents).

    python scripts/load_data.py            # load both (wipes existing airline data first)
    python scripts/load_data.py --neo4j    # only Neo4j
    python scripts/load_data.py --mongo    # only MongoDB
"""
import argparse
import csv
import os
import sys

from bson import json_util
from neo4j import GraphDatabase
from pymongo import ASCENDING, DESCENDING, MongoClient

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "app"))
import config  # noqa: E402

DATA = os.path.join(ROOT, "data")


def read_csv(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json_util.loads(f.read())  # converts {"$date": ...} to datetime


def load_neo4j():
    airports = [dict(r, lat=float(r["lat"]), lon=float(r["lon"])) for r in read_csv("airports.csv")]
    routes = [dict(r, distanceKm=int(r["distanceKm"]), durationMin=int(r["durationMin"]),
                   baseFare=float(r["baseFare"]), flightsPerDay=int(r["flightsPerDay"]))
              for r in read_csv("routes.csv")]
    driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
    with driver, driver.session(database=config.NEO4J_DATABASE) as s:
        s.run("CREATE CONSTRAINT airport_code IF NOT EXISTS FOR (a:Airport) REQUIRE a.code IS UNIQUE")
        s.run("MATCH (a:Airport) DETACH DELETE a")
        s.run("""UNWIND $rows AS r
                 MERGE (a:Airport {code: r.code})
                 SET a.name = r.name, a.city = r.city, a.country = r.country, a.lat = r.lat, a.lon = r.lon""",
              rows=airports)
        s.run("""UNWIND $rows AS r
                 MATCH (a:Airport {code: r.source}), (b:Airport {code: r.destination})
                 MERGE (a)-[f:FLIGHT_ROUTE {airline: r.airline}]->(b)
                 SET f.distanceKm = r.distanceKm, f.durationMin = r.durationMin,
                     f.baseFare = r.baseFare, f.flightsPerDay = r.flightsPerDay""",
              rows=routes)
        s.run("CREATE INDEX airport_country IF NOT EXISTS FOR (a:Airport) ON (a.country)")
        s.run("CREATE INDEX route_airline IF NOT EXISTS FOR ()-[r:FLIGHT_ROUTE]-() ON (r.airline)")
        n = s.run("MATCH (a:Airport) RETURN count(a) AS n").single()["n"]
        m = s.run("MATCH ()-[r:FLIGHT_ROUTE]->() RETURN count(r) AS n").single()["n"]
    print(f"[neo4j] {n} Airport nodes, {m} FLIGHT_ROUTE relationships")


def load_mongo():
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    for coll, fname in [("airlines", "airlines.json"), ("aircraft", "aircraft.json"),
                        ("users", "users.json"), ("flights", "flights.json"),
                        ("bookings", "bookings.json"), ("flight_status", "flight_status.json")]:
        db[coll].drop()
        docs = read_json(fname)
        db[coll].insert_many(docs)
        print(f"[mongo] {coll}: {len(docs)} documents")
    db.flights.create_index([("origin", ASCENDING), ("destination", ASCENDING), ("departureTime", ASCENDING)],
                            name="route_time_idx")
    db.flights.create_index([("airlineCode", ASCENDING)], name="airline_idx")
    db.users.create_index([("email", ASCENDING)], unique=True, name="email_unique")
    db.bookings.create_index([("userId", ASCENDING)], name="booking_user_idx")
    db.bookings.create_index([("flightId", ASCENDING)], name="booking_flight_idx")
    db.flight_status.create_index([("flightId", ASCENDING), ("updatedAt", DESCENDING)], name="status_flight_idx")
    print("[mongo] indexes created")
    client.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--neo4j", action="store_true")
    ap.add_argument("--mongo", action="store_true")
    args = ap.parse_args()
    both = not (args.neo4j or args.mongo)
    if both or args.neo4j:
        load_neo4j()
    if both or args.mongo:
        load_mongo()
