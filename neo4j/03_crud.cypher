// ===== Neo4j CRUD demo =====

// ---- CREATE ----
CREATE (:Airport {code:'TRZ', name:'Tiruchirappalli International', city:'Tiruchirappalli',
                  country:'India', lat:10.77, lon:78.71});

MATCH (a:Airport {code:'MAA'}), (b:Airport {code:'TRZ'})
CREATE (a)-[:FLIGHT_ROUTE {airline:'6E', distanceKm:290, durationMin:65, baseFare:55.0, flightsPerDay:2}]->(b);

// ---- READ ----
MATCH (a:Airport {code:'MAA'})-[r:FLIGHT_ROUTE]->(b)
RETURN b.code AS destination, b.city AS city, r.airline AS airline, r.distanceKm AS km, r.baseFare AS fare
ORDER BY fare;

MATCH (a:Airport) WHERE a.country = 'India' RETURN a.code, a.city ORDER BY a.code;

// ---- UPDATE ----
MATCH (:Airport {code:'MAA'})-[r:FLIGHT_ROUTE {airline:'6E'}]->(:Airport {code:'TRZ'})
SET r.baseFare = 60.0, r.flightsPerDay = 3
RETURN r;

MATCH (a:Airport {code:'TRZ'}) SET a.terminals = 1 RETURN a;      // schema-free: add a new property

// ---- DELETE ----
MATCH (:Airport {code:'MAA'})-[r:FLIGHT_ROUTE]->(:Airport {code:'TRZ'}) DELETE r;   // one relationship
MATCH (a:Airport {code:'TRZ'}) DETACH DELETE a;                                     // node + its relationships
