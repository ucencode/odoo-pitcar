# Pitcar Service Management System

> Portfolio write-up for [ucencode.github.io](https://ucencode.github.io).
> Technical claims are drawn from the code in this repository (`pitcar_custom/`,
> Odoo 16, module version `16.0.12`) and its commit history. Business context is
> drawn from the client's own public site, [pitcar.co.id](https://pitcar.co.id)
> — see *Sourcing* at the end.

---

## One-liner

An Odoo 16 ERP implementation for a car repair workshop, centred on a custom
addon that turns a generic sales order into a **service order** — one record
that carries the car, the mechanic team, the service advisor, the invoice and
the post-service follow-up from the moment the car rolls in.

## The client

Pitcar Service is a car workshop in Purwokerto, Central Java. It started in 2021,
mid-pandemic, as a **mobile home-service** operation — mechanics going to the
customer's car rather than the other way round — and grew from there into a
fixed workshop offering home service, pickup and one-stop servicing across
engine, oil, AC, brakes, transmission, suspension, ECU scanning, body repair,
detailing and European makes.

That growth path is the whole reason the project existed. A business that
started by driving to the customer scales on **the car**, not the counter:
the same vehicle comes back, gets picked up, gets serviced at intervals. By the
time I was working on the system it was handling roughly 400–450 units a month
against a base of 350+ regular customers — a volume where remembering which car
belongs to whom, and when it is next due, stops being something people can hold
in their heads.

## Context

The company was moving from "a workshop that works" to "a workshop with a
system" — its own positioning today describes the shift from pandemic-era home
service to a modern workshop running to dealer standards on an ERP-based
management system. The operational picture had to stop being split across parts
stock, service history, transactions, mechanic assignment and follow-up, and
start being one queryable thing.

Two constraints came with that:

- **It had to be handed over.** There was no plan to keep a permanent in-house
  engineering team, so anything exotic would have been a liability. Every
  technical decision below is downstream of that.
- **It had to be replicable.** The business was heading toward a franchise
  model, where the operational system is part of what a new outlet buys. A
  system that only works because the person who built it is available is not a
  system you can franchise.

## Problem

- **The car was not a first-class entity.** Odoo models customers, products and
  orders. It does not model *"the 2016 Toyota Avanza with plate B1234XYZ that
  this customer brings in twice a year."* For a business whose repeat unit is
  the vehicle, that gap is the whole problem — service history becomes guesswork.
- **Context was re-typed at every step.** The car, odometer reading, assigned
  mechanics and service advisor had to be repeated on the quotation, the parts
  picking, the work order sheet and the invoice — four chances to disagree.
- **Pickup and home service break the usual assumptions.** When the car is
  collected rather than driven in, "when did this job actually start" is a
  different question from "when was the order created" — and it is the one that
  matters for turnaround.
- **Follow-up was invisible.** Whether a customer was called after three days,
  whether they were reminded at the three- and six-month service intervals, and
  whether the reminder actually converted into a booking — none of it was data,
  so none of it could be measured. For a business built on 350+ returning
  customers, that is the most valuable data in the shop.
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
  `sale.order` instead of an off-system process — directly serving the repeat
  customer base the business runs on.
- Supported operations at roughly 400–450 service units per month against 350+
  regular customers.
- Shipped continuously against production for eleven months in small reviewed
  increments, then handed the system over — running and maintainable by an
  external maintainer — at the point of ownership transfer.

**Where it ended up.** The ERP-based management system is now part of how Pitcar
publicly positions itself — its "about" page cites it alongside dealer-standard
operations as what separates the current business from the 2021 home-service
original — and the franchise programme sells the computerised operational system
as part of what a new outlet gets. The "must be handed over, must be replicable"
constraint turned out to be the right thing to have optimised for: the system
outlived my involvement and became an asset the business could sell.

*Scope note: my contribution ended at the ownership transfer in October 2024.
The system as marketed today reflects continued development after that point by
the client's side; what I can speak to is the foundation in this repository.*

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

## Sourcing

**Technical claims** — field counts, indexes, constraints, overridden hooks,
report bindings, ACL rows, dependencies, timeline — are checkable against
`pitcar_custom/` and `git log` in this repository.

**Business context** — founding year and home-service origin, service mix,
volume (400–450 units/month), customer base (350+), the ERP as public
positioning, and the franchise programme — comes from the client's own site:

- [pitcar.co.id/tentang](https://pitcar.co.id/tentang/) — history, ERP positioning, customer base
- [pitcar.co.id/layanan](https://pitcar.co.id/layanan/) — service mix
- [pitcar.co.id/kemitraan](https://pitcar.co.id/kemitraan/) and [franchise.pitcar.co.id](https://franchise.pitcar.co.id/) — franchise programme, operational system as part of the package

These are the client's own marketing claims, not measurements I took. They are
reasonable to cite as context; they are not evidence that a specific number was
caused by this code.
