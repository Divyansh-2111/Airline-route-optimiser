// mongosh --file mongo/02_crud.js
db = db.getSiblingDB("airline_db");

// ---------------- CREATE ----------------
db.flights.insertOne({
  _id: "EK540_2026-11-10", flightNo: "EK540", airlineCode: "EK", origin: "MAA", destination: "DXB",
  departureTime: ISODate("2026-11-10T02:15:00Z"), arrivalTime: ISODate("2026-11-10T05:30:00Z"),
  durationMin: 225, distanceKm: 2960,
  aircraft: { aircraftId: "EK-W1", model: "Boeing 777-300ER", capacity: 354 },
  status: "SCHEDULED", delayMin: 0,
  fares: [{ class: "ECONOMY", price: 210.0, seatsAvailable: 42 }, { class: "BUSINESS", price: 890.0, seatsAvailable: 6 }],
  meal: "NON_VEG"
});
db.users.insertOne({ _id: "U100", userId: "U100", name: "Divyansh Srivastava", email: "divyansh@example.com", passwordHash: "x" });
db.bookings.insertOne({ _id: "BK9001", bookingId: "BK9001", userId: "U100", flightId: "EK540_2026-11-10",
  class: "ECONOMY", seatNo: "14C", farePaid: 210.0, bookingDate: new Date(), status: "CONFIRMED" });

// ---------------- READ ----------------
printjson(db.flights.findOne({ _id: "EK540_2026-11-10" }));
printjson(db.flights.find({ origin: "MAA", destination: "DXB", status: { $ne: "CANCELLED" } },
                          { flightNo: 1, departureTime: 1, fares: 1 }).sort({ departureTime: 1 }).limit(3).toArray());
// flights with a cheap economy seat available
printjson(db.flights.find({ origin: "MAA", fares: { $elemMatch: { class: "ECONOMY", price: { $lt: 150 }, seatsAvailable: { $gt: 0 } } } },
                          { flightNo: 1, destination: 1 }).limit(5).toArray());
printjson(db.bookings.find({ userId: "U100" }).toArray());
print("total flights:", db.flights.countDocuments());

// ---------------- UPDATE ----------------
db.bookings.updateOne({ _id: "BK9001" }, { $set: { seatNo: "15A" } });
db.flights.updateOne({ _id: "EK540_2026-11-10" }, { $set: { status: "DELAYED", delayMin: 45 } });
db.flights.updateOne({ _id: "EK540_2026-11-10", "fares.class": "ECONOMY" },
                     { $inc: { "fares.$.seatsAvailable": -1 } });                  // one seat sold
db.flights.updateMany({ origin: "MAA", destination: "DXB" }, { $set: { baggageAllowanceKg: 30 } });
db.flight_status.insertOne({ _id: "ST9001", statusId: "ST9001", flightId: "EK540_2026-11-10",
  status: "DELAYED", delayMin: 45, reason: "WEATHER", updatedAt: new Date() });     // delay/weather feed
printjson(db.flights.findOne({ _id: "EK540_2026-11-10" }, { status: 1, delayMin: 1, fares: 1 }));

// ---------------- DELETE ----------------
db.bookings.deleteOne({ _id: "BK9001" });                       // cancel a booking
db.flight_status.deleteMany({ flightId: "EK540_2026-11-10" });
db.flights.deleteOne({ _id: "EK540_2026-11-10" });
db.users.deleteOne({ _id: "U100" });
print("cleanup done");
