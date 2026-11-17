"""
Independent check: re-derive every discrepancy from the raw files (catalog,
invoice extraction truth, receiving log + its match truth) using the written
rules, and compare with evals/answer_key.csv. Does not import generate.py.
Run: python check_answer_key.py ..
"""
import csv, os, sys
from collections import Counter, defaultdict

D = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "..")
rd = lambda p: list(csv.DictReader(open(os.path.join(D, p))))
cat = {r["store_sku"]: r for r in rd("catalog/products.csv")}
ships = rd("shipments.csv")
lines = defaultdict(list)
for r in rd("evals/invoice_extraction_truth.csv"):
    lines[r["shipment_id"]].append(r)
match = {r["row_id"]: r["store_sku"] for r in rd("evals/receiving_match_truth.csv")}
recv = defaultdict(list)
for r in rd("receiving/receiving_log.csv"):
    recv[r["shipment_id"]].append(r)

ref_price = {s: round(float(c["unit_cost"]) * int(c["pack"]), 2) for s, c in cat.items()}
derived, problems = Counter(), []
for s in ships:
    sid = s["shipment_id"]
    L = lines[sid]
    # invoice total adds up?
    sub = round(sum(float(l["line_total_printed"]) for l in L), 2)
    if s["vendor_id"] not in ("V2", "V5") and abs(sub - float(s["invoice_total_printed"])) > 0.005:
        problems.append(f"{sid}: total {s['invoice_total_printed']} != lines {sub}")
    seen = Counter(l["matched_store_sku"] for l in L)
    inv_units = {}
    for sku, n in seen.items():
        if n > 1:
            derived[(sid, "DUPLICATE_LINE", sku)] += 1
    for l in L:
        sku = l["matched_store_sku"]
        q, p = int(l["qty"]), float(l["unit_price"])
        if abs(round(q * p, 2) - float(l["line_total_printed"])) > 0.005:
            derived[(sid, "MATH_ERROR", sku)] += 1
        inv_units[sku] = q * int(cat[sku]["pack"])
    for sku in seen:
        p = float(next(l["unit_price"] for l in L if l["matched_store_sku"] == sku))
        if abs(p - ref_price[sku]) > 0.005:
            derived[(sid, "PRICE_CHANGE", sku)] += 1
        ref_price[sku] = p
    rec_units, notes = Counter(), {}
    for r in recv[sid]:
        sku = match[r["row_id"]]
        mult = int(cat[sku]["pack"]) if r["uom"] == "CS" else 1
        rec_units[sku] += int(r["qty_received"]) * mult
        notes[sku] = r["note"]
        if int(r["qty_damaged"]) > 0:
            derived[(sid, "DAMAGED", sku)] += 1
    for sku in set(inv_units) | set(rec_units):
        i, r = inv_units.get(sku, 0), rec_units.get(sku, 0)
        if i and not r:
            derived[(sid, "MISSING", sku)] += 1
        elif r and not i:
            derived[(sid, "EXTRA", sku)] += 1
        elif r < i:
            derived[(sid, "PACK_MISMATCH" if "cases have" in notes.get(sku, "") else "SHORT", sku)] += 1
        elif r > i:
            derived[(sid, "OVER", sku)] += 1

key = Counter()
for a in rd("evals/answer_key.csv"):
    if a["issue_type"] == "SUBSTITUTION":  # = billed item missing + unbilled item received
        key[(a["shipment_id"], "MISSING", a["store_sku"])] += 1
        key[(a["shipment_id"], "EXTRA", a["related_store_sku"])] += 1
    else:
        key[(a["shipment_id"], a["issue_type"], a["store_sku"])] += 1

only_key, only_derived = key - derived, derived - key
print("answer key rows (substitutions expanded):", sum(key.values()))
print("derived from raw files:", sum(derived.values()))
print("in key but not derived:", dict(only_key) or "none")
print("derived but not in key:", dict(only_derived) or "none")
print("invoice total problems:", problems or "none")
sys.exit(1 if (only_key or only_derived or problems) else 0)
