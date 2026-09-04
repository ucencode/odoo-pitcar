# Portfolio content — Pitcar

Source material for the Pitcar entry on [ucencode.github.io](https://ucencode.github.io).
Everything here is derived from the code in `pitcar_custom/` and this
repository's commit history, so the claims on the site can be traced back to
something real.

| File | What it is |
|---|---|
| [`pitcar-overview.md`](pitcar-overview.md) | The long-form write-up: context, problem, role, what was built, engineering decisions, outcome, timeline |
| [`projects-entry.ts`](projects-entry.ts) | Drop-in replacement for the `pitcar` object in the site's `src/data/projects.ts` |
| [`diagrams/render.py`](diagrams/render.py) | Stdlib-only generator for the four SVG diagrams |
| `diagrams/*.svg` | The rendered diagrams, 1600×900, on the site's dark palette |

## Using it on the site

```bash
# from the ucencode.github.io checkout
mkdir -p public/slides/pitcar
cp ../odoo-pitcar/docs/portfolio/diagrams/*.svg public/slides/pitcar/
```

Then replace the `pitcar` object in `src/data/projects.ts` with the contents of
`projects-entry.ts` (drop the header comment). The `slides` array already
references the four diagrams alongside the existing `slide-01.webp` screenshot.

The project modal renders slides with a plain `<img>`, so SVG works without any
change to the component. If you would rather ship raster images, any SVG → WebP
converter will do — the diagrams are authored at exactly 1600×900.

## Regenerating the diagrams

```bash
python3 docs/portfolio/diagrams/render.py
```

No dependencies. Colours at the top of `render.py` mirror the dark-theme tokens
in the site's `src/styles/global.css`, so if the site palette changes, change
them in one place and re-run.

## A note on claims

**Code claims** — field counts, indexes, overridden hooks, constraints, report
bindings, ACL rows, dependencies, timeline — are checkable against
`pitcar_custom/` and `git log` in this repository.

**First-hand claims** — introducing Odoo as the platform choice, building and
maintaining the addon, the system carrying hundreds of service orders per month
from first production deployment, recommending the full-time hire and onboarding
the successor — are Ahmad's own account of the engagement.

**Client marketing claims** — the 2021 home-service origin, service mix, 400–450
units per month, 350+ regular customers, the ERP as public positioning, and the
franchise programme — come from the client's own public site
([tentang](https://pitcar.co.id/tentang/), [layanan](https://pitcar.co.id/layanan/),
[kemitraan](https://pitcar.co.id/kemitraan/),
[franchise.pitcar.co.id](https://franchise.pitcar.co.id/)). Cited as context —
not measurements taken from the system, and not evidence that a given number was
caused by this code.

**Scope boundary.** The contribution in this repository ends at the ownership
transfer in October 2024. The current figures and the franchise programme
post-date that. The write-up keeps these separate deliberately — the volume
claim made in Ahmad's own voice is "hundreds of service orders per month from
first deployment"; the 400–450 figure is attributed to the business, present
tense. Don't collapse the two.
