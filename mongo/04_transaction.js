// Multi-document ACID transaction: book a seat = decrement seats + insert booking, atomically.
// Requires a replica set (docker-compose.yml starts one).   mongosh --file mongo/04_transaction.js
const conn = db.getMongo();
const session = conn.startSession();
const sdb = session.getDatabase("airline_db");

const flightId = "AI100_2026-11-01";
const before = sdb.flights.findOne({ _id: flightId }, { fares: 1 });
print("economy seats before:", before.fares.find(f => f.class === "ECONOMY").seatsAvailable);

try {
  session.withTransaction(() => {
    const r = sdb.flights.updateOne(
      { _id: flightId, fares: { $elemMatch: { class: "ECONOMY", seatsAvailable: { $gt: 0 } } } },
      { $inc: { "fares.$.seatsAvailable": -1 } });
    if (r.modifiedCount !== 1) throw new Error("No seat available - rolling back");
    sdb.bookings.insertOne({ _id: "BKTXN1", bookingId: "BKTXN1", userId: "U001", flightId: flightId,
      class: "ECONOMY", seatNo: "22F", farePaid: before.fares[0].price, bookingDate: new Date(), status: "CONFIRMED" });
  });
  print("transaction committed");
} catch (e) {
  print("transaction aborted:", e.message);
} finally {
  session.endSession();
}
const after = db.getSiblingDB("airline_db").flights.findOne({ _id: flightId }, { fares: 1 });
print("economy seats after:", after.fares.find(f => f.class === "ECONOMY").seatsAvailable);
// cleanup:  db.bookings.deleteOne({_id:"BKTXN1"}); db.flights.updateOne({_id:"AI100_2026-11-01","fares.class":"ECONOMY"},{$inc:{"fares.$.seatsAvailable":1}})
