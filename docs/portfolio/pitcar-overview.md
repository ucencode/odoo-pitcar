# Pitcar Service Management System

> Portfolio write-up for [ucencode.github.io](https://ucencode.github.io).
> Everything below is drawn from the code in this repository (`pitcar_custom/`,
> Odoo 16, module version `16.0.12`) and its commit history.

---

## One-liner

An Odoo 16 ERP implementation for a car repair workshop, centred on a custom
addon that turns a generic sales order into a **service order** — one record
that carries the car, the mechanic team, the service advisor, the invoice and
the post-service follow-up from the moment the car rolls in.

## Context

Pitcar is a car service business. Like most workshops at that size, the
operational picture was split: which car came in, who worked on it, what parts
left the shelf, what was invoiced, and whether the customer was happy
afterwards all lived in different places. The company wanted one system, and —
just as importantly — one that could be **handed over**. There was no plan to
keep a permanent in-house engineering team, so anything exotic would have been
a liability.

That constraint shaped every technical decision in the addon.

## Problem

- **The car was not a first-class entity.** Odoo models customers, products and
  orders. It does not model *"the 2016 Toyota Avanza with plate B1234XYZ that
  this customer brings in twice a year."* Without that, service history is
  guesswork.
- **Context was re-typed at every step.** The car, odometer reading, assigned
  mechanics and service advisor had to be repeated on the quotation, the parts
  picking, the work order sheet and the invoice — four chances to disagree.
- **Follow-up was invisible.** Whether a customer was called after three days,
  whether they were reminded at the three- and six-month service intervals, and
  whether the reminder actually converted into a booking — none of it was data,
  so none of it could be measured.
- **Reporting could not answer basic questions.** "Which brands do we see most?"
  "Which mechanic team handled this repeat complaint?" "How many cars this
  month?" all required manual counting.

## My role

Backend / Odoo developer. I designed and built the `pitcar_custom` addon and
maintained it in production over roughly eleven months (Nov 2023 – Oct 2024),
authoring 49 of the repository's 61 commits and working with a second engineer
who reviewed and merged the later maintenance PRs. Both of us are listed as
maintainers in the module manifest. The repository here is my archived snapshot
taken at the point of ownership transfer; the live repository moved to the
client's side afterwards.

Practically, that meant: modelling the domain, extending the standard Odoo sale
/ stock / account / project flows in place, building the views and PDF reports
the shop floor actually used, and shipping small, reviewable changes against a
running production system.

## What I built

### 1. A car as a real entity

`res.partner.car` plus its reference models (`brand`, `type`, `transmission`)
and a `res.partner.source` for lead attribution.

- Number plates are the natural key: normalised on input (spaces stripped,
  upper-cased) and guarded by a uniqueness constraint, because the same plate
  arriving twice means the same car, not a new one.
- The display name is a stored computed field (`plate + brand + type`) with a
  **trigram index**, so the front desk can find a car by typing any fragment of
  the plate.
- Year is validated to a real range (1900 … current year) rather than being a
  free-text field that quietly accepts `20166`.
- Selecting a car on an order fills in the customer; selecting a customer
  narrows the car list to that customer's fleet. The domain works both ways so
  the advisor cannot mismatch them.

### 2. Service order = sale order, extended in place

Fifty-six fields were added to `sale.order` rather than building a parallel
service model. Eight car attributes (brand, type, year, transmission, engine
type, engine number, frame number, colour) are **stored related fields** — a
deliberate denormalisation so that orders stay filterable and groupable by car
characteristics without joins, which is what makes the reporting views cheap.

Alongside them: odometer at intake, car arrival time, a many-to-many mechanic
team with a computed flattened `generated_mechanic_team` label for printing, a
many-to-many service advisor link, and a campaign source (Facebook / Instagram /
YouTube / TikTok) for attribution.

### 3. Context that propagates instead of being re-typed

The car block is written once on the order and copied forward by overriding the
hooks Odoo already calls:

| Hook | Target | What moves |
|---|---|---|
| `_action_confirm()` | `stock.picking` | car, odometer, mechanics, advisors, arrival time |
| `_create_invoices()` | `account.move` | the same block, plus quotation date and completion date |
| `_prepare_invoice_values()` | `account.move` (down payment) | car and odometer, via the advance-payment wizard |

`_create_invoices()` also stamps `date_completed = now`, which is the timestamp
the entire follow-up engine hangs off.

Once the order is confirmed, `partner_car_id` becomes read-only in the
`sale` / `done` / `cancel` states, so the car recorded against the work cannot
drift after the work has started.

### 4. A feedback and retention workflow

One billing timestamp expands into three reminder windows — **+3 days**,
**+90 days**, **+180 days** — as stored computed fields, each paired with a
human-readable label field. Three saved search filters ("Reminder 3 Days — Hari
ini", and the 3- and 6-month equivalents) turn those into a daily call list the
service advisor opens directly on the sales list view. No cron job, no queue, no
separate reminder application to keep in sync — which is exactly the kind of
moving part a handed-over system does not want.

The capture around it is a small state machine:

- `is_willing_to_feedback` gates everything; answering *no* records the reason
  and clears the rating, satisfaction and tag fields.
- `customer_rating` (1–5) derives `customer_satisfaction` through a mapping
  applied consistently in `onchange`, `create()` **and** `write()`, so an order
  created through the UI, an import or the ORM all end up with the same derived
  value. Satisfaction is read-only — derived, never typed.
- A rating of 1 or 2 flips `show_complaint_action`, opening a complaint action
  and resolution status, plus tagging via `feedback.classification`.
- The 3- and 6-month reminders each record: was the customer contacted, did they
  respond, what did they say, how is it categorised, and did it convert into a
  booking with a date. Each window gets its own m2m relation table against the
  shared `feedback.classification` model.

### 5. Shop-floor output

A QWeb PDF **Work Order** report bound to `sale.order` (the sheet that goes to
the bay, carrying the car details and the mechanic team), plus a customised
invoice layout that prints the same car block so finance and the customer see
the same record the workshop did.

### 6. Navigation, reporting and access

Fifteen view files: tree, form and kanban views, search filters and group-by
across cars, brands, types, years, mechanics and vendors, plus dedicated Sales
configuration menus for Car Management, Mechanic Teams, Service Advisors,
Customer Tags and Product Tags. Access control is a nine-row
`ir.model.access.csv` scoped to `base.group_user`, with reference data
(transmissions, legacy mechanics) deliberately read-only.

`project.task` was also extended to link tasks to their quotation, pull the
order total, and compute a deadline duration for the kanban board.

## Engineering decisions worth defending

**Extend, don't rebuild.** Every behaviour above is an override of an existing
Odoo hook or an added field on an existing model. There is no parallel service,
no shadow table, no second source of truth. A maintainer with ordinary Odoo
knowledge can read the addon and understand it — which was the actual
requirement, since the system had to survive the handover.

**Denormalise where reads dominate.** Car attributes are stored related fields.
It costs write-time recomputation and buys cheap filtering, grouping and
reporting on the views people open every day. For an operational dashboard that
trade is the right way round.

**Never destroy history.** When the single-mechanic field (`car_mechanic_id`)
was superseded by a many-to-many team (`car_mechanic_id_new`), the old field was
kept as read-only rather than dropped, so orders closed before the change still
show who worked on them. The field names are ugly; the data is intact. That was
the correct call in a live system.

**Index what people search.** Trigram indexes on the plate and the computed car
name, btree indexes on brand and type, a SQL uniqueness constraint on mechanic
team names, and `index=True` on the foreign keys the list views group by.

**Derive, don't duplicate.** Satisfaction from rating, mechanic team label from
the m2m, follow-up dates from the completion timestamp, task total from the
linked order. Anything computable is computed, in one place, and stored when the
views need to sort on it.

## Outcome

- Replaced fragmented operational tooling with a single Odoo instance covering
  sales, service, inventory, invoicing and customer management.
- Made service history queryable: every visit is attached to a specific car,
  with the mechanic team, advisor, odometer and outcome attached to it.
- Turned follow-up into data. Contact rate, response rate and rebooking rate at
  3 days, 3 months and 6 months became ordinary group-by queries on
  `sale.order` instead of an off-system process.
- Supported the business at roughly 400+ service units per month.
- Shipped continuously against production for eleven months in small reviewed
  increments, then handed the system over — running, documented and maintainable
  by an external maintainer — at the point of ownership transfer.

## Stack

`Odoo 16` · `Python 3` · `PostgreSQL` · `XML / QWeb` · custom addon
(`pitcar_custom`, LGPL-3) · Git / GitHub PR review flow

Module dependencies: `base`, `sale`, `sale_management`, `sale_stock`, `stock`,
`account`, `crm`, `purchase`, `project`.

## Timeline

| Period | Focus |
|---|---|
| Nov – Dec 2023 | Car entity, plate normalisation, order/picking/invoice propagation, first filters and group-by |
| Jan – Mar 2024 | Tagging (customer, product, quotation), engine type, invoice and report layout |
| May 2024 | Brand/type CRUD, mechanic teams as a many-to-many with colour coding |
| Jun – Jul 2024 | Completion date, quotation date on reports, required-field tightening |
| Sep 2024 | Service advisors, campaign attribution, project task extensions |
| Sep – Oct 2024 | Feedback capture, 3-day / 3-month / 6-month reminder engine, car arrival time, handover |

## Diagrams

Rendered from [`diagrams/render.py`](diagrams/render.py) (stdlib only —
`python3 docs/portfolio/diagrams/render.py`):

| File | Shows |
|---|---|
| [`01-architecture.svg`](diagrams/01-architecture.svg) | Layers: users → Odoo 16 → `pitcar_custom` → core modules → PostgreSQL |
| [`02-data-model.svg`](diagrams/02-data-model.svg) | New and extended entities, relations, modelling decisions |
| [`03-order-lifecycle.svg`](diagrams/03-order-lifecycle.svg) | Arrival → quotation → confirm → work order → invoice → follow-up, with field propagation |
| [`04-followup-engine.svg`](diagrams/04-followup-engine.svg) | How one timestamp becomes a 3-day / 3-month / 6-month retention workflow |
