#!/usr/bin/env python3
"""Generate a synthetic webshop data warehouse (DuckDB) for the WJAX 2026 demo.

Everything in here is fake: names, e-mail addresses (the .test TLD is reserved by
RFC 2606), phone numbers and support-ticket texts. The data is shaped like the
event data a real shop would keep in its warehouse, including personal data, so
the demo shows what an agent sees when it works on sensitive tables.

The data contains one planted incident for the agent to find. It is described in
DEMO.md ("answer key"), not here, so that a reader of this file does not get the
solution for free.

Usage:
    python data/generate.py                 # writes data/warehouse.duckdb
    python data/generate.py --out other.duckdb --seed 7
"""

import argparse
import csv
import datetime as dt
import pathlib
import random
import tempfile

import duckdb

DAYS = 42
BASE_SESSIONS = 2800  # per day, before weekday and noise factors
DEFAULT_END = dt.date(2026, 11, 1)  # last day with data (a Sunday)
INCIDENT_START = dt.date(2026, 10, 26)

FIRST = ["Anna", "Ben", "Clara", "David", "Emma", "Felix", "Greta", "Hannes", "Ida", "Jonas",
         "Katja", "Lukas", "Mia", "Noah", "Olivia", "Paul", "Rita", "Samuel", "Tina", "Uwe",
         "Vera", "Walter", "Xenia", "Yannick", "Zoe", "Lena", "Max", "Sophie", "Tim", "Nora"]
LAST = ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker",
        "Schulz", "Hoffmann", "Koch", "Richter", "Klein", "Wolf", "Schröder", "Neumann",
        "Schwarz", "Zimmermann", "Braun", "Krüger", "Hofmann", "Hartmann", "Lange", "Werner",
        "Krause", "Lehmann", "Köhler", "Maier", "Herrmann", "König"]
CITIES = ["Hamburg", "Berlin", "München", "Köln", "Frankfurt", "Stuttgart", "Düsseldorf",
          "Leipzig", "Dresden", "Hannover", "Nürnberg", "Bremen", "Münster", "Kiel", "Freiburg"]
CATEGORIES = ["Jacken", "Schuhe", "Rucksäcke", "Zelte", "Schlafsäcke", "Zubehör"]

SOURCES = ["organic", "direct", "google_ads", "newsletter", "instagram", "tiktok"]
SOURCE_WEIGHTS = [35, 25, 15, 10, 8, 7]
SOURCE_CART_FACTOR = {"organic": 0.9, "direct": 1.3, "google_ads": 1.0,
                      "newsletter": 1.6, "instagram": 0.7, "tiktok": 0.5}

WEEKDAY_FACTOR = [1.0, 0.98, 0.97, 1.0, 1.05, 1.15, 1.2]  # Mon..Sun
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 3, 5, 6, 6, 6, 6, 7, 6, 6, 6, 6, 7, 9, 10, 10, 8, 4, 2]

TICKET_SUBJECTS = [
    ("Lieferung verspätet", "Meine Bestellung {oid} sollte laut Tracking längst da sein. "
     "Können Sie bitte nachsehen? Kundennummer {cid}, {first} {last}."),
    ("Falsche Größe geliefert", "Ich habe in der Bestellung {oid} Größe 42 bestellt, es kam 44. "
     "Wie läuft der Umtausch? Viele Grüße, {first} {last} aus {city}."),
    ("Rechnung als PDF", "Bitte schicken Sie mir die Rechnung zu Bestellung {oid} an {email}. "
     "{first} {last}, Kundennummer {cid}."),
    ("Rücksendung", "Ich möchte Artikel aus Bestellung {oid} zurückschicken. Bitte Retourenlabel an {email}. "
     "{first} {last}, {city}."),
    ("Gutschein funktioniert nicht", "Der Code aus dem Newsletter wird nicht akzeptiert. "
     "Kundennummer {cid}, {first} {last}, {email}."),
]
APPLE_PAY_TICKET = (
    "Apple Pay funktioniert nicht",
    "Hallo, ich habe jetzt mehrmals versucht, mit Apple Pay zu bezahlen, die App zeigt nur einen Fehler. "
    "Ich bin {first} {last} aus {city}, Kundennummer {cid}, iPhone mit der neuen App-Version. "
    "Bitte melden Sie sich unter {email} oder {phone}.",
)

SCHEMA = """
CREATE TABLE customers (
    customer_id INTEGER, first_name VARCHAR, last_name VARCHAR, email VARCHAR, phone VARCHAR,
    city VARCHAR, postcode VARCHAR, birth_year INTEGER, created_at TIMESTAMP, marketing_opt_in BOOLEAN);
CREATE TABLE products (
    product_id INTEGER, name VARCHAR, category VARCHAR, price_eur DECIMAL(8,2));
CREATE TABLE sessions (
    session_id INTEGER, customer_id INTEGER, started_at TIMESTAMP, platform VARCHAR,
    app_version VARCHAR, browser VARCHAR, utm_source VARCHAR);
CREATE TABLE events (
    event_id INTEGER, session_id INTEGER, ts TIMESTAMP, event_name VARCHAR, product_id INTEGER,
    payment_method VARCHAR, error_code VARCHAR);
CREATE TABLE orders (
    order_id INTEGER, customer_id INTEGER, session_id INTEGER, ts TIMESTAMP,
    amount_eur DECIMAL(10,2), payment_method VARCHAR, status VARCHAR);
CREATE TABLE support_tickets (
    ticket_id INTEGER, customer_id INTEGER, created_at TIMESTAMP, subject VARCHAR, body VARCHAR);
"""


class Generator:
    def __init__(self, seed: int, end: dt.date):
        self.rnd = random.Random(seed)
        self.end = end
        self.start = end - dt.timedelta(days=DAYS - 1)
        self.customers: list[dict] = []
        self.sessions: list[dict] = []
        self.events: list[dict] = []
        self.orders: list[dict] = []
        self.tickets: list[dict] = []
        self.products = self._products()
        self.next_event = 1
        self.next_order = 100_000
        self._seed_customers(8000)

    # -- reference data ---------------------------------------------------------

    def _products(self):
        names = {
            "Jacken": ["Fjord Shell", "Nordwind Parka", "Küstenjacke", "Trail Softshell", "Daunenweste"],
            "Schuhe": ["Moorland GTX", "Gipfel Pro", "Wattwanderer", "City Trekker", "Winterstiefel"],
            "Rucksäcke": ["Tagestour 24", "Hüttentour 38", "Expedition 65", "Pendler 18"],
            "Zelte": ["Solo Tarn", "Duo Fjell", "Familienzelt Nord"],
            "Schlafsäcke": ["Sommer 5", "Dreijahreszeiten", "Winter -15"],
            "Zubehör": ["Stirnlampe", "Trinkflasche", "Trekkingstöcke", "Gaskocher", "Merino-Socken"],
        }
        out, pid = [], 1
        for cat, items in names.items():
            for name in items:
                out.append({"product_id": pid, "name": name, "category": cat,
                            "price_eur": round(self.rnd.uniform(9, 299), 2)})
                pid += 1
        return out

    def _new_customer(self, created_at: dt.datetime) -> dict:
        r = self.rnd
        cid = len(self.customers) + 1
        first, last = r.choice(FIRST), r.choice(LAST)
        email = f"{first}.{last}{cid}@example.test".lower()
        for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
            email = email.replace(a, b)
        c = {
            "customer_id": cid, "first_name": first, "last_name": last, "email": email,
            "phone": f"+49 30 555 {r.randint(1000, 9999)}", "city": r.choice(CITIES),
            "postcode": f"{r.randint(10000, 99999)}", "birth_year": r.randint(1950, 2007),
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "marketing_opt_in": r.random() < 0.45,
        }
        self.customers.append(c)
        return c

    def _seed_customers(self, n: int):
        base = dt.datetime.combine(self.start, dt.time()) - dt.timedelta(days=730)
        for _ in range(n):
            self._new_customer(base + dt.timedelta(seconds=self.rnd.randint(0, 730 * 86400 - 1)))

    # -- sessions ---------------------------------------------------------------

    def _pick_source(self, day: dt.date) -> str:
        w = list(SOURCE_WEIGHTS)
        if day >= INCIDENT_START:  # a new campaign brings low-intent traffic
            days_in = (day - INCIDENT_START).days
            w[SOURCES.index("tiktok")] = min(18, 7 + 2 * (days_in + 1))
        return self.rnd.choices(SOURCES, w)[0]

    def _platform(self, day: dt.date):
        r = self.rnd
        platform = r.choices(["web", "ios", "android"], [35, 40, 25])[0]
        if platform == "ios":
            if day >= INCIDENT_START:
                share_new = min(0.8, 0.4 + 0.1 * (day - INCIDENT_START).days)
                version = "4.2.0" if r.random() < share_new else r.choice(["4.1.3", "4.1.3", "4.1.2"])
            else:
                version = r.choice(["4.1.3", "4.1.3", "4.1.3", "4.1.2"])
            return platform, version, None
        if platform == "android":
            return platform, r.choice(["3.9.1", "3.9.1", "3.9.0"]), None
        return platform, None, r.choices(["chrome", "safari", "firefox", "edge"], [55, 25, 8, 12])[0]

    def _methods(self, platform: str, browser: str | None) -> tuple[list[str], list[float]]:
        if platform == "ios":
            return ["apple_pay", "card", "paypal", "klarna"], [0.60, 0.15, 0.17, 0.08]
        if platform == "android":
            return ["google_pay", "card", "paypal", "klarna"], [0.25, 0.30, 0.35, 0.10]
        if browser == "safari":
            return ["apple_pay", "card", "paypal", "klarna"], [0.25, 0.25, 0.35, 0.15]
        return ["card", "paypal", "klarna"], [0.40, 0.40, 0.20]

    def _event(self, sid: int, ts: dt.datetime, name: str, **kw) -> dt.datetime:
        self.events.append({"event_id": self.next_event, "session_id": sid,
                            "ts": ts.strftime("%Y-%m-%d %H:%M:%S"), "event_name": name,
                            "product_id": kw.get("product_id"), "payment_method": kw.get("method"),
                            "error_code": kw.get("error")})
        self.next_event += 1
        return ts + dt.timedelta(seconds=self.rnd.randint(2, 60))

    def _attempt_payment(self, sid, ts, method, platform, version, day) -> tuple[bool, dt.datetime, str | None]:
        r = self.rnd
        ts = self._event(sid, ts, "payment_attempt", method=method)
        broken = (platform == "ios" and version == "4.2.0" and method == "apple_pay"
                  and day >= INCIDENT_START)
        if broken and r.random() < 0.85:
            error = "tokenization_timeout"
        elif r.random() < 0.06:
            error = r.choices(["card_declined", "3ds_failed"], [70, 30])[0]
        else:
            return True, ts, None
        ts = self._event(sid, ts, "payment_failed", method=method, error=error)
        return False, ts, error

    def _session(self, sid: int, day: dt.date):
        r = self.rnd
        hour = r.choices(range(24), HOUR_WEIGHTS)[0]
        ts = dt.datetime.combine(day, dt.time(hour, r.randint(0, 59), r.randint(0, 59)))
        platform, version, browser = self._platform(day)
        source = self._pick_source(day)
        customer = r.choice(self.customers[:8000]) if r.random() < 0.55 else None
        session = {"session_id": sid, "customer_id": customer["customer_id"] if customer else None,
                   "started_at": ts.strftime("%Y-%m-%d %H:%M:%S"), "platform": platform,
                   "app_version": version, "browser": browser, "utm_source": source}

        for _ in range(1 + int(r.expovariate(1.2))):
            ts = self._event(sid, ts, "page_view")
        if r.random() < 0.65:
            for _ in range(1 + int(r.expovariate(0.8))):
                ts = self._event(sid, ts, "product_view", product_id=r.choice(self.products)["product_id"])
            if r.random() < 0.10 * SOURCE_CART_FACTOR[source]:
                cart = [r.choice(self.products) for _ in range(r.choice([1, 1, 1, 2, 2, 3]))]
                for p in cart:
                    ts = self._event(sid, ts, "add_to_cart", product_id=p["product_id"])
                if r.random() < 0.55:
                    ts = self._event(sid, ts, "checkout_start")
                    methods, weights = self._methods(platform, browser)
                    method = r.choices(methods, weights)[0]
                    ok, ts, error = self._attempt_payment(sid, ts, method, platform, version, day)
                    if not ok and error == "tokenization_timeout" and customer and r.random() < 0.4:
                        self._ticket(customer, ts + dt.timedelta(hours=r.randint(1, 20)), APPLE_PAY_TICKET)
                    if not ok and r.random() < 0.15:  # some customers retry with another method
                        alt = [m for m in methods if m != method]
                        method = r.choice(alt)
                        ok, ts, _ = self._attempt_payment(sid, ts, method, platform, version, day)
                    if ok:
                        if customer is None:  # guest checkout creates a customer record
                            customer = self._new_customer(ts)
                            session["customer_id"] = customer["customer_id"]
                        ts = self._event(sid, ts, "purchase", method=method)
                        self.orders.append({
                            "order_id": self.next_order, "customer_id": customer["customer_id"],
                            "session_id": sid, "ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
                            "amount_eur": round(sum(p["price_eur"] for p in cart), 2),
                            "payment_method": method, "status": "paid"})
                        self.next_order += 1
        self.sessions.append(session)

    def _ticket(self, customer, ts, template):
        if ts.date() > self.end:
            return
        subject, body = template
        oid = (self.orders[-1]["order_id"] if self.orders else 100_000) - self.rnd.randint(0, 50)
        self.tickets.append({
            "ticket_id": len(self.tickets) + 1, "customer_id": customer["customer_id"],
            "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"), "subject": subject,
            "body": body.format(first=customer["first_name"], last=customer["last_name"],
                                city=customer["city"], cid=customer["customer_id"],
                                email=customer["email"], phone=customer["phone"], oid=oid)})

    def run(self):
        sid = 1
        for i in range(DAYS):
            day = self.start + dt.timedelta(days=i)
            n = int(BASE_SESSIONS * WEEKDAY_FACTOR[day.weekday()] * self.rnd.uniform(0.93, 1.07))
            for _ in range(n):
                self._session(sid, day)
                sid += 1
            for _ in range(self.rnd.randint(8, 16)):  # everyday support noise
                c = self.rnd.choice(self.customers[:8000])
                at = dt.datetime.combine(day, dt.time(self.rnd.randint(8, 18), self.rnd.randint(0, 59)))
                self._ticket(c, at, self.rnd.choice(TICKET_SUBJECTS))


def write(gen: Generator, out: pathlib.Path):
    out.unlink(missing_ok=True)
    con = duckdb.connect(str(out))
    con.execute(SCHEMA)
    tables = {"customers": gen.customers, "products": gen.products, "sessions": gen.sessions,
              "events": gen.events, "orders": gen.orders, "support_tickets": gen.tickets}
    with tempfile.TemporaryDirectory() as tmp:
        for name, rows in tables.items():
            path = pathlib.Path(tmp) / f"{name}.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            con.execute(f"COPY {name} FROM '{path}' (HEADER, NULLSTR '')")
    con.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path(__file__).with_name("warehouse.duckdb"))
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--end", type=dt.date.fromisoformat, default=DEFAULT_END,
                    help="last day with data (default: %(default)s)")
    args = ap.parse_args()

    gen = Generator(args.seed, args.end)
    gen.run()
    write(gen, args.out)
    print(f"wrote {args.out}: {len(gen.customers)} customers, {len(gen.sessions)} sessions, "
          f"{len(gen.events)} events, {len(gen.orders)} orders, {len(gen.tickets)} tickets "
          f"({gen.start} .. {gen.end})")


if __name__ == "__main__":
    main()
