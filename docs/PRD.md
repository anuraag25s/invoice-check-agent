# PRD: Invoice Check Agent

**Author:** Anuraag · **Status:** Draft v1 · **Last updated:** Nov 17, 2026

## 1. Summary

An AI agent that checks each vendor delivery against its invoice at a small independent store. Staff photograph the paper invoice. The agent turns it into a checklist that staff confirm while unloading, compares what was billed with what arrived, and flags every mismatch with its dollar impact. It then drafts a credit request. **The owner approves every action before anything reaches a vendor.**

## 2. Problem

Small stores receive weekly or biweekly deliveries from many vendors. Each comes with a paper invoice in the vendor's own format. Staff check them by eye, with no system behind it. Items get billed but never arrive, or arrive without being billed. Mismatches are noticed late or not at all, so the store pays for goods it never received and misses the vendor's claim window.

Evidence: firsthand observation at a mom-and-pop store (see `data/discovery.md`). Size and frequency are assumptions to validate.

## 3. Users and job to be done

| User | Need |
|---|---|
| **Owner / manager** (primary, decision-maker) | A short list of real problems, the evidence for each, and the dollars at stake, so they can act in minutes |
| **Receiving staff** (secondary) | A check that adds almost no time to unloading |

**Job to be done:** When a vendor delivery arrives, I want to know quickly whether what I'm billed for matches what came in, so I only pay for what I received and can raise problems while the vendor still accepts claims.

## 4. Goals and non-goals

**Goals (v1)**
- Catch billing and delivery mismatches on every delivery.
- Put a dollar value on each issue and suggest the action.
- Keep a person in control of every decision that costs money.
- Get better at each vendor over time, using people's corrections.

**Non-goals (v1)**
- Paying invoices or connecting to accounting software.
- Updating prices in Shopify or the point-of-sale system. Price changes are flagged for approval only.
- Low-stock alerts. Shopify Flow already does this natively, so it is not rebuilt here.
- Sending anything to vendors automatically.

## 5. User flow

1. **Capture:** staff photograph the invoice when the driver arrives.
2. **Checklist:** the agent reads the invoice and shows a checklist on the phone: each line with the expected count, in sellable units.
3. **Confirm:** staff tick each line while unloading, or correct the count, mark damage, or add an item that isn't on the list.
4. **Review:** the owner sees the flagged issues, each with the invoice line, the counted quantity, the dollar impact and a suggested action. They approve, edit or reject each one.
5. **Act:** approved issues become a drafted credit request email. Approved price changes are queued for a catalog update.
6. **Learn:** every correction a person makes (a product match, a count, a rejected flag) is saved and used on the next delivery.

## 6. How the agent works

| Stage | What it does | AI or rules? |
|---|---|---|
| 1. Read | Invoice photo → vendor, invoice number, lines (code, description, pack, qty, unit price, line total) | AI (vision model) |
| 2. Match | Each line → a store product, checking in order: vendor memory, item code, barcode, then the model choosing from the top 5 candidates with a confidence score | Lookups first, AI only for unclear lines |
| 3. Check | Compare billed and received sellable units; check line math, duplicates and price changes | Rules (plain code) |
| 4. Explain | Draft the owner summary and the credit request | AI |

The arithmetic and the rules stay in plain code, so the same input always gives the same flags and every flag can be traced. AI is used only where judgment is needed: reading messy documents, matching unclear lines and writing summaries.

**Issue types detected:** SHORT, MISSING, OVER, EXTRA, SUBSTITUTION, DAMAGED, PACK_MISMATCH, PRICE_CHANGE, MATH_ERROR, DUPLICATE_LINE. Definitions are in `data/README.md`.

## 7. Human-in-the-loop design

**Gates: where the agent stops and asks**

| Gate | Triggered when | Who decides |
|---|---|---|
| G1: Invoice needs a look | Lines don't add up to the invoice total, or the image can't be read | Owner |
| G2: Confirm a product match | Match confidence is below the threshold (starting at 0.85, to be tuned on the eval set) | Staff or owner |
| G3: Approve an action | Any issue that leads to a credit request, a return or a price change | Owner |

**Autonomy levels: the agent earns independence with evidence**

| Level | What the agent does alone | Unlocks when |
|---|---|---|
| 0: Suggest | Nothing; every issue is reviewed | Launch |
| 1: Auto-match | Matches already confirmed in vendor memory | Match accuracy ≥ 95% on the eval set |
| 2: Auto-approve small | Price changes under 3% on known items | 4 weeks of approvals with no reversals |
| 3: Exceptions only | Everything except gates G1–G3 | Owner opts in, based on pilot data |

## 8. Requirements

| # | Requirement | Priority |
|---|---|---|
| R1 | Read invoice photos and scans across all 6 vendor layouts | P0 |
| R2 | Convert cases and eaches to sellable units using pack size | P0 |
| R3 | Match lines to products; send low-confidence matches to a person | P0 |
| R4 | Detect all 10 issue types, each with a dollar impact and a suggested action | P0 |
| R5 | Mobile checklist for staff to confirm counts | P0 |
| R6 | Owner review screen: approve, edit or reject each issue, with evidence side by side | P0 |
| R7 | Save every human correction to vendor memory and use it first | P0 |
| R8 | Draft a credit request email from the approved issues | P1 |
| R9 | Audit log of every flag, decision and who made it | P1 |
| R10 | Vendor scorecard: issues and dollars by vendor over time | P2 |

## 9. Success metrics

**Launch bar (on the synthetic eval set, scored per stage)**

| Stage | Metric | Target |
|---|---|---|
| Read | Fields read correctly (qty, unit price, line total) | ≥ 95% |
| Match | Lines matched to the correct product | ≥ 90% (≥ 95% on a second pass with memory) |
| Check | Planted issues caught (37 in total) | ≥ 90% |
| Check | False alarms on the 14 clean deliveries | 0 |
| Check | Dollars caught (out of $806.09 planted) | ≥ 95% |

**Pilot metrics (real use)**
- Staff time per delivery: under 5 minutes.
- Share of flags the owner accepts without changes.
- Credits requested and received per month.
- Share of lines handled without a person, tracked week over week.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A misread invoice line creates a false flag | Show the image crop next to each flag; the owner approves every action |
| A wrong product match hides a real issue | Confidence threshold, gate G2, and the match evaluated as its own stage |
| Staff skip the checklist when they're busy | One tap per line, with "all good" as the default; measure completion rate |
| The synthetic data doesn't reflect real invoices | Validate with real deliveries during the pilot; label all results as synthetic |
| Over-trust as autonomy grows | Each autonomy level needs evidence to unlock and can be rolled back |

## 11. Open questions

- How are mismatches handled today, and how often are credits actually recovered?
- What are vendors' real claim windows?
- Will staff use a phone during unloading, or is paper plus a photo afterwards more realistic?

## 12. Milestones

| Milestone | Output |
|---|---|
| M1: Feasibility test | 5 invoices read by hand in Claude; finding in `docs/decisions.md` |
| M2: Read | Extraction script + score |
| M3: Match | Matching + vendor memory + score, before and after memory |
| M4: Check | Rules engine + recall, false alarms, dollars caught |
| M5: Review app | Streamlit checklist, review and credit-request screens |
| M6: Improve | 2–3 scored iterations in `eval/results/results_log.md` |
| M7: Publish | README, demo video, write-up |
