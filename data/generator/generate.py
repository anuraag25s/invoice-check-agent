"""
Synthetic data generator for the invoice-vs-shipment reconciliation agent.

Everything here is fictional: the store, the vendors, the products, the people.
Run:  python generate.py ../   (writes into the synthetic-data folder)
Seeded, so every run produces the same data.
"""
import csv, json, math, os, random, shutil, subprocess, sys, tempfile
import datetime as dt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "..")
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

STORE = ("Maple Street Market", "214 Maple St.", "Anytown, VA 00000")
STAFF = ["Ravi", "Maria", "Jen"]
START = dt.date(2026, 9, 21)  # Monday, week 0
WEEKS = 8

# ---------------------------------------------------------------- vendors ---
# (id, name, short, cadence, weekday 0=Mon, weeks, order_unit, code_style, layout)
VENDORS = [
    ("V1", "Sunrise Wholesale Grocers", "sunrise", "biweekly", 2, [0, 2, 4, 6], "CS", "vendor_code", "A"),
    ("V2", "Metro Beverage Supply", "metro", "weekly", 1, list(range(8)), "CS", "vendor_code", "B"),
    ("V3", "Greenleaf Produce Co.", "greenleaf", "weekly", 0, list(range(8)), "CS", "none", "C"),
    ("V4", "Lakeside Snack Distributors", "lakeside", "weekly", 3, list(range(8)), "EA", "upc", "D"),
    ("V5", "Harbor Household Supply", "harbor", "biweekly", 4, [1, 3, 5, 7], "CS", "vendor_code", "E"),
    ("V6", "Spice Route Imports", "spiceroute", "biweekly", 2, [1, 3, 5, 7], "CS", "none", "F"),
]
VMAP = {v[0]: v for v in VENDORS}

# (store name, vendor description, pack = sellable units per order unit,
#  cost per sellable unit, sell unit, category)
P = {
 "V1": [
  ("Spaghetti Pasta 16 oz", "PASTA SPAGHETTI 16OZ", 12, 1.05, "ea", "Pasta"),
  ("Penne Pasta 16 oz", "PASTA PENNE RIGATE 16OZ", 12, 1.10, "ea", "Pasta"),
  ("Marinara Sauce 24 oz", "SAUCE MARINARA 24OZ JAR", 12, 2.15, "ea", "Sauce"),
  ("Long Grain White Rice 5 lb", "RICE LG WHITE 5LB", 8, 3.40, "ea", "Rice"),
  ("Black Beans 15.5 oz can", "BEANS BLACK 15.5OZ CAN", 24, 0.72, "ea", "Canned"),
  ("Diced Tomatoes 14.5 oz can", "TOMATO DICED 14.5OZ", 24, 0.78, "ea", "Canned"),
  ("Creamy Peanut Butter 16 oz", "PNT BUTTER CREAMY 16OZ", 12, 2.05, "ea", "Spreads"),
  ("Strawberry Jam 18 oz", "PRESERVES STRAWB 18OZ", 12, 2.30, "ea", "Spreads"),
  ("All-Purpose Flour 5 lb", "FLOUR AP BLEACHED 5LB", 8, 2.20, "ea", "Baking"),
  ("Granulated Sugar 4 lb", "SUGAR GRAN 4LB", 8, 2.60, "ea", "Baking"),
  ("Vegetable Oil 48 oz", "OIL VEG 48OZ", 9, 3.35, "ea", "Oil"),
  ("Chicken Noodle Soup 10.75 oz", "SOUP CHKN NOODLE 10.75OZ", 24, 0.95, "ea", "Canned"),
  ("Old Fashioned Oats 42 oz", "OATS OLD FASHIONED 42OZ", 12, 3.10, "ea", "Cereal"),
  ("Corn Flakes 18 oz", "CEREAL CORN FLAKES 18OZ", 12, 2.45, "ea", "Cereal"),
 ],
 "V2": [
  ("Cola 2 L", "COLA 2LTR", 8, 1.25, "ea", "Soda"),
  ("Diet Cola 2 L", "DIET COLA 2LTR", 8, 1.25, "ea", "Soda"),
  ("Lemon-Lime Soda 2 L", "LEMON LIME 2LTR", 8, 1.20, "ea", "Soda"),
  ("Cola 12-pack cans", "COLA 12/12OZ CAN", 2, 4.60, "ea", "Soda multipack"),
  ("Spring Water 24-pack 16.9 oz", "SPRING WTR 24/.5L", 1, 3.10, "ea", "Water"),
  ("Spring Water 1 gal", "SPRING WTR 1GAL", 6, 0.85, "ea", "Water"),
  ("Orange Juice 52 oz", "OJ NFC 52OZ", 6, 2.90, "ea", "Juice"),
  ("Sports Drink Fruit Punch 28 oz", "SPORTS DRK FRT PNCH 28OZ", 15, 0.95, "ea", "Sports drink"),
  ("Sports Drink Lemon-Lime 28 oz", "SPORTS DRK LMN LIME 28OZ", 15, 0.95, "ea", "Sports drink"),
  ("Iced Tea Lemon 18.5 oz", "ICED TEA LEMON 18.5OZ", 12, 0.88, "ea", "Tea"),
  ("Energy Drink 16 oz can", "ENERGY 16OZ CAN", 24, 1.45, "ea", "Energy"),
  ("Sparkling Water Lime 8-pack", "SPRK WTR LIME 8/12OZ", 3, 3.20, "ea", "Water"),
 ],
 "V3": [
  ("Bananas", "Bananas 40#", 40, 0.46, "lb", "Fruit"),
  ("Red Onions", "Red onion 25#", 25, 0.62, "lb", "Onions"),
  ("Yellow Onions", "Yellow onions 50#", 50, 0.38, "lb", "Onions"),
  ("Russet Potatoes", "Russet 50#", 50, 0.42, "lb", "Potatoes"),
  ("Roma Tomatoes", "Roma tom 25#", 25, 0.95, "lb", "Tomatoes"),
  ("Hass Avocados", "Avocado 48ct", 48, 0.78, "ea", "Fruit"),
  ("Limes", "Limes 110ct", 110, 0.18, "ea", "Citrus"),
  ("Lemons", "Lemons 115ct", 115, 0.25, "ea", "Citrus"),
  ("Cilantro bunch", "Cilantro 30 bu", 30, 0.40, "bunch", "Herbs"),
  ("Green Bell Peppers", "Green pepper 25#", 25, 0.85, "lb", "Peppers"),
  ("Iceberg Lettuce", "Iceberg 24ct", 24, 0.95, "ea", "Greens"),
  ("Gala Apples", "Gala 88ct", 88, 0.48, "ea", "Fruit"),
  ("Carrots 2 lb bag", "Carrots 24/2#", 24, 1.10, "bag", "Roots"),
 ],
 "V4": [
  ("Potato Chips Classic 8 oz", "CHIPS CLASSIC 8OZ", 1, 2.45, "ea", "Chips"),
  ("Potato Chips BBQ 8 oz", "CHIPS BBQ 8OZ", 1, 2.45, "ea", "Chips"),
  ("Potato Chips Sour Cream & Onion 8 oz", "CHIPS SC&O 8OZ", 1, 2.45, "ea", "Chips"),
  ("Tortilla Chips 13 oz", "TORTILLA CHIP REST 13OZ", 1, 2.85, "ea", "Chips"),
  ("Pretzel Twists 16 oz", "PRETZEL TWIST 16OZ", 1, 2.30, "ea", "Pretzels"),
  ("Cheese Puffs 8 oz", "CHEESE PUFF 8OZ", 1, 2.10, "ea", "Puffs"),
  ("Butter Popcorn 6 oz", "POPCORN BUTTER 6OZ", 1, 2.20, "ea", "Popcorn"),
  ("Trail Mix 10 oz", "TRAIL MIX ORIG 10OZ", 1, 3.60, "ea", "Nuts"),
  ("Chocolate Chip Cookies 13 oz", "COOKIE CHOC CHIP 13OZ", 1, 2.75, "ea", "Cookies"),
  ("Sandwich Crackers 8-pack", "CRACKER SNDWCH 8PK", 1, 2.40, "ea", "Crackers"),
  ("Beef Jerky Original 2.85 oz", "JERKY BEEF ORIG 2.85OZ", 1, 3.90, "ea", "Meat snacks"),
  ("Salsa Medium 16 oz", "SALSA MED 16OZ", 1, 2.15, "ea", "Dips"),
 ],
 "V5": [
  ("Paper Towels 6-roll", "PT 6RL MEGA", 4, 7.20, "ea", "Paper"),
  ("Bath Tissue 12-roll", "BT 12RL DBL", 4, 8.40, "ea", "Paper"),
  ("Dish Soap 24 oz", "DISH LIQ ORIG 24OZ", 9, 1.85, "ea", "Cleaning"),
  ("Laundry Detergent 92 oz", "LDRY DET 92OZ 64LD", 4, 9.80, "ea", "Laundry"),
  ("Trash Bags 13 gal 40 ct", "TRASH BAG 13G 40CT", 6, 5.10, "ea", "Bags"),
  ("Aluminum Foil 75 sq ft", "FOIL 75SF", 12, 3.05, "ea", "Wraps"),
  ("Bleach 81 oz", "BLEACH REG 81OZ", 6, 2.75, "ea", "Cleaning"),
  ("All-Purpose Cleaner 32 oz", "APC SPRAY 32OZ", 12, 2.40, "ea", "Cleaning"),
  ("Scrub Sponges 6-pack", "SPONGE SCRUB 6PK", 12, 2.90, "ea", "Cleaning"),
  ("AA Batteries 4-pack", "BATT AA 4PK", 12, 3.40, "ea", "Batteries"),
  ("Hand Soap 7.5 oz pump", "HAND SOAP 7.5OZ PUMP", 12, 1.35, "ea", "Personal care"),
  ("Zip Bags Gallon 30 ct", "ZIP BAG GAL 30CT", 12, 2.60, "ea", "Wraps"),
 ],
 "V6": [
  ("Basmati Rice 10 lb", "BSMT RICE 10LB", 4, 11.50, "ea", "Rice"),
  ("Toor Dal 4 lb", "TOOR DAL 4LB", 10, 5.40, "ea", "Lentils"),
  ("Chana Dal 4 lb", "CHANA DAL 4LB", 10, 4.60, "ea", "Lentils"),
  ("Turmeric Powder 7 oz", "HALDI PWD 200G", 20, 1.40, "ea", "Spices"),
  ("Cumin Seeds 7 oz", "JEERA 200G", 20, 1.90, "ea", "Spices"),
  ("Garam Masala 3.5 oz", "GARAM MSL 100G", 20, 1.75, "ea", "Spices"),
  ("Ghee 32 oz", "GHEE 32OZ", 12, 9.20, "ea", "Dairy"),
  ("Mango Pickle 10 oz", "MANGO PKL 300G", 12, 2.40, "ea", "Condiments"),
  ("Chickpea Flour 4 lb", "BESAN 4LB", 10, 4.10, "ea", "Flour"),
  ("Frozen Paratha 5-pack", "PARATHA FRZ 5PC", 24, 1.95, "ea", "Frozen"),
  ("Coconut Milk 13.5 oz", "COCO MILK 400ML", 24, 0.95, "ea", "Canned"),
  ("Tamarind Paste 8 oz", "IMLI PASTE 227G", 24, 1.30, "ea", "Condiments"),
 ],
}
UNMAPPED = {("V1", 12), ("V1", 13), ("V5", 11)}  # vendor code printed on invoice, missing in catalog


def upc_check(d11):
    s = sum(int(c) for c in d11[0::2]) * 3 + sum(int(c) for c in d11[1::2])
    return d11 + str((10 - s % 10) % 10)


def retail(cost):
    p = cost * random.uniform(1.38, 1.6)
    if p < 3:
        return round(math.ceil(p * 10) / 10 - 0.01, 2)
    return math.floor(p) + 0.99


# ---------------------------------------------------------------- catalog ---
catalog = []  # dicts
sku_n = 1001
for vid, items in P.items():
    for i, (name, vdesc, pack, cost, sunit, cat) in enumerate(items):
        if vid == "V3":
            upc = ""
        else:
            upc = upc_check(f"0{random.randint(10000, 89999)}{random.randint(10000, 99999)}")
        if vid == "V1":
            vcode = f"SW-{random.randint(10000, 19999)}"
        elif vid == "V2":
            vcode = f"MB{random.randint(2000, 2999)}"
        elif vid == "V4":
            vcode = upc
        elif vid == "V5":
            vcode = f"HH-{random.randint(100, 999)}"
        else:
            vcode = ""
        catalog.append(dict(
            store_sku=f"MSM-{sku_n}", product_name=name, category=cat, vendor_id=vid,
            vendor_item_code_on_invoice=vcode,
            vendor_item_code=("" if (vid, i) in UNMAPPED else vcode),
            vendor_description=vdesc, upc=upc,
            order_unit=VMAP[vid][6], pack=pack, sell_unit=sunit,
            unit_cost=cost, retail_price=retail(cost)))
        sku_n += 1
BY_SKU = {c["store_sku"]: c for c in catalog}
BY_VENDOR = {}
for c in catalog:
    BY_VENDOR.setdefault(c["vendor_id"], []).append(c)

# ------------------------------------------------------------- schedule ----
schedule = []
for v in VENDORS:
    vid, _, _, _, wd, weeks = v[:6]
    for w in weeks:
        d = START + dt.timedelta(days=7 * w + wd)
        schedule.append((d, vid))
schedule.sort()

ISSUE_WEIGHTS = {"SHORT": 20, "MISSING": 12, "OVER": 8, "EXTRA": 10, "SUBSTITUTION": 8,
                 "DAMAGED": 10, "PRICE_CHANGE": 14, "MATH_ERROR": 6, "DUPLICATE_LINE": 4,
                 "PACK_MISMATCH": 6}
ACTIONS = {
    "SHORT": "Request credit for units not received",
    "MISSING": "Request credit; item billed but not delivered",
    "OVER": "Call vendor: keep and get invoiced, or return extra units",
    "EXTRA": "Call vendor: item delivered but not billed; confirm, then keep or return",
    "SUBSTITUTION": "Decide: accept substitute (get invoice corrected) or return it and request credit",
    "DAMAGED": "Request credit or replacement for damaged units",
    "PRICE_CHANGE": "Review cost change; approve new cost and update retail price",
    "MATH_ERROR": "Request corrected invoice; line total does not equal qty x price",
    "DUPLICATE_LINE": "Request credit; same item billed twice",
    "PACK_MISMATCH": "Request credit; cases held fewer units than invoiced pack size",
}
DAMAGE_NOTES = {"Canned": "dented cans", "Soda": "crushed case", "Water": "leaking bottles",
                "Fruit": "bruised", "Tomatoes": "crushed/soft", "Greens": "wilted",
                "Chips": "crushed bags", "Paper": "wet packaging", "Cleaning": "leaking",
                "Dairy": "leaking jar", "Spreads": "broken jar", "Sauce": "broken jar"}

# minimum examples per issue type, so every type can be evaluated
BAG = {"SHORT": 6, "MISSING": 4, "OVER": 3, "EXTRA": 3, "SUBSTITUTION": 3, "DAMAGED": 4,
       "PRICE_CHANGE": 5, "MATH_ERROR": 3, "DUPLICATE_LINE": 3, "PACK_MISMATCH": 3}
_bag = [t for t, n in BAG.items() for _ in range(n)]
random.shuffle(_bag)
_issue_ships = sorted(random.sample(range(1, len(schedule) + 1), 20))
DEAL = {}
for i, t in enumerate(_bag):
    DEAL.setdefault(_issue_ships[i % len(_issue_ships)], []).append(t)
CARRY = []
SUB_USED = set()  # keep substitutions varied across categories
last_price = {}  # sku -> last invoiced price per order unit
shipments, inv_truth, receiving, answer_key = [], [], [], []
inv_counter = {"V1": 40211, "V2": 482310, "V3": 1187, "V4": 770412, "V5": 30518, "V6": 214}


def inv_number(vid):
    inv_counter[vid] += random.randint(3, 40)
    n = inv_counter[vid]
    return {"V1": f"SW-2026-{n}", "V2": f"MB {n}", "V3": f"No. {n}", "V4": f"LS-DSD-{n}",
            "V5": f"HHS-INV-{n}", "V6": f"SRI/26/{n}"}[vid]


def order_qty(c):
    if c["order_unit"] == "EA":
        return random.choice([6, 8, 10, 12, 12, 18, 24])
    if c["vendor_id"] == "V3":
        return random.choice([1, 1, 2, 2, 3, 4])
    return random.choice([1, 2, 2, 3, 3, 4, 5])


for s_idx, (ddate, vid) in enumerate(schedule, 1):
    sid = f"SHP-{s_idx:03d}"
    v = VMAP[vid]
    inv_date = ddate - dt.timedelta(days=random.choice([1, 2])) if vid in ("V1", "V5", "V6") else ddate
    invno = inv_number(vid)
    pool = BY_VENDOR[vid]
    k = random.randint(6, min(11, len(pool) - 2))
    chosen = random.sample(pool, k)
    lines = []
    for c in chosen:
        q = order_qty(c)
        price = last_price.get(c["store_sku"], round(c["unit_cost"] * c["pack"], 2))
        lines.append(dict(sku=c["store_sku"], qty=q, price=price, prev_price=price,
                          printed_pack=c["pack"], dup=False, math_delta=0.0))
    received = {l["sku"]: dict(units=l["qty"] * BY_SKU[l["sku"]]["pack"], damaged=0, note="")
                for l in lines}
    issues = []
    used = set()

    todo = CARRY + DEAL.get(s_idx, [])
    CARRY.clear()
    for t in todo:
        applied = False
        for _attempt in range(10):
            free = [i for i in range(len(lines)) if i not in used]
            if t != "EXTRA" and not free:
                break
            li = random.choice(free) if free else None
            L = lines[li] if li is not None else None
            c = BY_SKU[L["sku"]] if L else None
            ok = True
            if t == "SHORT":
                if c["order_unit"] == "EA":
                    if L["qty"] < 2: ok = False
                    else: received[c["store_sku"]]["units"] = L["qty"] - random.randint(1, min(L["qty"] - 1, 6))
                elif L["qty"] >= 2:
                    received[c["store_sku"]]["units"] = (L["qty"] - random.randint(1, L["qty"] - 1)) * c["pack"]
                elif c["pack"] >= 6 and vid != "V3":
                    received[c["store_sku"]]["units"] = L["qty"] * c["pack"] - random.randint(1, min(c["pack"] - 1, 4))
                else:
                    ok = False
            elif t == "MISSING":
                received.pop(c["store_sku"])
            elif t == "OVER":
                received[c["store_sku"]]["units"] += c["pack"] if c["order_unit"] == "CS" else 6
            elif t == "EXTRA":
                cand = [x for x in pool if x["store_sku"] not in received and x["store_sku"] not in [l["sku"] for l in lines]]
                if not cand: ok = False
                else:
                    x = random.choice(cand)
                    received[x["store_sku"]] = dict(units=x["pack"] if x["order_unit"] == "CS" else 6, damaged=0,
                                                    note=random.choice(["", "not sure if we ordered this", ""]))
                    issues.append(dict(type="EXTRA", sku=x["store_sku"], line=None))
                    applied = True
                    break
            elif t == "SUBSTITUTION":
                cand = [x for x in pool if x["category"] == c["category"] and x["pack"] == c["pack"]
                        and x["store_sku"] not in received and x["store_sku"] not in [l["sku"] for l in lines]]
                if c["category"] in SUB_USED: cand = []
                if not cand: ok = False
                else:
                    x = random.choice(cand)
                    SUB_USED.add(c["category"])
                    r = received.pop(c["store_sku"])
                    received[x["store_sku"]] = dict(units=r["units"], damaged=0, note="")
                    issues.append(dict(type="SUBSTITUTION", sku=c["store_sku"], sub=x["store_sku"], line=li))
                    used.add(li)
                    applied = True
                    break
            elif t == "DAMAGED":
                r = received[c["store_sku"]]
                r["damaged"] = random.randint(1, min(3, r["units"]))
                r["note"] = DAMAGE_NOTES.get(c["category"], "damaged packaging")
            elif t == "PACK_MISMATCH":
                if vid in ("V1", "V2", "V5", "V6") and c["pack"] >= 8:
                    actual = c["pack"] - (2 if c["pack"] < 12 else random.choice([2, 4]))
                    received[c["store_sku"]]["units"] = L["qty"] * actual
                    received[c["store_sku"]]["note"] = f"cases have {actual} each, not {c['pack']}"
                    received[c["store_sku"]]["force_ea"] = True
                else:
                    ok = False
            elif t == "PRICE_CHANGE":
                f = random.choice([1.04, 1.06, 1.08, 1.10, 1.12, 0.94])
                L["price"] = round(L["price"] * f, 2)
            elif t == "MATH_ERROR":
                L["math_delta"] = random.choice([L["price"], 9.00, 10.00])
            elif t == "DUPLICATE_LINE":
                L["dup"] = True
            if ok:
                applied = True
                issues.append(dict(type=t, sku=c["store_sku"], line=li))
                used.add(li)
                break
        if not applied:
            CARRY.append(t)

    # printed invoice lines (duplicates inserted)
    printed = []
    for L in lines:
        L["ext_correct"] = round(L["qty"] * L["price"], 2)
        L["ext_printed"] = round(L["ext_correct"] + L["math_delta"], 2)
        printed.append(L)
    for L in list(lines):
        if L["dup"]:
            printed.insert(random.randint(0, len(printed)), dict(L))
    subtotal = round(sum(l["ext_printed"] for l in printed), 2)
    extra_line = None
    if vid == "V2":
        containers = 0
        for l in printed:
            c = BY_SKU[l["sku"]]
            per = 12 if "12-pack" in c["product_name"] else 24 if "24-pack" in c["product_name"] else 8 if "8-pack" in c["product_name"] else 1
            containers += l["qty"] * c["pack"] * per
        extra_line = ("DEPOSIT", f"{containers} containers @ $0.05", round(containers * 0.05, 2))
    if vid == "V5" and subtotal > 250:
        extra_line = ("DISCOUNT", "Promo discount 5%", -round(subtotal * 0.05, 2))
    total = round(subtotal + (extra_line[2] if extra_line else 0), 2)

    for i, l in enumerate(printed, 1):
        c = BY_SKU[l["sku"]]
        inv_truth.append(dict(
            shipment_id=sid, invoice_number=invno, line_no=i,
            vendor_item_code_printed=c["vendor_item_code_on_invoice"],
            description_printed=c["vendor_description"], pack_printed=l["printed_pack"],
            qty=l["qty"], uom=c["order_unit"], unit_price=f"{l['price']:.2f}",
            line_total_printed=f"{l['ext_printed']:.2f}", line_total_correct=f"{l['ext_correct']:.2f}",
            matched_store_sku=c["store_sku"]))

    # answer key rows
    for iss in issues:
        t, sku = iss["type"], iss["sku"]
        c = BY_SKU[sku]
        L = lines[iss["line"]] if iss["line"] is not None else None
        cost_unit = round((L["price"] if L else last_price.get(sku, c["unit_cost"] * c["pack"])) / c["pack"], 4)
        inv_units = L["qty"] * c["pack"] if L else 0
        rec = received.get(sku, {"units": 0, "damaged": 0})
        rec_units = rec["units"]
        impact, related, expl = 0.0, "", ""
        if t in ("SHORT", "MISSING", "PACK_MISMATCH"):
            impact = (inv_units - rec_units) * cost_unit
            expl = f"Invoiced {inv_units} {c['sell_unit']}, received {rec_units}."
        elif t == "OVER":
            expl = f"Invoiced {inv_units}, received {rec_units}; {rec_units - inv_units} units not billed (worth ${(rec_units - inv_units) * cost_unit:.2f})."
        elif t == "EXTRA":
            expl = f"Received {rec_units} {c['sell_unit']} not on the invoice (worth ${rec_units * cost_unit:.2f})."
        elif t == "SUBSTITUTION":
            x = BY_SKU[iss["sub"]]
            related = x["store_sku"]
            rec_units = received[x["store_sku"]]["units"]
            impact = inv_units * cost_unit - rec_units * x["unit_cost"]
            expl = f"Invoiced {c['product_name']}, received {x['product_name']} instead ({rec_units} units)."
        elif t == "DAMAGED":
            impact = rec["damaged"] * cost_unit
            expl = f"{rec['damaged']} of {rec_units} units damaged ({rec['note']})."
        elif t == "PRICE_CHANGE":
            impact = (L["price"] - L["prev_price"]) * L["qty"]
            expl = f"Price per {c['order_unit']} went from ${L['prev_price']:.2f} to ${L['price']:.2f} ({(L['price'] / L['prev_price'] - 1) * 100:+.1f}%)."
        elif t == "MATH_ERROR":
            impact = L["ext_printed"] - L["ext_correct"]
            expl = f"Line printed ${L['ext_printed']:.2f}; {L['qty']} x ${L['price']:.2f} = ${L['ext_correct']:.2f}."
        elif t == "DUPLICATE_LINE":
            impact = L["ext_printed"]
            expl = f"Line for {c['vendor_description']} appears twice; received once."
        answer_key.append(dict(
            shipment_id=sid, invoice_number=invno, vendor=v[1], issue_type=t,
            store_sku=sku, product_name=c["product_name"], related_store_sku=related,
            invoiced_units=inv_units, received_units=rec_units, damaged_units=rec.get("damaged", 0),
            dollar_impact=f"{impact:.2f}", expected_action=ACTIONS[t], explanation=expl))

    # receiving log
    staff = random.choice(STAFF)
    items = list(received.items())
    random.shuffle(items)
    for sku, r in items:
        c = BY_SKU[sku]
        units = r["units"]
        if c["order_unit"] == "CS" and c["pack"] > 1 and units % c["pack"] == 0 and not r.get("force_ea") and (random.random() < 0.8 or vid == "V3"):
            q, u = units // c["pack"], "CS"
        else:
            q, u = units, c["sell_unit"].upper()
        words = [w for w in c["product_name"].replace("-", " ").split() if not any(ch.isdigit() for ch in w) and w not in ("oz", "lb", "L", "gal", "ct", "pack", "can", "cans", "bag", "sq", "ft", "pump", "bunch")]
        short = " ".join(words[: random.choice([2, 2, 3])]).lower()
        receiving.append(dict(
            row_id=f"R{len(receiving) + 1:04d}", _sku=sku,
            shipment_id=sid, received_date=ddate.isoformat(), received_by=staff,
            upc_scanned=(c["upc"] if c["upc"] and random.random() < 0.7 else ""),
            item_as_written=short, qty_received=q, uom=u,
            qty_damaged=r["damaged"], note=r["note"]))

    for L in lines:
        last_price[L["sku"]] = L["price"]

    shipments.append(dict(
        shipment_id=sid, vendor_id=vid, vendor=v[1], invoice_number=invno,
        invoice_date=inv_date.isoformat(), received_date=ddate.isoformat(),
        invoice_file="", invoice_total_printed=f"{total:.2f}",
        n_invoice_lines=len(printed), n_issues=len(issues),
        _render=dict(lines=printed, subtotal=subtotal, extra=extra_line, total=total, inv_date=inv_date)))

# ---------------------------------------------------------------- render ----
W, H = letter
FOOT = "Synthetic test document - fictional vendor and store. Not a real invoice."


def money(x): return f"{x:,.2f}"


def draw_table(cv, x0, y, cols, rows, font, size, lh, grid=True, jitter=0.0):
    # cols: list of (header, width, align)
    cv.setFont(font + ("-Bold" if font in ("Helvetica", "Courier") else ""), size)
    x = x0
    for h, w, a in cols:
        cv.drawString(x + 3, y, h) if a == "l" else cv.drawRightString(x + w - 3, y, h)
        x += w
    tw = sum(w for _, w, _ in cols)
    if grid: cv.line(x0, y - 4, x0 + tw, y - 4)
    y -= lh
    cv.setFont(font, size)
    for row in rows:
        x = x0
        for (h, w, a), val in zip(cols, row):
            dx, dy = (random.uniform(-jitter, jitter), random.uniform(-jitter, jitter)) if jitter else (0, 0)
            if a == "l": cv.drawString(x + 3 + dx, y + dy, str(val))
            else: cv.drawRightString(x + w - 3 + dx, y + dy, str(val))
            x += w
        if grid:
            cv.setStrokeGray(0.75); cv.line(x0, y - 4, x0 + tw, y - 4); cv.setStrokeGray(0)
        y -= lh
    return y


def render(pdf_path, s):
    vid = s["vendor_id"]; v = VMAP[vid]; R = s["_render"]; lines = R["lines"]
    cv = canvas.Canvas(pdf_path, pagesize=letter)
    lay = v[8]
    def cat(l): return BY_SKU[l["sku"]]
    if lay == "A":
        cv.setFont("Helvetica-Bold", 17); cv.drawString(40, H - 55, v[1].upper())
        cv.setFont("Helvetica", 8.5); cv.drawString(40, H - 68, "1800 Commerce Pkwy, Unit 4  |  Ph (555) 201-7700  |  ar@sunrise-wholesale.example")
        cv.setFont("Helvetica-Bold", 20); cv.drawRightString(W - 40, H - 58, "INVOICE")
        cv.setFont("Helvetica", 9)
        for i, (k, val) in enumerate([("Invoice #", s["invoice_number"]), ("Date", R["inv_date"].strftime("%m/%d/%Y")),
                                      ("PO #", f"MSM-{random.randint(100, 999)}"), ("Terms", "Net 15")]):
            cv.drawString(W - 210, H - 85 - 13 * i, k); cv.drawRightString(W - 40, H - 85 - 13 * i, val)
        cv.setFont("Helvetica-Bold", 9); cv.drawString(40, H - 100, "BILL TO / SHIP TO")
        cv.setFont("Helvetica", 9)
        for i, t in enumerate(STORE): cv.drawString(40, H - 113 - 12 * i, t)
        cols = [("ITEM #", 70, "l"), ("DESCRIPTION", 200, "l"), ("PACK", 50, "r"), ("QTY", 40, "r"), ("UOM", 40, "l"), ("PRICE", 60, "r"), ("AMOUNT", 72, "r")]
        rows = [(cat(l)["vendor_item_code_on_invoice"], cat(l)["vendor_description"], f"{l['printed_pack']}/CS", l["qty"], "CS", money(l["price"]), money(l["ext_printed"])) for l in lines]
        y = draw_table(cv, 40, H - 175, cols, rows, "Helvetica", 9, 17)
        cv.setFont("Helvetica-Bold", 10)
        cv.drawString(W - 210, y - 10, "SUBTOTAL"); cv.drawRightString(W - 40, y - 10, money(R["subtotal"]))
        cv.drawString(W - 210, y - 26, "TOTAL DUE"); cv.drawRightString(W - 40, y - 26, "$" + money(R["total"]))
        cv.setFont("Helvetica", 8); cv.drawString(40, y - 60, "Shortages must be reported within 48 hours of delivery. Thank you for your business.")
    elif lay == "B":
        cv.setFont("Courier-Bold", 14); cv.drawString(40, H - 50, "METRO BEVERAGE SUPPLY")
        cv.setFont("Courier", 9); cv.drawString(40, H - 63, "ROUTE 7 DELIVERY INVOICE   - DRIVER COPY / CUSTOMER COPY -")
        cv.drawString(40, H - 82, f"INV: {s['invoice_number']}   DATE: {R['inv_date'].strftime('%m/%d/%y')}   ACCT: 10-4471")
        cv.drawString(40, H - 95, f"CUST: {STORE[0].upper()}  {STORE[1].upper()}")
        cols = [("CODE", 60, "l"), ("QTY", 35, "r"), ("DESCRIPTION", 210, "l"), ("SIZE", 55, "l"), ("CS PRICE", 70, "r"), ("EXT", 70, "r")]
        rows = [(cat(l)["vendor_item_code_on_invoice"], l["qty"], cat(l)["vendor_description"], f"{l['printed_pack']}/CS", money(l["price"]), money(l["ext_printed"])) for l in lines]
        y = draw_table(cv, 40, H - 125, cols, rows, "Courier", 9, 15, grid=False)
        cv.setFont("Courier", 9)
        cv.drawString(40, y - 5, "-" * 85)
        cv.drawString(250, y - 20, "PRODUCT TOTAL"); cv.drawRightString(540, y - 20, money(R["subtotal"]))
        cv.drawString(250, y - 34, f"DEPOSIT {R['extra'][1]}"); cv.drawRightString(540, y - 34, money(R["extra"][2]))
        cv.setFont("Courier-Bold", 10); cv.drawString(250, y - 50, "AMOUNT DUE"); cv.drawRightString(540, y - 50, money(R["total"]))
        cv.setFont("Courier", 9); cv.drawString(40, y - 90, "DRIVER SIG ______________   RECEIVED BY ______________   CASES CHECKED [ ]")
    elif lay in ("C", "F"):
        hand = "Helvetica-Oblique"
        if lay == "C":
            cv.setFont("Times-Bold", 18); cv.drawCentredString(W / 2, H - 50, "Greenleaf Produce Co.")
            cv.setFont("Times-Roman", 9); cv.drawCentredString(W / 2, H - 63, "Fresh fruit & vegetables  -  Farmers Mkt Bldg C  -  (555) 640-2290")
            cv.setFont("Times-Roman", 11); cv.drawString(40, H - 92, "DELIVERY TICKET"); cv.drawRightString(W - 40, H - 92, s["invoice_number"])
            cv.drawString(40, H - 110, "Sold to: ____________________________   Date: ______________")
            cv.setFont(hand, 12); cv.drawString(95, H - 108, STORE[0]); cv.drawString(298, H - 108, R["inv_date"].strftime("%-m/%-d"))
            cols = [("Qty", 50, "r"), ("Item", 250, "l"), ("Price", 90, "r"), ("Amount", 100, "r")]
            rows = [(l["qty"], cat(l)["vendor_description"], money(l["price"]), money(l["ext_printed"])) for l in lines]
        else:
            cv.setFont("Courier-Bold", 15); cv.drawString(40, H - 50, "SPICE ROUTE IMPORTS LLC")
            cv.setFont("Courier", 8.5); cv.drawString(40, H - 62, "Importers & Distributors of Indian Groceries  |  Whse 12, Industrial Rd")
            cv.setFont("Courier-Bold", 12); cv.drawRightString(W - 40, H - 50, "TAX INVOICE")
            cv.setFont("Courier", 9.5)
            cv.drawString(40, H - 88, f"Bill No: {s['invoice_number']}"); cv.drawString(300, H - 88, f"Dated: {R['inv_date'].strftime('%d-%m-%Y')}")
            cv.drawString(40, H - 101, f"M/s {STORE[0]}, {STORE[1]}")
            cols = [("S.No", 40, "r"), ("Particulars", 230, "l"), ("Qty", 45, "r"), ("Rate", 80, "r"), ("Amount", 95, "r")]
            rows = [(i, f"{cat(l)['vendor_description']} x{l['printed_pack']}", f"{l['qty']} cs", money(l["price"]), money(l["ext_printed"])) for i, l in enumerate(lines, 1)]
        y = draw_table(cv, 40, H - 145, cols, rows, hand if lay == "C" else "Courier", 11 if lay == "C" else 9.5, 20 if lay == "C" else 16, grid=True, jitter=1.5 if lay == "C" else 0)
        cv.setFont(hand if lay == "C" else "Courier-Bold", 13 if lay == "C" else 10)
        cv.drawString(330, y - 15, "Total"); cv.drawRightString(530, y - 15, "$" + money(R["total"]))
        if lay == "C":
            cv.ellipse(440, y - 25, 540, y + 3)
            cv.setFont("Times-Roman", 9); cv.drawString(40, y - 60, "Claims for shortage or quality must be made at time of delivery.")
        else:
            cv.setFont("Courier", 8.5); cv.drawString(40, y - 50, "Goods once sold will not be taken back. E.&O.E.  Payment due within 30 days.")
    elif lay == "D":
        cv.setFont("Times-Bold", 16); cv.drawString(40, H - 52, "Lakeside Snack Distributors")
        cv.setFont("Times-Roman", 10); cv.drawString(40, H - 66, "Direct Store Delivery  -  Rep: T. Okafor  -  Route 22")
        cv.setFont("Times-Bold", 12); cv.drawRightString(W - 40, H - 52, "DSD INVOICE")
        cv.setFont("Times-Roman", 10)
        cv.drawRightString(W - 40, H - 68, s["invoice_number"]); cv.drawRightString(W - 40, H - 81, R["inv_date"].strftime("%B %d, %Y"))
        cv.drawString(40, H - 95, f"Store: {STORE[0]} - {STORE[1]}")
        cols = [("UPC", 95, "l"), ("Description", 210, "l"), ("Units", 50, "r"), ("Unit Cost", 70, "r"), ("Extended", 80, "r")]
        rows = [(cat(l)["upc"], cat(l)["vendor_description"], l["qty"], money(l["price"]), money(l["ext_printed"])) for l in lines]
        y = draw_table(cv, 40, H - 130, cols, rows, "Times-Roman", 10, 17)
        cv.setFont("Times-Bold", 11); cv.drawString(330, y - 12, "Invoice Total"); cv.drawRightString(545, y - 12, "$" + money(R["total"]))
        cv.setFont("Times-Italic", 9); cv.drawString(40, y - 45, "Stales and credits will appear on next invoice.")
    elif lay == "E":
        cv.setFillGray(0.92); cv.rect(0, H - 80, W, 80, fill=1, stroke=0); cv.setFillGray(0)
        cv.setFont("Helvetica-Bold", 16); cv.drawString(40, H - 45, "Harbor Household Supply")
        cv.setFont("Helvetica", 9); cv.drawString(40, H - 60, "Cleaning  -  Paper  -  Household essentials")
        cv.setFont("Helvetica", 9)
        cv.drawRightString(W - 40, H - 40, f"Invoice {s['invoice_number']}"); cv.drawRightString(W - 40, H - 53, f"Issued {R['inv_date'].isoformat()}")
        cv.drawRightString(W - 40, H - 66, "Due on receipt + 20 days")
        cv.drawString(40, H - 100, f"Customer: {STORE[0]}, {STORE[1]}, {STORE[2]}")
        cols = [("Description", 190, "l"), ("Cases", 45, "r"), ("Case Price", 70, "r"), ("Units/Case", 65, "r"), ("Item #", 60, "l"), ("Line Total", 80, "r")]
        rows = [(cat(l)["vendor_description"], l["qty"], money(l["price"]), l["printed_pack"], cat(l)["vendor_item_code_on_invoice"], money(l["ext_printed"])) for l in lines]
        y = draw_table(cv, 40, H - 135, cols, rows, "Helvetica", 9, 17)
        cv.setFont("Helvetica", 10)
        cv.drawString(330, y - 10, "Subtotal"); cv.drawRightString(550, y - 10, money(R["subtotal"]))
        yy = y - 25
        if R["extra"]:
            cv.drawString(330, yy, R["extra"][1]); cv.drawRightString(550, yy, money(R["extra"][2])); yy -= 15
        cv.setFont("Helvetica-Bold", 11); cv.drawString(330, yy, "Total"); cv.drawRightString(550, yy, "$" + money(R["total"]))
    cv.setFont("Helvetica", 6); cv.setFillGray(0.45); cv.drawCentredString(W / 2, 22, FOOT)
    cv.save()


def degrade(png, out_jpg, photo):
    im = Image.open(png).convert("RGB")
    if not photo:
        im = im.convert("L").rotate(random.uniform(-0.8, 0.8), expand=True, fillcolor=255)
        arr = np.array(im).astype(np.int16)
        arr += np.random.normal(0, 9, arr.shape).astype(np.int16)
        speck = np.random.random(arr.shape) < 0.0008
        arr[speck] = 60
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.4))
        im.save(out_jpg, quality=72)
        return
    w, h = im.size
    j = lambda: random.uniform(0.0, 0.015)
    quad = (w * j(), h * j(), w * j(), h * (1 - j()), w * (1 - j()), h * (1 - j()), w * (1 - j()), h * j())
    im = im.transform((w, h), Image.QUAD, data=quad, fillcolor=(250, 250, 248))
    im = im.rotate(random.uniform(-0.9, 0.9), expand=True, fillcolor=(95, 80, 62))
    bg = Image.new("RGB", (im.width + 120, im.height + 120), random.choice([(92, 76, 58), (120, 120, 118), (70, 72, 78)]))
    bg.paste(im, (60 + random.randint(-20, 20), 60 + random.randint(-20, 20)))
    im = bg
    arr = np.array(im).astype(np.float32)
    gx = np.linspace(random.uniform(0.62, 0.8), 1.0, im.width)[None, :, None]
    gy = np.linspace(1.0, random.uniform(0.8, 0.95), im.height)[:, None, None]
    arr *= gx * gy
    arr[..., 0] *= 1.04; arr[..., 2] *= 0.93
    arr += np.random.normal(0, 5, arr.shape)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    im = ImageEnhance.Contrast(im).enhance(0.9)
    im.thumbnail((1150, 1500))
    im.save(out_jpg, quality=58)


inv_dir = os.path.join(OUT, "invoices"); os.makedirs(inv_dir, exist_ok=True)
tmp = tempfile.mkdtemp()
for s in shipments:
    v = VMAP[s["vendor_id"]]
    pdf = os.path.join(tmp, s["shipment_id"] + ".pdf")
    render(pdf, s)
    subprocess.run(["pdftoppm", "-r", "120", "-png", "-singlefile", pdf, pdf[:-4]], check=True)
    photo = v[8] in ("C", "F") or random.random() < 0.35
    name = f"{s['shipment_id']}_{v[2]}_{'photo' if photo else 'scan'}.jpg"
    degrade(pdf[:-4] + ".png", os.path.join(inv_dir, name), photo)
    s["invoice_file"] = "invoices/" + name
shutil.rmtree(tmp)


# ----------------------------------------------------------------- write ----
def write(path, rows, fields=None):
    path = os.path.join(OUT, path); os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = fields or [k for k in rows[0] if not k.startswith("_")]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


write("catalog/products.csv", catalog, ["store_sku", "product_name", "category", "vendor_id", "vendor_item_code", "upc",
                                         "order_unit", "pack", "sell_unit", "unit_cost", "retail_price"])
write("catalog/vendors.csv", [dict(vendor_id=v[0], vendor=v[1], delivery_cadence=v[3],
                                   delivery_day=["Mon", "Tue", "Wed", "Thu", "Fri"][v[4]], order_unit=v[6],
                                   item_codes_on_invoice=v[7], invoice_style={"A": "printed, item codes", "B": "route ticket, deposits",
                                   "C": "handwritten ticket, no codes", "D": "DSD, UPC codes", "E": "printed, columns in unusual order, promo discount",
                                   "F": "importer bill, abbreviations and metric sizes, no codes"}[v[8]]) for v in VENDORS])
write("shipments.csv", shipments)
write("receiving/receiving_log.csv", receiving)
write("evals/answer_key.csv", answer_key)
write("evals/invoice_extraction_truth.csv", inv_truth)
write("evals/receiving_match_truth.csv", [dict(row_id=r["row_id"], shipment_id=r["shipment_id"], store_sku=r["_sku"]) for r in receiving])
print("unplaced issues:", CARRY)
print(json.dumps(dict(products=len(catalog), shipments=len(shipments), invoice_lines=len(inv_truth),
                      receiving_rows=len(receiving), issues=len(answer_key)), indent=1))
