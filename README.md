# Airline Route Optimizer (Neo4j + MongoDB)

DBMS project, Review 2: database implementation and core functionality.
Neo4j models the airport network as a graph and finds routes. MongoDB stores the changing operational data: flights, fares, seats, bookings, delays.

## Project layout
```
data/      airports.csv, routes.csv (Neo4j)  |  flights, bookings, users, airlines, aircraft, flight_status .json (MongoDB)
scripts/   generate_data.py (reproducible sample data), load_data.py (loads both DBs)
neo4j/     01 constraints/indexes, 02 LOAD CSV, 03 CRUD, 04 route queries, 05 GDS algorithms (Cypher)
mongo/     01 indexes + explain, 02 CRUD, 03 aggregations, 04 transaction (mongosh)
app/       route_optimizer.py (CLI + integration logic), api.py (Flask REST layer), config.py
```

## Sample data (meets the 50+ records requirement)
| Store | Item | Count |
|---|---|---|
| Neo4j | Airport nodes | 50 |
| Neo4j | FLIGHT_ROUTE relationships | 346 |
| MongoDB | flights (3 dates x 2 departures per route) | 2,076 |
| MongoDB | flight_status | 394 |
| MongoDB | users / bookings / airlines / aircraft | 25 / 40 / 16 / 64 |

All times are stored in UTC. The sample flights cover **2026-11-01 to 2026-11-03**.

## Setup
```bash
# 1. Start both databases (Neo4j with GDS + APOC, MongoDB as a single-node replica set for transactions)
docker compose up -d

# 2. Python environment
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. (Optional) regenerate the data, then load both databases
python scripts/generate_data.py
python scripts/load_data.py
```
Not using Docker? Install Neo4j Desktop and MongoDB, set the connection details in `.env` (copy `.env.example`), and start `mongod --replSet rs0` followed by `rs.initiate()` in mongosh if you want transactions.

## Run the demo
```bash
# Neo4j: paste the files into Neo4j Browser, or:
cypher-shell -u neo4j -p password123 -f neo4j/03_crud.cypher
cypher-shell -u neo4j -p password123 -f neo4j/04_route_queries.cypher
cypher-shell -u neo4j -p password123 -f neo4j/05_gds_algorithms.cypher   # needs the GDS plugin

# MongoDB
mongosh --file mongo/01_indexes.js
mongosh --file mongo/02_crud.js
mongosh --file mongo/03_aggregations.js
mongosh --file mongo/04_transaction.js

# Integrated route search (Neo4j finds the paths, MongoDB supplies real flights, fares and seats)
python app/route_optimizer.py MAA JFK --date 2026-11-01 --pref cheapest --top 3
python app/route_optimizer.py MAA JFK --date 2026-11-01 --pref fastest
python app/route_optimizer.py MAA SYD --pref fewest_stops --cabin BUSINESS

# REST API
python app/api.py
curl "http://localhost:5000/routes?src=MAA&dst=JFK&pref=cheapest&top=3"
curl -X POST localhost:5000/book -H "Content-Type: application/json" -d '{"userId":"U001","flightId":"AI100_2026-11-01"}'
```
Preferences: `cheapest`, `fastest`, `fewest_stops`, `shortest_distance`.

## Mapping to the Review 2 rubric
| Criterion (marks) | Where it is shown |
|---|---|
| Database implementation (2) | `scripts/load_data.py`, `neo4j/01-02`, `mongo/01`, 50 nodes, 346 relationships, 6 collections |
| CRUD operations (3) | `neo4j/03_crud.cypher`, `mongo/02_crud.js`, `POST /book` in the API |
| Advanced NoSQL (5) | Graph traversal and shortest paths (`neo4j/04`), GDS Dijkstra / A* / Yen's (`neo4j/05`), aggregation pipelines with `$lookup`, `$bucket` and `$group` (`mongo/03`), compound index with `explain()` (`mongo/01`), ACID transactions (`mongo/04`, `book_flight`), Neo4j + MongoDB integration (`app/`) |

## Design notes
- Neo4j holds the slow-changing structure (airports and routes with `distanceKm`, `durationMin` and `baseFare`). MongoDB holds the fast-changing data (fares, seats, delays, bookings). The shared key is the IATA airport code.
- `route_optimizer.py` uses plain Cypher variable-length paths for the candidate search, so it works on any Neo4j edition. The GDS algorithms are in `neo4j/05_gds_algorithms.cypher`.
- Candidate paths are pre-ranked using static route weights. They are then re-ranked using real schedules, delays and seat availability from MongoDB, with a 60-minute minimum connection time.
- The flight schema is deliberately flexible. Some flights have `PREMIUM_ECONOMY` fares, `meal`, `codeshare` or `baggageAllowanceKg` and others do not.
- The Review 1 `FARE` and `FLIGHT_STATUS` entities are embedded in the flight document (`fares`, `status`, `delayMin`). `flight_status` is also kept as a separate collection for the history of updates.
