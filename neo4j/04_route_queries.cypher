// ===== Neo4j route optimisation (plain Cypher - works on any edition) =====

// 1. Fewest stops: shortestPath / allShortestPaths
MATCH p = shortestPath((s:Airport {code:'MAA'})-[:FLIGHT_ROUTE*..4]->(d:Airport {code:'JFK'}))
RETURN [n IN nodes(p) | n.code] AS route, length(p) AS hops;

MATCH p = allShortestPaths((s:Airport {code:'MAA'})-[:FLIGHT_ROUTE*..4]->(d:Airport {code:'JFK'}))
RETURN [n IN nodes(p) | n.code] AS route, length(p) AS hops;

// 2. Weighted: CHEAPEST (up to 3 layovers => max 4 flights)
MATCH p = (s:Airport {code:'MAA'})-[:FLIGHT_ROUTE*1..4]->(d:Airport {code:'JFK'})
WHERE ALL(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
RETURN [n IN nodes(p) | n.code] AS route,
       reduce(c = 0.0, r IN relationships(p) | c + r.baseFare) AS totalFare
ORDER BY totalFare ASC LIMIT 5;

// 3. Weighted: FASTEST (flight time only, layovers come from MongoDB schedules)
MATCH p = (s:Airport {code:'MAA'})-[:FLIGHT_ROUTE*1..4]->(d:Airport {code:'JFK'})
WHERE ALL(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
RETURN [n IN nodes(p) | n.code] AS route,
       reduce(t = 0, r IN relationships(p) | t + r.durationMin) AS totalMinutes
ORDER BY totalMinutes ASC LIMIT 5;

// 4. Weighted: SHORTEST DISTANCE
MATCH p = (s:Airport {code:'MAA'})-[:FLIGHT_ROUTE*1..4]->(d:Airport {code:'JFK'})
WHERE ALL(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
RETURN [n IN nodes(p) | n.code] AS route,
       reduce(k = 0, r IN relationships(p) | k + r.distanceKm) AS totalKm
ORDER BY totalKm ASC LIMIT 5;

// 5. Which airports are used as layovers for MAA -> JFK?
MATCH p = (:Airport {code:'MAA'})-[:FLIGHT_ROUTE*2..3]->(:Airport {code:'JFK'})
UNWIND nodes(p)[1..-1] AS layover
RETURN layover.code AS layoverAirport, count(*) AS timesUsed ORDER BY timesUsed DESC;

// 6. Network analysis: busiest hubs by number of direct routes (degree)
MATCH (a:Airport)-[r:FLIGHT_ROUTE]->()
RETURN a.code AS airport, a.city AS city, count(r) AS outgoingRoutes
ORDER BY outgoingRoutes DESC LIMIT 10;

// 7. Everything reachable from Chennai within 2 flights
MATCH (:Airport {code:'MAA'})-[:FLIGHT_ROUTE*1..2]->(x:Airport)
RETURN count(DISTINCT x) AS reachableAirports;

// 8. Airlines operating out of each country
MATCH (a:Airport)-[r:FLIGHT_ROUTE]->()
RETURN a.country AS country, collect(DISTINCT r.airline) AS airlines ORDER BY country;

// 9. Indexing: compare plans
EXPLAIN MATCH (a:Airport {code:'MAA'}) RETURN a;            // NodeUniqueIndexSeek
PROFILE MATCH (a:Airport) WHERE a.country = 'India' RETURN count(a);   // uses airport_country index

// 10. Transaction demo - run in cypher-shell (or Browser with :auto is NOT needed here):
//   :begin
//   MATCH (:Airport {code:'MAA'})-[r:FLIGHT_ROUTE {airline:'6E'}]->(:Airport {code:'BLR'}) SET r.baseFare = 999;
//   MATCH (:Airport {code:'MAA'})-[r:FLIGHT_ROUTE {airline:'6E'}]->(:Airport {code:'BLR'}) RETURN r.baseFare;
//   :rollback        // fare is back to its original value  (use :commit to keep it)
