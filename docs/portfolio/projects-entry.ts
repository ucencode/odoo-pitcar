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
    "An Odoo 16 ERP implementation for a car repair workshop, centred on a custom addon that turns a generic sales order into a service order — one record carrying the car, mechanic team, service advisor, invoice and post-service follow-up from the moment the car rolls in.",
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
        "Odoo models customers, products and orders — but not the car. Without the vehicle as a first-class entity, service history for a returning customer was guesswork.",
        "The car, odometer, assigned mechanics and service advisor had to be re-typed on the quotation, the parts picking, the work order and the invoice — four chances for the same visit to disagree with itself.",
        "Follow-up after a service was not data. Whether a customer was called, reminded at the 3- and 6-month intervals, or rebooked could not be measured.",
        "The company needed a system that could be handed over — there was no plan for a permanent in-house engineering team, so anything exotic would have become a liability.",
      ],
    },
    {
      title: "My Role",
      bullets: [
        "Odoo / backend developer — designed and built the custom addon and maintained it in production for around 11 months, authoring the large majority of the repository's commits.",
        "Worked with a second engineer through a PR review flow, shipping small reviewable changes against a live system rather than big-bang releases.",
        "Owned the domain modelling, the workflow extensions, the shop-floor PDF reports, and the handover state of the codebase at ownership transfer.",
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
        "Supported operations at around 400+ service units per month.",
        "Handed the system over running and maintainable — every customisation is a standard Odoo override, readable by any Odoo developer without tribal knowledge.",
      ],
    },
  ],
  links: [
    { label: "Company Website", url: "https://pitcar.co.id" },
    {
      label: "Archived Code Snapshot",
      url: "https://github.com/ucencode/odoo-pitcar",
    },
  ],
}
