# Review 2 demo script (about 8 minutes)

1. **Show the setup (30 s).** `docker compose ps`, then the repo structure on GitHub.
2. **Database created + data loaded (1 min).**
   - Neo4j Browser: `MATCH (a:Airport) RETURN count(a)` (50) and `MATCH ()-[r]->() RETURN count(r)` (346). Then `MATCH (a:Airport)-[r:FLIGHT_ROUTE]->(b) RETURN a,r,b LIMIT 80` for the graph picture.
   - MongoDB Compass or mongosh: `db.flights.countDocuments()` (2076) and `show collections`.
   - Show one flight document to point out the nested `fares` and `aircraft` and the optional fields.
3. **CRUD (2 min).** Run `neo4j/03_crud.cypher` and `mongo/02_crud.js`. Say "create, read, update, delete" as each block runs.
4. **Advanced Neo4j (2 min).**
   - `shortestPath` for MAA to JFK.
   - Cheapest / fastest / shortest distance with up to 3 layovers (`04_route_queries.cypher`).
   - GDS Dijkstra and Yen's top-3 (`05_gds_algorithms.cypher`).
5. **Advanced MongoDB (1.5 min).**
   - Aggregation: average fare per route, and bookings per airline using `$lookup`.
   - Index: `explain()` showing IXSCAN vs COLLSCAN.
   - Transaction: `04_transaction.js`, seats go from N to N-1 and a booking appears.
6. **Integration (1 min).** `python app/route_optimizer.py MAA JFK --pref cheapest` then `--pref fastest`. Explain that Neo4j finds the paths, MongoDB supplies live fares and seats, and the result is ranked.
7. **Close (30 s).** Review 3 plan: SQL join vs Neo4j multi-hop benchmark, API polish, final report.
