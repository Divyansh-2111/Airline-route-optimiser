// mongosh --file mongo/01_indexes.js
db = db.getSiblingDB("airline_db");

db.flights.createIndex({ origin: 1, destination: 1, departureTime: 1 }, { name: "route_time_idx" });
db.flights.createIndex({ airlineCode: 1 }, { name: "airline_idx" });
db.users.createIndex({ email: 1 }, { unique: true, name: "email_unique" });
db.bookings.createIndex({ userId: 1 }, { name: "booking_user_idx" });
db.bookings.createIndex({ flightId: 1 }, { name: "booking_flight_idx" });
db.flight_status.createIndex({ flightId: 1, updatedAt: -1 }, { name: "status_flight_idx" });

printjson(db.flights.getIndexes());

// Show the index being used (look for IXSCAN and a small totalDocsExamined)
const plan = db.flights
  .find({ origin: "MAA", destination: "DXB", departureTime: { $gte: ISODate("2026-11-01T00:00:00Z") } })
  .explain("executionStats");
print("stage:", plan.queryPlanner.winningPlan.stage || plan.queryPlanner.winningPlan.inputStage.stage);
print("docsExamined:", plan.executionStats.totalDocsExamined, " returned:", plan.executionStats.nReturned);

// Compare without the index:
const plan2 = db.flights
  .find({ origin: "MAA", destination: "DXB" }).hint({ $natural: 1 }).explain("executionStats");
print("COLLSCAN docsExamined:", plan2.executionStats.totalDocsExamined);
