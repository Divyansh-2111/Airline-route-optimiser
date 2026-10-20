// mongosh --file mongo/03_aggregations.js
db = db.getSiblingDB("airline_db");

print("\n1) Average ECONOMY fare per route (top 10 most expensive)");
printjson(db.flights.aggregate([
  { $unwind: "$fares" },
  { $match: { "fares.class": "ECONOMY" } },
  { $group: { _id: { origin: "$origin", destination: "$destination" },
              avgFare: { $avg: "$fares.price" }, flights: { $sum: 1 } } },
  { $sort: { avgFare: -1 } }, { $limit: 10 },
  { $project: { _id: 0, route: { $concat: ["$_id.origin", "-", "$_id.destination"] },
                avgFare: { $round: ["$avgFare", 2] }, flights: 1 } }
]).toArray());

print("\n2) Bookings and revenue per airline ($lookup bookings -> flights)");
printjson(db.bookings.aggregate([
  { $lookup: { from: "flights", localField: "flightId", foreignField: "_id", as: "flight" } },
  { $unwind: "$flight" },
  { $group: { _id: "$flight.airlineCode", bookings: { $sum: 1 }, revenue: { $sum: "$farePaid" } } },
  { $lookup: { from: "airlines", localField: "_id", foreignField: "airlineCode", as: "airline" } },
  { $unwind: "$airline" },
  { $project: { _id: 0, airline: "$airline.name", bookings: 1, revenue: { $round: ["$revenue", 2] } } },
  { $sort: { revenue: -1 } }
]).toArray());

print("\n3) Busiest origin airports (number of scheduled departures)");
printjson(db.flights.aggregate([
  { $match: { status: { $ne: "CANCELLED" } } },
  { $group: { _id: "$origin", departures: { $sum: 1 } } },
  { $sort: { departures: -1 } }, { $limit: 5 }
]).toArray());

print("\n4) Delay analysis: average delay and count by reason (flight_status)");
printjson(db.flight_status.aggregate([
  { $match: { status: "DELAYED" } },
  { $group: { _id: "$reason", delayedFlights: { $sum: 1 }, avgDelayMin: { $avg: "$delayMin" } } },
  { $project: { avgDelayMin: { $round: ["$avgDelayMin", 1] }, delayedFlights: 1 } },
  { $sort: { delayedFlights: -1 } }
]).toArray());

print("\n5) Economy fare distribution ($bucket)");
printjson(db.flights.aggregate([
  { $unwind: "$fares" }, { $match: { "fares.class": "ECONOMY" } },
  { $bucket: { groupBy: "$fares.price", boundaries: [0, 100, 250, 500, 1000, 5000],
               default: "5000+", output: { flights: { $sum: 1 } } } }
]).toArray());

print("\n6) Sold-out economy flights per airline");
printjson(db.flights.aggregate([
  { $match: { fares: { $elemMatch: { class: "ECONOMY", seatsAvailable: 0 } } } },
  { $group: { _id: "$airlineCode", soldOut: { $sum: 1 } } }, { $sort: { soldOut: -1 } }
]).toArray());

print("\n7) Flights per cabin class using $facet + the flexible schema (PREMIUM_ECONOMY exists only on some flights)");
printjson(db.flights.aggregate([
  { $unwind: "$fares" },
  { $group: { _id: "$fares.class", flights: { $sum: 1 }, avgPrice: { $avg: "$fares.price" } } },
  { $project: { avgPrice: { $round: ["$avgPrice", 2] }, flights: 1 } }
]).toArray());
