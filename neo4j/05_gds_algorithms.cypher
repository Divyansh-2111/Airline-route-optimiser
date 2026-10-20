// ===== Graph Data Science library (requires the GDS plugin - included in docker-compose.yml) =====

// Project the in-memory graph (with lat/lon for A*)
CALL gds.graph.project(
  'airNet',
  {Airport: {properties: ['lat', 'lon']}},
  {FLIGHT_ROUTE: {properties: ['distanceKm', 'durationMin', 'baseFare']}}
);

// Dijkstra - cheapest MAA -> JFK
MATCH (s:Airport {code:'MAA'}), (t:Airport {code:'JFK'})
CALL gds.shortestPath.dijkstra.stream('airNet',
     {sourceNode: s, targetNode: t, relationshipWeightProperty: 'baseFare'})
YIELD totalCost, nodeIds
RETURN totalCost AS fare, [n IN nodeIds | gds.util.asNode(n).code] AS route;

// Dijkstra - fastest (flight minutes)
MATCH (s:Airport {code:'MAA'}), (t:Airport {code:'JFK'})
CALL gds.shortestPath.dijkstra.stream('airNet',
     {sourceNode: s, targetNode: t, relationshipWeightProperty: 'durationMin'})
YIELD totalCost, nodeIds
RETURN totalCost AS minutes, [n IN nodeIds | gds.util.asNode(n).code] AS route;

// Dijkstra - shortest distance
MATCH (s:Airport {code:'MAA'}), (t:Airport {code:'JFK'})
CALL gds.shortestPath.dijkstra.stream('airNet',
     {sourceNode: s, targetNode: t, relationshipWeightProperty: 'distanceKm'})
YIELD totalCost, nodeIds
RETURN totalCost AS km, [n IN nodeIds | gds.util.asNode(n).code] AS route;

// A* - uses lat/lon as the heuristic
MATCH (s:Airport {code:'MAA'}), (t:Airport {code:'JFK'})
CALL gds.shortestPath.astar.stream('airNet',
     {sourceNode: s, targetNode: t, latitudeProperty: 'lat', longitudeProperty: 'lon',
      relationshipWeightProperty: 'distanceKm'})
YIELD totalCost, nodeIds
RETURN totalCost AS km, [n IN nodeIds | gds.util.asNode(n).code] AS route;

// Yen's - top 3 cheapest alternatives
MATCH (s:Airport {code:'MAA'}), (t:Airport {code:'JFK'})
CALL gds.shortestPath.yens.stream('airNet',
     {sourceNode: s, targetNode: t, k: 3, relationshipWeightProperty: 'baseFare'})
YIELD index, totalCost, nodeIds
RETURN index AS rank, totalCost AS fare, [n IN nodeIds | gds.util.asNode(n).code] AS route;

// Bonus - most connected hubs (PageRank / degree centrality)
CALL gds.degree.stream('airNet') YIELD nodeId, score
RETURN gds.util.asNode(nodeId).code AS airport, score ORDER BY score DESC LIMIT 10;

// Clean up
CALL gds.graph.drop('airNet');
