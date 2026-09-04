#!/usr/bin/env python3
"""Render the Pitcar portfolio diagrams as standalone SVGs.

No dependencies — stdlib only. Run from anywhere:

    python3 docs/portfolio/diagrams/render.py

Output lands next to this file as `NN-name.svg`. The palette mirrors the
dark theme tokens in ucencode.github.io (`src/styles/global.css`), so the
diagrams sit correctly on the project modal's black slide background.
"""

from __future__ import annotations

import os
from html import escape

# --- palette (hex equivalents of the site's dark-theme HSL tokens) ---------
BG = "#0b0e13"        # --background 222 25% 6%
PANEL = "#14171f"     # --card       222 20% 10%
PANEL_2 = "#1d212a"   # --secondary  222 18% 14%
BORDER = "#2a2f3a"    # --border, lifted for legibility on screen
TEXT = "#e8ebee"      # --foreground 210 15% 92%
MUTED = "#768393"     # --muted-foreground 215 12% 52%
PRIMARY = "#10b981"   # --primary    160 84% 39%
PRIMARY_DIM = "#0d3b30"
WARN = "#f0b429"
INFO = "#5b9dd9"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, system-ui, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"

HERE = os.path.dirname(os.path.abspath(__file__))


# --- primitives -----------------------------------------------------------
def text(x, y, s, size=14, fill=TEXT, weight="400", anchor="start", mono=False,
         opacity=1.0, spacing=None):
    family = MONO if mono else SANS
    extra = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" '
        f'opacity="{opacity}"{extra}>{escape(s)}</text>'
    )


def rect(x, y, w, h, fill=PANEL, stroke=BORDER, rx=10, sw=1, dash=None, opacity=1.0):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"{d}/>'
    )


def caption(x, y, s, fill=PRIMARY):
    """Small uppercase mono eyebrow, matching the site's section labels."""
    return text(x, y, s.upper(), size=11, fill=fill, mono=True, spacing="1.4")


def card(x, y, w, h, title, lines, accent=BORDER, title_fill=TEXT,
         fill=PANEL, line_size=12, line_gap=19, mono_lines=True, note=None):
    """A titled box with a bulleted body. Returns a list of svg fragments."""
    out = [rect(x, y, w, h, fill=fill, stroke=accent)]
    out.append(f'<rect x="{x}" y="{y}" width="4" height="{h}" rx="2" fill="{accent}"/>')
    out.append(text(x + 16, y + 25, title, size=14, fill=title_fill, weight="600"))
    ly = y + 48
    for ln in lines:
        out.append(text(x + 16, ly, ln, size=line_size, fill=MUTED, mono=mono_lines))
        ly += line_gap
    if note:
        out.append(text(x + 16, y + h - 12, note, size=11, fill=MUTED, opacity=0.8))
    return out


def band(x, y, w, h, fill=PANEL_2, stroke=BORDER, dash=None):
    return rect(x, y, w, h, fill=fill, stroke=stroke, rx=14, dash=dash)


def arrow(x1, y1, x2, y2, color=PRIMARY, width=1.6, dash=None, marker="arrow"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<path d="M {x1} {y1} L {x2} {y2}" stroke="{color}" stroke-width="{width}" '
        f'fill="none" marker-end="url(#{marker})"{d}/>'
    )


def elbow(x1, y1, x2, y2, color=BORDER, width=1.4, dash=None, marker="arrow_dim"):
    """Orthogonal connector: horizontal, then vertical, then horizontal."""
    mx = (x1 + x2) / 2
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<path d="M {x1} {y1} H {mx} V {y2} H {x2}" stroke="{color}" '
        f'stroke-width="{width}" fill="none" marker-end="url(#{marker})"{d}/>'
    )


def chevron(x, y, w, h, label, sub, index, accent=PRIMARY):
    """A numbered pipeline stage box."""
    out = [rect(x, y, w, h, fill=PANEL, stroke=accent)]
    out.append(f'<circle cx="{x + 26}" cy="{y + 26}" r="13" fill="{PRIMARY_DIM}" '
               f'stroke="{accent}" stroke-width="1"/>')
    out.append(text(x + 26, y + 30, str(index), size=12, fill=accent, weight="700",
                    anchor="middle", mono=True))
    out.append(text(x + 48, y + 31, label, size=14, fill=TEXT, weight="600"))
    ly = y + 58
    for ln in sub:
        out.append(text(x + 16, ly, ln, size=11.5, fill=MUTED, mono=True))
        ly += 18
    return out


def svg(width, height, body, title, subtitle):
    defs = f'''<defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{PRIMARY}"/>
    </marker>
    <marker id="arrow_dim" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{MUTED}"/>
    </marker>
    <marker id="arrow_info" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{INFO}"/>
    </marker>
  </defs>'''
    head = [
        text(60, 62, title, size=30, fill=TEXT, weight="700"),
        text(60, 92, subtitle, size=15, fill=MUTED),
    ]
    parts = "\n  ".join(head + body)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{SANS}">\n'
        f'  {defs}\n'
        f'  <rect width="{width}" height="{height}" fill="{BG}"/>\n'
        f'  {parts}\n'
        f'</svg>\n'
    )


# --- 01 · architecture ----------------------------------------------------
def diagram_architecture():
    W, H = 1600, 900
    b = []
    x0, w = 60, 1480

    # Users
    b.append(caption(x0, 136, "Users · one Odoo instance, role-scoped menus"))
    actors = [
        ("Service Advisor", "intake, quotation, feedback, follow-up"),
        ("Mechanic Team", "assigned per order, tracked on the work order"),
        ("Finance / Cashier", "invoicing, car data carried onto the invoice"),
        ("Leadership", "filters & group-by across cars, brands, mechanics"),
    ]
    aw = (w - 3 * 16) / 4
    for i, (name, sub) in enumerate(actors):
        ax = x0 + i * (aw + 16)
        b.append(rect(ax, 150, aw, 68, fill=PANEL, stroke=BORDER))
        b.append(text(ax + 16, 178, name, size=14, fill=TEXT, weight="600"))
        b.append(text(ax + 16, 199, sub, size=11.5, fill=MUTED))
    for i in range(4):
        ax = x0 + i * (aw + 16) + aw / 2
        b.append(arrow(ax, 220, ax, 250, color=MUTED, width=1.3))

    # Platform
    b.append(band(x0, 254, w, 62))
    b.append(text(x0 + 20, 291, "Odoo 16 · web client + ORM + QWeb reporting engine",
                  size=14, fill=TEXT, weight="600"))
    b.append(text(x0 + w - 20, 291, "python 3 · werkzeug", size=12, fill=MUTED,
                  anchor="end", mono=True))
    b.append(arrow(x0 + w / 2, 318, x0 + w / 2, 352, color=PRIMARY, width=1.8))

    # pitcar_custom
    b.append(band(x0, 356, w, 292, fill="#0f1a17", stroke=PRIMARY, dash="6 5"))
    b.append(caption(x0 + 20, 384, "pitcar_custom  ·  v16.0.12  ·  the addon in this repo"))
    b.append(text(x0 + w - 20, 384, "~990 LOC python · 15 view files · LGPL-3",
                  size=11, fill=MUTED, anchor="end", mono=True))
    cw = (w - 40 - 3 * 16) / 4
    cols = [
        ("New models", [
            "res.partner.car",
            "res.partner.car.brand",
            "res.partner.car.type",
            "res.partner.car.transmission",
            "res.partner.source",
            "pitcar.mechanic[.new]",
            "pitcar.service.advisor",
            "feedback.classification",
        ]),
        ("Extended models", [
            "sale.order      +56 fields",
            "account.move",
            "stock.picking",
            "res.partner",
            "res.partner.category",
            "project.task",
            "product.product / .tag",
            "crm.tag",
        ]),
        ("Views & navigation", [
            "tree / form / kanban",
            "search filters + group-by",
            "saved 'reminder due today'",
            "  filters on sale.order",
            "Sales > Car Management",
            "Sales > Mechanic Teams",
            "Sales > Service Advisors",
            "Customer Cars menu",
        ]),
        ("Reports & access", [
            "QWeb PDF: Work Order",
            "  (bound to sale.order)",
            "customised invoice layout",
            "  w/ car + mechanic block",
            "ir.model.access.csv",
            "  9 ACL rows, base.group_user",
            "seed data: partners, cars",
        ]),
    ]
    for i, (t, lines) in enumerate(cols):
        cx = x0 + 20 + i * (cw + 16)
        b += card(cx, 400, cw, 230, t, lines, accent=PRIMARY, line_size=11.5,
                  line_gap=17.5)
    b.append(arrow(x0 + w / 2, 650, x0 + w / 2, 684, color=PRIMARY, width=1.8))

    # Core modules
    b.append(caption(x0, 706, "Odoo core modules declared in __manifest__ depends"))
    deps = ["base", "sale", "sale_management", "sale_stock", "stock", "account",
            "crm", "purchase", "project"]
    dw = (w - 8 * 10) / 9
    for i, dep in enumerate(deps):
        dx = x0 + i * (dw + 10)
        b.append(rect(dx, 718, dw, 46, fill=PANEL, stroke=BORDER, rx=8))
        b.append(text(dx + dw / 2, 746, dep, size=12, fill=TEXT, anchor="middle",
                      mono=True))
    b.append(arrow(x0 + w / 2, 766, x0 + w / 2, 796, color=MUTED, width=1.3))

    # Storage
    b.append(band(x0, 796, w, 54, fill=PANEL))
    b.append(text(x0 + 20, 828, "PostgreSQL", size=14, fill=TEXT, weight="600"))
    b.append(text(x0 + 130, 828,
                  "stored computed fields · trigram indexes on plate & car name · "
                  "SQL uniqueness on mechanic name",
                  size=12, fill=MUTED, mono=True))

    # operating context
    b.append(text(x0, 876,
                  "Operating context — car workshop in Purwokerto, Central Java. "
                  "Grew from pandemic-era mobile home service (2021) into a fixed "
                  "shop running ~400–450 service units/month for 350+ regular "
                  "customers.",
                  size=11.5, fill=MUTED, opacity=0.85))

    return W, H, svg(W, H, b,
                     "Pitcar Service Management System — Architecture",
                     "A single Odoo 16 addon layered over the standard sale / stock / "
                     "account / project modules. No forks, no parallel services.")


# --- 02 · data model ------------------------------------------------------
def diagram_data_model():
    W, H = 1600, 900
    b = []

    b.append(caption(60, 130, "New model", PRIMARY))
    b.append(rect(150, 119, 14, 14, fill=PRIMARY_DIM, stroke=PRIMARY, rx=3))
    b.append(caption(200, 130, "Extended Odoo model", INFO))
    b.append(rect(370, 119, 14, 14, fill=PANEL, stroke=INFO, rx=3))

    def model(x, y, w, h, name, fields, new=True, note=None):
        accent = PRIMARY if new else INFO
        out = [rect(x, y, w, h, fill=PANEL, stroke=accent)]
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="10" '
                   f'fill="{PRIMARY_DIM if new else "#12212e"}"/>')
        out.append(f'<rect x="{x}" y="{y + 18}" width="{w}" height="10" '
                   f'fill="{PRIMARY_DIM if new else "#12212e"}"/>')
        out.append(text(x + 12, y + 19, name, size=12.5, fill=accent, weight="600",
                        mono=True))
        ly = y + 48
        for f in fields:
            out.append(text(x + 12, ly, f, size=11, fill=MUTED, mono=True))
            ly += 16
        if note:
            out.append(text(x + 12, y + h - 10, note, size=10.5, fill=MUTED,
                            opacity=0.75))
        return out

    # column 1 — reference data
    b += model(60, 160, 250, 62, "res.partner.car.brand", ["name · car_count"])
    b += model(60, 244, 250, 62, "res.partner.car.type", ["name · brand · car_count"])
    b += model(60, 328, 250, 62, "res.partner.car.transmission", ["name"])
    b += model(60, 412, 250, 62, "res.partner.source", ["name"])

    # column 2 — customer & car
    b += model(370, 160, 260, 96, "res.partner", [
        "gender · dob · source", "category_id (required)", "phone (required)",
    ], new=False)
    b += model(370, 300, 260, 190, "res.partner.car", [
        "number_plate  unique, trigram",
        "name  computed, stored",
        "brand / brand_type / year",
        "transmission · color",
        "engine_type · engine_number",
        "frame_number · image · notes",
        "partner_id",
    ], note="constraints: unique plate, year 1900..today")

    # column 3 — the hub
    b += model(700, 160, 320, 360, "sale.order", [
        "partner_car_id           m2o",
        "partner_car_* (8 related, stored)",
        "partner_car_odometer",
        "car_arrival_time",
        "service_advisor_id       m2m",
        "car_mechanic_id_new      m2m",
        "generated_mechanic_team  computed",
        "date_completed",
        "customer_rating 1..5",
        "customer_satisfaction    derived",
        "customer_feedback + classification",
        "review_google · follow_instagram",
        "complaint_action / _status",
        "reminder_3_months / _6_months",
        "next_follow_up_3_days / _3m / _6m",
        "campaign (fb / ig / yt / tiktok)",
    ], new=False, note="the operational record: one car visit end to end")

    # column 4 — downstream
    b += model(1090, 160, 300, 124, "stock.picking", [
        "◄ filled by _action_confirm()",
        "partner_car_id · odometer",
        "car_mechanic_id_new · generated_team",
        "service_advisor_id · car_arrival_time",
    ], new=False)
    b += model(1090, 310, 300, 124, "account.move", [
        "◄ filled by _create_invoices()",
        "partner_car_id · odometer",
        "date_sale_quotation / _completed",
        "service_advisor_id · car_arrival_time",
    ], new=False)
    b += model(1090, 460, 300, 80, "project.task", [
        "sale_order_id · entry_date",
        "order_total · days_until_deadline",
    ], new=False)

    # bottom band — m2m dimensions
    b += model(420, 610, 250, 74, "pitcar.mechanic.new", [
        "name (unique) · color",
    ])
    b += model(700, 610, 250, 74, "pitcar.service.advisor", [
        "user_id · name (computed)",
    ])
    b += model(980, 610, 280, 74, "feedback.classification", [
        "name — reused by 3 m2m relations",
    ])

    # relations
    b.append(elbow(310, 191, 370, 340, color=MUTED, dash="4 4"))      # brand -> car
    b.append(elbow(310, 275, 370, 360, color=MUTED, dash="4 4"))      # type -> car
    b.append(elbow(310, 359, 370, 380, color=MUTED, dash="4 4"))      # transmission
    b.append(elbow(310, 443, 370, 205, color=MUTED, dash="4 4"))      # source -> partner
    b.append(arrow(500, 256, 500, 296, color=MUTED, width=1.4, marker="arrow_dim"))
    b.append(arrow(632, 380, 696, 380, color=PRIMARY, width=1.8))
    b.append(text(664, 370, "1 : N", size=10.5, fill=PRIMARY, mono=True,
                  anchor="middle"))

    b.append(arrow(1022, 240, 1086, 222, color=INFO, width=1.8, marker="arrow_info"))
    b.append(arrow(1022, 340, 1086, 372, color=INFO, width=1.8, marker="arrow_info"))
    b.append(arrow(1022, 470, 1086, 500, color=MUTED, width=1.5, marker="arrow_dim"))

    b.append(arrow(545, 610, 700, 522, color=MUTED, width=1.4, marker="arrow_dim"))
    b.append(arrow(825, 610, 825, 524, color=MUTED, width=1.4, marker="arrow_dim"))
    b.append(arrow(1105, 610, 950, 524, color=MUTED, width=1.4, marker="arrow_dim"))
    b.append(text(700, 706, "many-to-many · a visit can involve several mechanics and "
                  "advisors; feedback tags are shared across the post-service, "
                  "3-month and 6-month relations",
                  size=11.5, fill=MUTED, anchor="middle"))

    # footnote
    b.append(rect(60, 760, 1480, 90, fill=PANEL, stroke=BORDER))
    b.append(caption(76, 786, "Modelling decisions worth calling out"))
    notes = [
        "Car attributes are stored related fields on sale.order / account.move — denormalised on purpose so orders stay filterable and groupable by brand, type and year without joins.",
        "number_plate is normalised (spaces stripped, upper-cased) on change and guarded by a search_count constraint; plate and computed car name carry trigram indexes for quick search.",
        "car_mechanic_id (m2o) was kept read-only alongside car_mechanic_id_new (m2m) so historical orders keep their original single-mechanic value after the model changed.",
    ]
    ny = 808
    for n in notes:
        b.append(text(76, ny, "— " + n, size=11.5, fill=MUTED))
        ny += 17

    return W, H, svg(W, H, b,
                     "Data Model — custom and extended entities",
                     "Nine new models plus field extensions on nine core models. "
                     "sale.order is the hub that every workflow reads from.")


# --- 03 · order lifecycle -------------------------------------------------
def diagram_lifecycle():
    W, H = 1600, 900
    b = []

    b.append(caption(60, 132, "Stage · standard Odoo sale flow, extended in place"))

    stages = [
        ("Car arrives", [
            "car_arrival_time",
            "customer + car picked",
            "  (car filters the",
            "   customer, and back)",
        ]),
        ("Quotation", [
            "odometer reading",
            "service advisors (m2m)",
            "mechanic team (m2m)",
            "campaign source",
        ]),
        ("Confirmed", [
            "_action_confirm()",
            "→ stock.picking gets",
            "  car, odometer,",
            "  mechanics, advisors",
        ]),
        ("Work order", [
            "QWeb PDF printed",
            "car block + mechanic",
            "team on the sheet",
            "for the workshop",
        ]),
        ("Invoiced", [
            "_create_invoices()",
            "date_completed = now",
            "→ account.move gets",
            "  the same car block",
        ]),
        ("Post-service", [
            "rating + satisfaction",
            "feedback classification",
            "complaint action if 1–2",
            "follow-up clock starts",
        ]),
    ]
    sw = (1480 - 5 * 14) / 6
    for i, (t, sub) in enumerate(stages):
        sx = 60 + i * (sw + 14)
        b += chevron(sx, 146, sw, 148, t, sub, i + 1)
        if i < 5:
            b.append(arrow(sx + sw + 1, 220, sx + sw + 12, 220, color=PRIMARY,
                           width=1.8))

    # propagation lane
    b.append(band(60, 330, 1480, 214, fill="#0f1a17", stroke=PRIMARY, dash="6 5"))
    b.append(caption(80, 358, "Field propagation — written once on the order, copied "
                              "forward by overridden hooks"))

    src_x, src_w = 80, 380
    b += card(src_x, 376, src_w, 148, "sale.order (source of truth)", [
        "partner_car_id",
        "partner_car_odometer",
        "car_mechanic_id / car_mechanic_id_new",
        "generated_mechanic_team",
        "service_advisor_id",
        "car_arrival_time",
    ], accent=PRIMARY, line_size=11.5, line_gap=17)

    targets = [
        ("stock.picking", [
            "◄ _action_confirm()",
            "car, odometer, mechanics,",
            "advisors, arrival time — so the",
            "warehouse move shows which",
            "car it is for",
        ]),
        ("account.move", [
            "◄ _create_invoices()",
            "same block + quotation date and",
            "completed date, so finance can",
            "group revenue by car, brand",
            "and mechanic",
        ]),
        ("account.move (down payment)", [
            "◄ _prepare_invoice_values()",
            "the sale.advance.payment.inv",
            "wizard carries car + odometer",
            "onto down-payment invoices too",
        ]),
    ]
    tw = (1480 - 40 - src_w - 24 - 2 * 16) / 3
    for i, (name, lines) in enumerate(targets):
        tx = src_x + src_w + 24 + i * (tw + 16)
        b += card(tx, 376, tw, 148, name, lines, accent=INFO, line_size=11,
                  line_gap=16.5)
        b.append(arrow(tx - 15, 450, tx - 3, 450, color=INFO, width=1.5,
                       marker="arrow_info"))

    # guard rails
    b.append(caption(60, 592, "Guard rails encoded in the model"))
    guards = [
        ("Readonly after confirm", "partner_car_id is locked in the sale / done / "
                                   "cancel states via READONLY_FIELD_STATES, so the "
                                   "car cannot drift after the work starts."),
        ("Two-way domain", "Picking a car sets the customer; picking a customer "
                           "narrows the car list to that customer's fleet."),
        ("Unique, clean plates", "Plates are upper-cased and space-stripped on input "
                                 "and rejected if they already exist."),
        ("History preserved", "The superseded single-mechanic field stays readable "
                              "on old records instead of being dropped."),
    ]
    gw = (1480 - 3 * 16) / 4
    for i, (t, d) in enumerate(guards):
        gx = 60 + i * (gw + 16)
        b.append(rect(gx, 606, gw, 118, fill=PANEL, stroke=BORDER))
        b.append(text(gx + 16, 634, t, size=13, fill=TEXT, weight="600"))
        # naive wrap
        words, line, ly = d.split(), "", 656
        for word in words:
            if len(line) + len(word) + 1 > 42:
                b.append(text(gx + 16, ly, line, size=11, fill=MUTED))
                ly += 16
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            b.append(text(gx + 16, ly, line, size=11, fill=MUTED))

    b.append(rect(60, 748, 1480, 100, fill=PANEL, stroke=BORDER))
    b.append(caption(76, 774, "Why extend instead of build separately"))
    b.append(text(76, 800,
                  "Everything above is an override of an existing Odoo hook — no "
                  "parallel service, no shadow tables, no second source of truth.",
                  size=12.5, fill=MUTED))
    b.append(text(76, 822,
                  "That was the constraint the project was designed around: the "
                  "system had to stay maintainable by whoever took it over, using "
                  "stock Odoo knowledge and nothing else.",
                  size=12.5, fill=MUTED))

    return W, H, svg(W, H, b,
                     "Service Order Lifecycle — from arrival to follow-up",
                     "One record follows the car through the workshop. Each stage "
                     "hook copies the car context forward instead of re-entering it.")


# --- 04 · retention engine ------------------------------------------------
def diagram_followup():
    W, H = 1600, 900
    b = []

    # trigger
    b.append(caption(60, 132, "Trigger"))
    b += card(60, 146, 320, 104, "date_completed", [
        "set by _create_invoices()",
        "the moment the car is billed",
    ], accent=PRIMARY, line_size=12, line_gap=18,
        note="one timestamp drives every reminder below")

    b.append(arrow(382, 198, 452, 198, color=PRIMARY, width=1.8))

    # computed windows
    b.append(caption(460, 132, "Stored computed windows (@api.depends on date_completed)"))
    windows = [
        ("+3 days", "next_follow_up_3_days", "did the repair hold?"),
        ("+90 days", "next_follow_up_3_months", "service interval nudge"),
        ("+180 days", "next_follow_up_6_months", "second interval nudge"),
    ]
    ww = (1080 - 2 * 16) / 3
    for i, (delta, field, why) in enumerate(windows):
        wx = 460 + i * (ww + 16)
        b.append(rect(wx, 146, ww, 104, fill=PANEL, stroke=PRIMARY))
        b.append(text(wx + 16, 176, delta, size=17, fill=PRIMARY, weight="700",
                      mono=True))
        b.append(text(wx + 16, 200, field, size=11, fill=TEXT, mono=True))
        b.append(text(wx + 16, 222, why, size=11.5, fill=MUTED))
        b.append(text(wx + 16, 240, "+ notif_… human-readable label", size=10.5,
                      fill=MUTED, opacity=0.8))
        b.append(arrow(wx + ww / 2, 252, wx + ww / 2, 282, color=PRIMARY, width=1.5))

    # saved filters
    b.append(band(460, 286, 1080, 92, fill=PANEL))
    b.append(caption(480, 312, "Saved search filters on the sale.order list"))
    b.append(text(480, 340, "\"Reminder 3 Days — Hari ini\"    ·    "
                            "\"Reminder 3 Bulan — Hari ini\"    ·    "
                            "\"Reminder 6 Bulan — Hari ini\"",
                  size=13, fill=TEXT, mono=True))
    b.append(text(480, 364, "The advisor opens one saved filter and gets today's call "
                            "list. No cron, no queue, no separate reminder app to keep "
                            "in sync.", size=11.5, fill=MUTED))

    b.append(arrow(1000, 380, 1000, 406, color=PRIMARY, width=1.8))

    # feedback branch
    b.append(caption(60, 420, "Post-service capture (day 0–3)"))
    b += card(60, 434, 400, 136, "is_willing_to_feedback", [
        "no  → no_feedback_reason, and the",
        "     rating / satisfaction / tag",
        "     fields are cleared on change",
        "yes → continue to rating",
    ], accent=WARN, line_size=11.5, line_gap=17)

    b.append(arrow(462, 502, 512, 502, color=MUTED, width=1.5, marker="arrow_dim"))

    b += card(512, 434, 440, 136, "customer_rating  1 – 5", [
        "1 → very_dissatisfied     4 → satisfied",
        "2 → dissatisfied          5 → very_satisfied",
        "3 → neutral",
        "mapped in onchange, create() and write()",
    ], accent=WARN, line_size=11.5, line_gap=17,
        note="satisfaction is readonly — derived, never typed by hand")

    b.append(arrow(954, 502, 1004, 502, color=MUTED, width=1.5, marker="arrow_dim"))

    b += card(1004, 434, 536, 136, "rating ≤ 2  →  complaint path opens", [
        "show_complaint_action flips true",
        "complaint_action   what was done about it",
        "complaint_status   solved / not solved",
        "feedback_classification_ids  what went wrong",
    ], accent="#e05252", line_size=11.5, line_gap=17)

    # reminder branch
    b.append(caption(60, 604, "Reminder capture (month 3 and month 6, same shape)"))
    cells = [
        ("reminder_N_months", "was the customer contacted at all — yes / no, with a "
                              "reason recorded when not"),
        ("is_response_N_months", "did they answer, and what did they say "
                                 "(feedback_N_months)"),
        ("category_N_months", "tagged with feedback.classification through a dedicated "
                              "m2m relation table per window"),
        ("is_booking_N_months", "did the reminder convert — and if so, "
                                "booking_date_N_months"),
    ]
    cw = (1480 - 3 * 16) / 4
    for i, (field, desc) in enumerate(cells):
        cx = 60 + i * (cw + 16)
        b.append(rect(cx, 610, cw, 122, fill=PANEL, stroke=BORDER))
        b.append(f'<rect x="{cx}" y="610" width="4" height="122" rx="2" '
                 f'fill="{INFO}"/>')
        b.append(text(cx + 16, 638, field, size=12.5, fill=INFO, weight="600",
                      mono=True))
        words, line, ly = desc.split(), "", 664
        for word in words:
            if len(line) + len(word) + 1 > 40:
                b.append(text(cx + 16, ly, line, size=11.5, fill=MUTED))
                ly += 17
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            b.append(text(cx + 16, ly, line, size=11.5, fill=MUTED))
        if i < 3:
            b.append(arrow(cx + cw + 2, 671, cx + cw + 12, 671, color=MUTED,
                           width=1.4, marker="arrow_dim"))

    b.append(rect(60, 756, 1480, 92, fill=PANEL, stroke=BORDER))
    b.append(caption(76, 782, "The point"))
    b.append(text(76, 808,
                  "Follow-up is the part of a service business that usually lives "
                  "outside the system — a notebook, a spreadsheet, a chat thread. "
                  "Modelling it as fields on the order that already",
                  size=12.5, fill=MUTED))
    b.append(text(76, 830,
                  "exists makes contact rate, response rate and rebooking rate "
                  "ordinary group-by queries on sale.order, with nothing to "
                  "reconcile between two systems.",
                  size=12.5, fill=MUTED))

    return W, H, svg(W, H, b,
                     "Feedback & Follow-up Engine",
                     "One billing timestamp expands into a 3-day, 3-month and "
                     "6-month retention workflow that the service advisor works "
                     "off a saved filter.")


DIAGRAMS = {
    "01-architecture.svg": diagram_architecture,
    "02-data-model.svg": diagram_data_model,
    "03-order-lifecycle.svg": diagram_lifecycle,
    "04-followup-engine.svg": diagram_followup,
}


def main():
    for filename, fn in DIAGRAMS.items():
        _, _, content = fn()
        path = os.path.join(HERE, filename)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"wrote {path} ({len(content):,} bytes)")


if __name__ == "__main__":
    main()
