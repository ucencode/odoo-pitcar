/**
 * Drop-in replacement for the `pitcar` entry in
 * ucencode.github.io → src/data/projects.ts
 *
 * Matches the existing `Project` interface exactly (id, title, description,
 * image, slides, projectStack, links, additionalInfo) and follows the
 * Problem / My Role / What I Built / Outcome section shape used by the
 * ClinicOS and BookYourGP entries.
 *
 * Before pasting, copy the diagrams into the site repo:
 *
 *   mkdir -p public/slides/pitcar
 *   cp <this-repo>/docs/portfolio/diagrams/*.svg public/slides/pitcar/
 *
 * The modal renders slides with a plain <img>, so the SVGs work as-is. They
 * are authored at 1600×900 on the same dark palette as the site, so they sit
 * correctly on the modal's black slide background.
 */

{
  id: "pitcar",
  title: "Pitcar Service Management System",
  description:
    "I introduced Odoo to a car workshop that had grown out of pandemic-era mobile home service, then built the addon that turns a generic sales order into a service order — one record carrying the car, mechanic team, service advisor, invoice and post-service follow-up from the moment the car rolls in. Built deliberately to be inherited, and then handed over to the full-time engineer I recommended they hire.",
  image: {
    src: "/projects/pitcar-preview.webp",
    alt: "Pitcar project preview",
  },
  slides: [
    {
      path: "slides/pitcar/slide-01.webp",
      caption: "Sales list view — orders grouped and filtered by car, brand and mechanic team",
    },
    {
      path: "slides/pitcar/01-architecture.svg",
      caption:
        "One Odoo 16 instance. All customisation lives in a single addon layered over the standard sale / stock / account / project modules — no forks, no parallel services.",
    },
    {
      path: "slides/pitcar/02-data-model.svg",
      caption:
        "Nine new models plus field extensions on nine core models. The car becomes a first-class entity; sale.order is the hub every workflow reads from.",
    },
    {
      path: "slides/pitcar/03-order-lifecycle.svg",
      caption:
        "The car context is entered once and copied forward by overriding the hooks Odoo already calls — confirm, invoice, down-payment.",
    },
    {
      path: "slides/pitcar/04-followup-engine.svg",
      caption:
        "One billing timestamp expands into a 3-day, 3-month and 6-month retention workflow the service advisor works off a saved filter.",
    },
  ],
  projectStack: [
    "Odoo 16",
    "Python",
    "PostgreSQL",
    "Custom Addons",
    "XML / QWeb",
    "ORM Overrides",
    "Data Modeling",
    "Query Optimization",
  ],
  additionalInfo: [
    {
      title: "Problem",
      bullets: [
        "The business scales on the car, not the counter — it began as mobile home service, so the same vehicle comes back, gets collected, and is due again at intervals. Odoo models customers, products and orders, but not the car, so service history for a returning customer was guesswork.",
        "The car, odometer, assigned mechanics and service advisor had to be re-typed on the quotation, the parts picking, the work order and the invoice — four chances for the same visit to disagree with itself.",
        "Follow-up was not data. Whether a customer was called, reminded at the 3- and 6-month service intervals, or rebooked could not be measured — for a shop running on 350+ repeat customers, the most valuable information in the building.",
        "And the constraint that mattered most was about me, not them: I was working on an uncommitted footing. A shop running its daily operations on my code deserved software that would outlive my availability, so the system had to be one a different engineer could pick up cold.",
      ],
    },
    {
      title: "My Role",
      bullets: [
        "Made the platform call. The client came with an operations problem, not an ERP to implement — choosing to customise Odoo rather than write a bespoke workshop app was my decision, and the one the whole project rests on. It left them with a system any Odoo developer on the market can maintain.",
        "Designed and built the custom addon solo and maintained it in production for around 11 months, authoring the large majority of the repository's commits.",
        "Shipped small reviewable changes against a live system rather than big-bang releases — the shop had cars in the bay throughout.",
        "Engineered my own replacement. Working on an uncommitted footing was a risk to the client, so I told them to hire a permanent engineer, onboarded the person they hired through PR review until they were the one merging, and closed out my involvement deliberately.",
      ],
    },
    {
      title: "What I Built",
      bullets: [
        "Modelled the vehicle as a real entity — plates normalised and uniqueness-constrained, trigram-indexed search, validated year, and two-way domains so a car and its owner can never be mismatched on an order.",
        "Extended sale.order into a service order in place (56 fields): mechanic teams and service advisors as many-to-many, odometer and arrival time, campaign attribution, and eight stored related car attributes so orders stay filterable without joins.",
        "Made context propagate instead of being re-entered — overriding _action_confirm, _create_invoices and the advance-payment wizard so the car block flows onto the picking and the invoice automatically.",
        "Built a retention engine off a single billing timestamp: stored computed 3-day / 3-month / 6-month windows surfaced as saved 'due today' filters, with feedback, satisfaction, complaint handling and rebooking captured on the order itself — no cron, no queue, nothing extra to keep in sync.",
        "Delivered the shop-floor output: a QWeb Work Order PDF and a customised invoice layout printing the same car and mechanic block the workshop worked from, plus filters, group-bys and configuration menus for day-to-day operations.",
      ],
    },
    {
      title: "Outcome",
      bullets: [
        "Replaced fragmented operational tooling with one Odoo instance covering sales, service, inventory, invoicing and customer management.",
        "Made service history queryable — every visit attached to a specific car, with mechanic team, advisor, odometer and outcome attached to it.",
        "Turned follow-up into data: contact, response and rebooking rates at 3 days, 3 months and 6 months became ordinary group-by queries instead of an off-system process.",
        "Ran real operations from first production deployment onward, handling hundreds of service orders per month.",
        "Handed over cleanly — the client hired a permanent engineer on my recommendation, I onboarded them, and the system carried on without me. Every customisation is a standard Odoo override, readable without tribal knowledge.",
        "Two years on, the ERP layer this work established is part of how the company publicly positions itself, and the computerised operational system forms part of what franchise partners buy. The business now reports 400–450 units a month against 350+ regular customers — figures that post-date my involvement, and the return on having built something inheritable.",
      ],
    },
  ],
  links: [
    { label: "Company Website", url: "https://pitcar.co.id" },
    { label: "Franchise Programme", url: "https://franchise.pitcar.co.id" },
    {
      label: "Archived Code Snapshot",
      url: "https://github.com/ucencode/odoo-pitcar",
    },
  ],
}
