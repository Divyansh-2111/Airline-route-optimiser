// ===== Load data with LOAD CSV (alternative to scripts/load_data.py) =====
// Needs data/*.csv in Neo4j's import folder (docker-compose already mounts ./data there).

LOAD CSV WITH HEADERS FROM 'file:///airports.csv' AS row
MERGE (a:Airport {code: row.code})
SET a.name = row.name, a.city = row.city, a.country = row.country,
    a.lat = toFloat(row.lat), a.lon = toFloat(row.lon);

LOAD CSV WITH HEADERS FROM 'file:///routes.csv' AS row
MATCH (a:Airport {code: row.source}), (b:Airport {code: row.destination})
MERGE (a)-[f:FLIGHT_ROUTE {airline: row.airline}]->(b)
SET f.distanceKm = toInteger(row.distanceKm), f.durationMin = toInteger(row.durationMin),
    f.baseFare = toFloat(row.baseFare), f.flightsPerDay = toInteger(row.flightsPerDay);

// ---- verify (expect 50 nodes, 346 relationships) ----
MATCH (a:Airport) RETURN count(a) AS airports;
MATCH ()-[r:FLIGHT_ROUTE]->() RETURN count(r) AS routes;
