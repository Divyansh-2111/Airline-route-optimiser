#!/usr/bin/env python3
"""
Generate the sample dataset for the Airline Route Optimizer (Review 2).

Outputs (in ../data):
  airports.csv, routes.csv                        -> Neo4j graph
  airlines.json, aircraft.json, users.json,
  flights.json, bookings.json, flight_status.json -> MongoDB

Dates are written as MongoDB extended JSON ({"$date": ...}) so the files work with
both `mongoimport --jsonArray` and bson.json_util in load_data.py.
All flight times are stored in UTC to keep layover maths simple.
The seed is fixed, so the output is reproducible.
"""
import csv
import hashlib
import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

random.seed(459)
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(DATA, exist_ok=True)

DATES = ["2026-11-01", "2026-11-02", "2026-11-03"]

AIRPORTS_RAW = """
MAA|Chennai International|Chennai|India|12.99|80.18
DEL|Indira Gandhi International|Delhi|India|28.56|77.10
BOM|Chhatrapati Shivaji Maharaj Intl|Mumbai|India|19.09|72.87
BLR|Kempegowda International|Bengaluru|India|13.20|77.71
HYD|Rajiv Gandhi International|Hyderabad|India|17.24|78.43
CCU|Netaji Subhas Chandra Bose Intl|Kolkata|India|22.65|88.45
COK|Cochin International|Kochi|India|10.15|76.40
GOI|Dabolim Airport|Goa|India|15.38|73.83
AMD|Sardar Vallabhbhai Patel Intl|Ahmedabad|India|23.07|72.63
PNQ|Pune Airport|Pune|India|18.58|73.92
DXB|Dubai International|Dubai|UAE|25.25|55.36
DOH|Hamad International|Doha|Qatar|25.27|51.61
AUH|Zayed International|Abu Dhabi|UAE|24.43|54.65
MCT|Muscat International|Muscat|Oman|23.59|58.28
SIN|Changi Airport|Singapore|Singapore|1.36|103.99
KUL|Kuala Lumpur International|Kuala Lumpur|Malaysia|2.75|101.71
BKK|Suvarnabhumi Airport|Bangkok|Thailand|13.69|100.75
HKG|Hong Kong International|Hong Kong|Hong Kong|22.31|113.91
NRT|Narita International|Tokyo|Japan|35.77|140.39
ICN|Incheon International|Seoul|South Korea|37.46|126.44
PVG|Pudong International|Shanghai|China|31.14|121.81
PEK|Beijing Capital International|Beijing|China|40.08|116.58
CGK|Soekarno-Hatta International|Jakarta|Indonesia|-6.13|106.66
CMB|Bandaranaike International|Colombo|Sri Lanka|7.18|79.88
LHR|Heathrow Airport|London|UK|51.47|-0.45
CDG|Charles de Gaulle|Paris|France|49.01|2.55
FRA|Frankfurt Airport|Frankfurt|Germany|50.03|8.57
AMS|Schiphol Airport|Amsterdam|Netherlands|52.31|4.76
IST|Istanbul Airport|Istanbul|Turkey|41.26|28.74
MAD|Adolfo Suarez Madrid-Barajas|Madrid|Spain|40.49|-3.57
FCO|Leonardo da Vinci-Fiumicino|Rome|Italy|41.80|12.25
ZRH|Zurich Airport|Zurich|Switzerland|47.46|8.55
LIS|Humberto Delgado Airport|Lisbon|Portugal|38.78|-9.14
DME|Domodedovo International|Moscow|Russia|55.41|37.91
JFK|John F. Kennedy Intl|New York|USA|40.64|-73.78
LAX|Los Angeles International|Los Angeles|USA|33.94|-118.41
ORD|O'Hare International|Chicago|USA|41.98|-87.90
SFO|San Francisco International|San Francisco|USA|37.62|-122.38
ATL|Hartsfield-Jackson Atlanta Intl|Atlanta|USA|33.64|-84.43
MIA|Miami International|Miami|USA|25.79|-80.29
DFW|Dallas/Fort Worth International|Dallas|USA|32.90|-97.04
SEA|Seattle-Tacoma International|Seattle|USA|47.45|-122.31
YYZ|Toronto Pearson International|Toronto|Canada|43.68|-79.63
MEX|Benito Juarez International|Mexico City|Mexico|19.44|-99.07
GRU|Guarulhos International|Sao Paulo|Brazil|-23.43|-46.47
SYD|Sydney Kingsford Smith|Sydney|Australia|-33.94|151.18
MEL|Melbourne Airport|Melbourne|Australia|-37.67|144.84
JNB|O.R. Tambo International|Johannesburg|South Africa|-26.14|28.25
CAI|Cairo International|Cairo|Egypt|30.12|31.41
NBO|Jomo Kenyatta International|Nairobi|Kenya|-1.32|36.93
"""

# code: (name, country, fare factor)
AIRLINES = {
    "AI": ("Air India", "India", 0.95), "6E": ("IndiGo", "India", 0.80),
    "EK": ("Emirates", "UAE", 1.10), "EY": ("Etihad Airways", "UAE", 1.05),
    "QR": ("Qatar Airways", "Qatar", 1.10), "SQ": ("Singapore Airlines", "Singapore", 1.15),
    "CX": ("Cathay Pacific", "Hong Kong", 1.10), "JL": ("Japan Airlines", "Japan", 1.10),
    "BA": ("British Airways", "UK", 1.10), "LH": ("Lufthansa", "Germany", 1.05),
    "AF": ("Air France", "France", 1.05), "TK": ("Turkish Airlines", "Turkey", 0.95),
    "AA": ("American Airlines", "USA", 1.00), "UA": ("United Airlines", "USA", 1.00),
    "DL": ("Delta Air Lines", "USA", 1.00), "QF": ("Qantas", "Australia", 1.10),
}

# Undirected pairs "A-B:AIRLINE"; each becomes two directed routes.
ROUTES_RAW = """
MAA-DEL:AI MAA-BOM:6E MAA-BLR:6E MAA-HYD:6E MAA-CCU:AI MAA-COK:AI DEL-BOM:AI DEL-BLR:6E
DEL-HYD:6E DEL-CCU:AI DEL-GOI:6E DEL-AMD:6E BOM-BLR:6E BOM-GOI:6E BOM-HYD:AI BOM-AMD:6E
BOM-PNQ:6E BLR-HYD:6E BLR-COK:6E BLR-GOI:6E CCU-BLR:6E PNQ-DEL:AI COK-BOM:AI
MAA-DXB:EK MAA-SIN:SQ MAA-KUL:AI MAA-CMB:AI MAA-DOH:QR DEL-DXB:EK DEL-LHR:BA DEL-JFK:AI
DEL-FRA:LH DEL-SIN:SQ DEL-BKK:AI DEL-DOH:QR DEL-AUH:EY DEL-HKG:CX DEL-MCT:AI DEL-PEK:AI
BOM-DXB:EK BOM-LHR:BA BOM-SIN:SQ BOM-DOH:QR BOM-AUH:EY BOM-CDG:AF BOM-MCT:AI BLR-DXB:EK
BLR-SIN:SQ BLR-FRA:LH HYD-DXB:EK HYD-DOH:QR CCU-BKK:AI CCU-DXB:EK COK-DXB:EK COK-DOH:QR
COK-AUH:EY
DXB-MCT:EK DXB-LHR:EK DXB-JFK:EK DXB-SIN:EK DXB-BKK:EK DXB-SYD:EK DXB-FRA:EK DXB-CDG:EK
DXB-IST:TK DXB-JNB:EK DXB-CAI:EK DXB-NBO:EK DXB-DOH:EK DOH-LHR:QR DOH-JFK:QR DOH-SIN:QR
DOH-CDG:QR DOH-SYD:QR DOH-JNB:QR DOH-IST:QR AUH-LHR:EY AUH-JFK:EY AUH-SYD:EY
SIN-SYD:SQ SIN-MEL:SQ SIN-HKG:CX SIN-NRT:SQ SIN-LHR:SQ SIN-KUL:SQ SIN-CGK:SQ SIN-BKK:SQ
SIN-ICN:SQ SIN-CMB:SQ HKG-NRT:CX HKG-LAX:CX HKG-JFK:CX HKG-SYD:CX HKG-PVG:CX HKG-BKK:CX
NRT-LAX:JL NRT-SFO:JL NRT-ICN:JL NRT-JFK:JL NRT-SEA:DL ICN-SFO:UA ICN-LAX:UA PVG-SFO:UA
PVG-NRT:JL PEK-NRT:JL PEK-FRA:LH PEK-LAX:UA PEK-PVG:CX PEK-ICN:CX KUL-SYD:QF KUL-BKK:SQ
KUL-CGK:SQ SYD-MEL:QF SYD-LAX:QF
LHR-JFK:BA LHR-CDG:BA LHR-FRA:BA LHR-AMS:BA LHR-IST:TK LHR-MAD:BA LHR-FCO:BA LHR-ZRH:BA
LHR-LIS:BA LHR-ORD:AA LHR-LAX:BA LHR-JNB:BA FRA-JFK:LH FRA-ORD:LH FRA-IST:LH FRA-ZRH:LH
FRA-DME:LH CDG-JFK:AF CDG-MAD:AF CDG-FCO:AF CDG-AMS:AF CDG-GRU:AF IST-JFK:TK IST-CAI:TK
IST-JNB:TK IST-DME:TK IST-FCO:TK MAD-GRU:BA MAD-MEX:BA MAD-JFK:BA LIS-GRU:BA LIS-JFK:BA
AMS-JFK:AF ZRH-JFK:LH
JFK-LAX:AA JFK-ORD:AA JFK-ATL:DL JFK-MIA:AA JFK-YYZ:AA JFK-SFO:UA LAX-SFO:UA LAX-SEA:DL
LAX-DFW:AA LAX-ORD:UA LAX-MEX:AA ORD-DFW:AA ORD-ATL:DL ORD-YYZ:UA ATL-MIA:DL ATL-DFW:DL
MIA-GRU:AA MIA-MEX:AA DFW-MEX:AA SEA-SFO:UA SEA-ORD:UA GRU-JFK:AA YYZ-LHR:AA
JNB-NBO:QR NBO-CAI:TK
"""

NARROW = [("Airbus A320-200", 180), ("Boeing 737-800", 189)]
WIDE = [("Boeing 777-300ER", 354), ("Airbus A350-900", 325), ("Boeing 787-9", 296), ("Airbus A380-800", 489)]


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def dt(d):  # MongoDB extended-JSON date
    return {"$date": d.strftime("%Y-%m-%dT%H:%M:%SZ")}


def dump(name, obj, compact=False):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, separators=(",", ":"))
        else:
            json.dump(obj, f, indent=2)


# ---------------- airports ----------------
airports = {}
for line in AIRPORTS_RAW.strip().splitlines():
    code, name, city, country, lat, lon = line.split("|")
    airports[code] = dict(code=code, name=name, city=city, country=country, lat=float(lat), lon=float(lon))
with open(os.path.join(DATA, "airports.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["code", "name", "city", "country", "lat", "lon"])
    w.writeheader()
    w.writerows(airports.values())

# ---------------- routes ----------------
directed, seen = [], set()
for tok in ROUTES_RAW.split():
    pair, al = tok.split(":")
    a, b = pair.split("-")
    assert a in airports and b in airports and al in AIRLINES, tok
    for s, d in ((a, b), (b, a)):
        if (s, d) in seen:
            continue
        seen.add((s, d))
        pa, pb = airports[s], airports[d]
        dist = round(haversine(pa["lat"], pa["lon"], pb["lat"], pb["lon"]))
        dur = round(dist / 830 * 60 + 30)
        base = round((0.075 * dist + 40) * AIRLINES[al][2], 2)
        directed.append(dict(source=s, destination=d, airline=al, distanceKm=dist,
                             durationMin=dur, baseFare=base, flightsPerDay=2))
used = {r["source"] for r in directed} | {r["destination"] for r in directed}
assert used == set(airports), set(airports) - used
with open(os.path.join(DATA, "routes.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(directed[0].keys()))
    w.writeheader()
    w.writerows(directed)

# ---------------- airlines & aircraft ----------------
airlines_docs = [dict(_id=c, airlineCode=c, name=v[0], country=v[1]) for c, v in AIRLINES.items()]
dump("airlines.json", airlines_docs)

aircraft_docs, fleet = [], {}
for code in AIRLINES:
    fleet[code] = {"N": [], "W": []}
    for i in range(1, 3):
        for kind, pool in (("N", NARROW), ("W", WIDE)):
            model, cap = pool[(i - 1) % len(pool)] if kind == "N" else pool[(2 * (i - 1)) % len(pool)]
            aid = f"{code}-{kind}{i}"
            aircraft_docs.append(dict(_id=aid, aircraftId=aid, model=model, totalSeats=cap, airlineCode=code))
            fleet[code][kind].append(dict(aircraftId=aid, model=model, capacity=cap))
dump("aircraft.json", aircraft_docs)

# ---------------- flights & flight_status ----------------
flights, statuses = [], []
for idx, r in enumerate(directed):
    narrow = r["distanceKm"] < 2500
    for date in DATES:
        for slot in (0, 1):
            ac = random.choice(fleet[r["airline"]]["N" if narrow else "W"])
            dep = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(
                hours=random.randint(0, 10) + 12 * slot, minutes=random.choice([0, 15, 30, 45]))
            arr = dep + timedelta(minutes=r["durationMin"])
            fno = f"{r['airline']}{100 + (idx * 2 + slot) % 900}"
            cap = ac["capacity"]
            econ_seats = 0 if random.random() < 0.03 else random.randint(5, int(cap * 0.35))
            econ_price = round(r["baseFare"] * random.uniform(0.9, 1.3), 2)
            fares = [{"class": "ECONOMY", "price": econ_price, "seatsAvailable": econ_seats},
                     {"class": "BUSINESS", "price": round(econ_price * random.uniform(3.0, 4.0), 2),
                      "seatsAvailable": random.randint(0, min(24, cap // 10))}]
            if not narrow and random.random() < 0.4:  # flexible schema: only some flights have this class
                fares.insert(1, {"class": "PREMIUM_ECONOMY", "price": round(econ_price * 1.8, 2),
                                 "seatsAvailable": random.randint(0, 20)})
            roll, delay = random.random(), 0
            status = "SCHEDULED"
            if roll < 0.03:
                status = "CANCELLED"
            elif roll < 0.10:
                status, delay = "DELAYED", random.choice([20, 35, 45, 60, 90, 120])
            doc = {
                "_id": f"{fno}_{date}", "flightNo": fno, "airlineCode": r["airline"],
                "origin": r["source"], "destination": r["destination"],
                "departureTime": dt(dep), "arrivalTime": dt(arr),
                "durationMin": r["durationMin"], "distanceKm": r["distanceKm"],
                "aircraft": dict(aircraftId=ac["aircraftId"], model=ac["model"], capacity=cap),
                "status": status, "delayMin": delay, "fares": fares,
            }
            # airline-specific optional attributes (the point of using a document store)
            if random.random() < 0.6:
                doc["meal"] = random.choice(["VEG", "NON_VEG", "SNACK", "NONE"])
            if not narrow:
                doc["baggageAllowanceKg"] = random.choice([23, 30, 35])
            if random.random() < 0.15:
                doc["codeshare"] = random.sample([c for c in AIRLINES if c != r["airline"]], 2)
            flights.append(doc)
            if status != "SCHEDULED" or random.random() < 0.10:
                sid = f"ST{len(statuses) + 1:04d}"
                statuses.append({
                    "_id": sid, "statusId": sid, "flightId": doc["_id"],
                    "status": "ON_TIME" if status == "SCHEDULED" else status, "delayMin": delay,
                    "reason": random.choice(["WEATHER", "ATC", "TECHNICAL", "CREW"]) if status != "SCHEDULED" else "NONE",
                    "updatedAt": dt(dep - timedelta(hours=3)),
                })
dump("flights.json", flights, compact=True)
dump("flight_status.json", statuses)

# ---------------- users & bookings ----------------
NAMES = ["Aarav Mehta", "Diya Nair", "Rohan Iyer", "Ananya Rao", "Karthik Subramanian", "Meera Pillai",
         "Vikram Singh", "Isha Kapoor", "Arjun Reddy", "Sneha Das", "Rahul Verma", "Priya Menon",
         "Aditya Joshi", "Kavya Krishnan", "Siddharth Jain", "Neha Bansal", "Manoj Kumar", "Pooja Shah",
         "Harish Babu", "Lakshmi Narayan", "Imran Khan", "Fatima Sheikh", "John Mathew", "Sara Thomas",
         "Tarun Gupta"]
users = []
for i, n in enumerate(NAMES, 1):
    email = n.lower().replace(" ", ".") + "@example.com"
    users.append(dict(_id=f"U{i:03d}", userId=f"U{i:03d}", name=n, email=email,
                      passwordHash=hashlib.sha256(("Passw0rd!" + email).encode()).hexdigest()))
dump("users.json", users)

bookable = [f for f in flights if f["status"] != "CANCELLED" and f["fares"][0]["seatsAvailable"] > 0]
bookings = []
for i, f in enumerate(random.sample(bookable, 40), 1):
    cls = random.choice(["ECONOMY", "ECONOMY", "ECONOMY", "BUSINESS"])
    fare = next(x for x in f["fares"] if x["class"] == cls)
    bdate = datetime(2026, 10, random.randint(1, 19), random.randint(6, 22), random.randint(0, 59), tzinfo=timezone.utc)
    bookings.append({
        "_id": f"BK{i:04d}", "bookingId": f"BK{i:04d}", "userId": random.choice(users)["userId"],
        "flightId": f["_id"], "class": cls, "seatNo": f"{random.randint(1, 40)}{random.choice('ABCDEF')}",
        "farePaid": fare["price"], "bookingDate": dt(bdate), "status": "CONFIRMED",
    })
dump("bookings.json", bookings)

print(f"airports={len(airports)} routes(directed)={len(directed)} airlines={len(airlines_docs)} "
      f"aircraft={len(aircraft_docs)} flights={len(flights)} flight_status={len(statuses)} "
      f"users={len(users)} bookings={len(bookings)}")
