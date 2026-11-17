# Synthetic data: invoice vs. shipment reconciliation

Test data for an AI agent that checks vendor invoices against what actually arrived at a small store. **Everything here is fictional**: the store (Maple Street Market), the six vendors, the products, the staff and every number. Nothing comes from a real business.

Each invoice image carries a footer marking it as a synthetic test document.

## What's in it

| | |
|---|---|
| Store catalog | 75 products from 6 vendors |
| Deliveries | 36 shipments over 8 weeks (Sep 21 – Nov 13, 2026), weekly and biweekly |
| Invoices | 36 images: 18 flat scans, 18 phone photos (tilted, shadowed, slightly blurred) |
| Invoice lines | 311 |
| Receiving log | 307 rows, recorded by store staff as goods were counted |
| Planted issues | 37 across 22 shipments; 14 shipments are clean |
| Dollar exposure | $806.09 the store would lose if no issue were caught (out of $18,827.85 invoiced) |

## Folder map

```
synthetic-data/
  README.md                 this file
  discovery.md              problem, users, what's observed vs. assumed
  shipments.csv             one row per delivery; links to the invoice image
  catalog/
    products.csv            the store's product list (what the agent matches against)
    vendors.csv             vendor cadence, units and invoice style
  invoices/                 SHP-###_<vendor>_<scan|photo>.jpg  <- agent input
  receiving/
    receiving_log.csv       what staff counted  <- agent input
  evals/                    answer keys: never give these to the agent
    invoice_extraction_truth.csv   every printed invoice line, correctly read
    receiving_match_truth.csv      which product each receiving row refers to
    answer_key.csv                 every planted discrepancy and the right action
  generator/
    generate.py             rebuilds everything (seeded, so output is identical)
    check_answer_key.py     re-derives every discrepancy from the raw files
```

**The agent's inputs** are the invoice images, `receiving_log.csv`, `products.csv` and `vendors.csv`. Everything in `evals/` is for scoring.

## The issues planted

| Issue | Count | What happened | Expected action |
|---|---|---|---|
| SHORT | 6 | Fewer units arrived than invoiced | Request credit |
| MISSING | 4 | Billed, nothing arrived | Request credit |
| OVER | 3 | More arrived than billed | Call vendor: keep and get invoiced, or return |
| EXTRA | 3 | Arrived, not on the invoice at all | Call vendor |
| SUBSTITUTION | 3 | A different product arrived in place of the billed one | Accept and correct the invoice, or return |
| DAMAGED | 4 | Arrived damaged (dented, crushed, leaking, bruised) | Request credit or replacement |
| PACK_MISMATCH | 3 | Cases held fewer units than the invoice's pack size | Request credit |
| PRICE_CHANGE | 5 | Cost per case or unit changed from the last invoice | Approve new cost, update retail price |
| MATH_ERROR | 3 | Line total ≠ qty × price | Request corrected invoice |
| DUPLICATE_LINE | 3 | Same item billed twice | Request credit |

The first two (SHORT, MISSING) and the next two (OVER, EXTRA) are the problems observed at a real store. The other six are common in grocery receiving and make the eval harder. Issue rates were chosen so each type has at least three examples. **They are not real-world error rates.**

## What makes it hard

- **Vendor wording differs from store wording.** Vendors print "PNT BUTTER CREAMY 16OZ" or "HALDI PWD 200G"; the catalog says "Creamy Peanut Butter 16 oz" and "Turmeric Powder 7 oz".
- **Codes are inconsistent.** Two vendors print their own item codes, one prints UPCs, and two print no codes at all. Three products carry a vendor code on the invoice that isn't mapped in the catalog yet.
- **Units are mixed.** Invoices bill cases (CS) or eaches (EA). Staff record whatever they counted (cases, eaches, or produce cases by the pound). Everything has to be converted to sellable units using `pack`.
- **The receiving log is messy.** Staff write short names ("peanut butter"), scan a UPC on just over half the rows, and list items in a different order than the invoice.
- **Formats vary.** Six layouts, including a handwritten produce ticket and an importer's bill with metric sizes, plus vendor deposits and promo discounts that affect the total.

## Rules the answer key follows

- **Units:** compare in sellable units = quantity × `pack` (cases) or quantity (eaches).
- **PRICE_CHANGE:** flag when the price per order unit differs from the last invoiced price for that product. The first time a product appears, compare with the catalog's `unit_cost × pack`.
- **SUBSTITUTION:** billed product A missing, unbilled product B of the same category and pack size received in its place.
- **dollar_impact:** what the store would overpay if the issue went unnoticed. OVER and EXTRA are 0 because the store isn't overbilled; the value of the unbilled goods is in `explanation`.

## How to use it for evals

Score the agent in three stages, so a failure points to one step:

1. **Read the invoice.** Compare the agent's extracted lines against `invoice_extraction_truth.csv`: % of fields correct (qty, unit price, line total).
2. **Match.** Compare its product matches against `matched_store_sku` (invoice side) and `receiving_match_truth.csv` (receiving side): % matched correctly.
3. **Reconcile.** Compare the issues it raises against `answer_key.csv`: issues caught (recall), false alarms on the 14 clean shipments (precision), and the dollar amount caught.

## Rebuild

```
cd generator
python generate.py ..
python check_answer_key.py ..   # should report no mismatches
```

Needs Python 3 with `reportlab`, `Pillow`, `numpy`, and `pdftoppm` (from poppler).
