# Discovery: checking vendor deliveries against invoices

**How this discovery was done:** firsthand observation from working at a small, single-location independent store. No formal interviews have been run. Each statement below is marked **Observed** (seen firsthand) or **Assumption** (to be validated). The test data in this repo is synthetic; see `README.md`.

## What's been observed

- **Observed:** Several vendors deliver every week or every other week.
- **Observed:** Every delivery comes with a paper invoice.
- **Observed:** Staff check the invoice against the goods by hand. There is no system or automation for it.
- **Observed:** Mismatches happen in both directions: an item is on the invoice but not in the shipment, or it's in the shipment but not on the invoice.
- **Observed:** The store owner or manager is the one who acts on a mismatch.

## Problem statement

Small independent stores pay vendor invoices without a reliable check that everything billed actually arrived. Items billed but not delivered are money paid for nothing. Items delivered but not billed lead to disputes later. Both throw off stock counts, and for stores that also sell online, the website can show items that aren't on the shelf.

## Job to be done

> When a vendor delivery arrives, I want to know quickly whether what I'm billed for matches what came in, so I only pay for what I received and can raise problems while the vendor will still accept a claim.

## Users

| User | Role in the process | What they need |
|---|---|---|
| Store owner / manager (primary) | Approves payment, raises credits with vendors | A short list of problems with the evidence, and the dollar amount at stake |
| Receiving staff (secondary) | Unloads and counts goods | A check that adds almost no time to unloading |

**Assumption:** receiving staff have a phone on hand and will use it if it's faster than paper.

## Current process

1. **Observed:** Driver drops off the goods with a paper invoice.
2. **Observed:** Staff compare the goods to the invoice by eye.
3. **Assumption:** Problems are noted on the paper invoice, or remembered.
4. **Assumption:** The owner pays the invoice later, often without seeing those notes.
5. **Assumption:** Credits are requested by phone, if at all.

## Assumptions to validate

| Assumption | Why it matters | Cheapest test |
|---|---|---|
| Checking one delivery takes 15–30 minutes | Sets the time-saved baseline | Time the next two deliveries |
| Roughly half of deliveries have at least one mismatch | Decides whether this is worth building | Look back at last month's invoices for notes or credits |
| Most mismatches are found after the driver leaves | Decides whether the check must happen at the door | Ask the owner |
| Some vendors only accept claims within 24–48 hours | Makes speed a requirement, not a nice-to-have | Read the fine print on current invoices |
| The owner will trust a flag that shows the invoice line and the count side by side | Shapes the human-review screen | Show the owner a mockup |

The issue rates in the synthetic data were chosen to give each issue type enough test cases. They are not estimates of real rates.

## What this means for the product

- **The core job is reconciliation.** Catching cost changes on the same invoices is a useful side effect, so it's included as a secondary issue type (`PRICE_CHANGE`).
- **The biggest open design question is how "what arrived" gets recorded.** Today it lives in someone's head, and an agent can't check a count nobody wrote down. Options:
  1. Staff photograph the invoice; the agent turns it into a checklist on their phone; staff tick off or correct counts while unloading.
  2. Staff scan barcodes as they unload.
  3. Staff keep writing on paper and photograph it afterwards.

  Option 1 is the proposed v1. It puts a person in the loop exactly where they already are, and it gives the agent a clean count to compare against.
- **The agent proposes, the owner decides.** The agent flags issues, sizes them in dollars and drafts the credit request. A person approves before anything goes to a vendor.

## Success metrics (targets are hypotheses)

- **Issues caught:** at least 90% of planted issues in the test set, with zero false alarms on clean shipments.
- **Time to check a delivery:** under 5 minutes of staff time.
- **Dollars recovered per month:** credits requested and received.
- **Owner trust:** share of flags the owner accepts without changes.
