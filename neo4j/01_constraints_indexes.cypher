// ===== Neo4j schema: constraints & indexes =====
CREATE CONSTRAINT airport_code IF NOT EXISTS FOR (a:Airport) REQUIRE a.code IS UNIQUE;
CREATE INDEX airport_country IF NOT EXISTS FOR (a:Airport) ON (a.country);
CREATE INDEX route_airline IF NOT EXISTS FOR ()-[r:FLIGHT_ROUTE]-() ON (r.airline);
SHOW INDEXES;
