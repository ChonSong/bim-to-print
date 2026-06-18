# Financial model template — 3DCP pilot (CAPEX/OPEX)

Cost breakdown structure and unit economics for a 3D-printed concrete housing pilot.

---

## Capital expenditure (CAPEX)

### Printer acquisition

| Item | Contour3D (partner) | CyBe (buy) | Luyten (buy) | Notes |
|------|---------------------|------------|--------------|-------|
| Printer unit | $0 (service) | $80,000 | $300–500k | CyBe price from EUR 49k |
| Delivery & install | $0 | $5–10k | $10–25k |
| Training | $0 | $5–10k | $10–20k |
| Mixing unit | $0 | Included (starter kit) | $15–30k |
| On-site shelter | $0 | $10–20k | $10–20k | Covered print area |
| **Subtotal** | **$0** | **$100–120k** | **$345–595k** |

### Site preparation

| Item | Cost | Notes |
|------|------|-------|
| Level concrete pad | $5–15k | Depending on subsoil |
| Utilities connection | $3–8k | Power + water for printer |
| Access / cranage | $2–5k | If gantry needs assembly |
| Fencing / security | $2–5k | |
| **Subtotal** | **$12–33k** | |

### Design & engineering

| Item | Cost | Notes |
|------|------|-------|
| BIM model | $10–25k | 70 m² 2-bedroom from architect |
| Structural engineering | $8–15k | Load calcs, certificate |
| G-code generation (`bim2print`) | $0–2k | Open-source |
| **Subtotal** | **$18–42k** | |

---

## Operational expenditure (OPEX)

### Materials (per pilot)

| Item | Quantity | Unit cost | Total |
|------|----------|-----------|-------|
| Concrete (printable mix) | 15–25 m³ | $250–400/m³ | $3,750–10,000 |
| Reinforcement (reduced) | — | — | $2,000–5,000 |
| Additives (retarder, fibres) | — | — | $1,000–2,000 |
| **Subtotal** | | | **$6,750–17,000** |

### Testing & certification

| Item | Cost | Notes |
|------|------|-------|
| Lab test suite (full) | $8,800–21,000 | See lab-certification-directory |
| Certifier engagement | $5–15k | Pre-engagement + assessment |
| **Subtotal** | **$13,800–36,000** | |

### Labour

| Role | Effort (months) | Monthly cost | Total |
|------|-----------------|-------------|-------|
| Project manager | 12 | $12–15k | $144–180k |
| Structural engineer (part-time) | 6 | $5–8k | $30–48k |
| Print operator | 4 | $8–10k | $32–40k |
| Site labour (finishing) | 6 | $12–15k | $72–90k |
| **Subtotal** | | | **$278–358k** |

### Fit-out & services

| Item | Cost | Notes |
|------|------|-------|
| Roof structure + covering | $25–40k | Lightweight roof |
| Plumbing | $10–20k | |
| Electrical + data | $10–15k | |
| Internal finishing | $15–30k | Render, paint, floors |
| External finishing | $10–20k | Render / cladding |
| **Subtotal** | **$70–125k** | |

---

## Total — all scenarios

| Scenario | Printer | Fit-out | Other | **Total** | Contingency (20%) | **Grand total** |
|----------|---------|---------|-------|:---------:|:-----------------:|:---------------:|
| **Pilot with Contour3D** | $0 | $278–358k | $70–125k + $14–36k | **$362–519k** | **$72–104k** | **$434–623k** |
| **Pilot with CyBe** | $100–120k | $278–358k | $70–125k + $14–36k | **$462–639k** | **$92–128k** | **$554–767k** |
| **Pilot with Luyten** | $345–595k | $278–358k | $70–125k + $14–36k | **$707–1,114k** | **$141–223k** | **$848–1,337k** |

---

## Per-print cost estimator

Use this to calculate cost per m² for production runs (after pilot):

| Input | Value |
|-------|-------|
| Wall area to print | _______ m² |
| Print speed | _______ mm/s |
| Layer height | _______ mm |
| Extrusion width | _______ mm |
| Concrete cost per m³ | $_______ |
| Print time (estimated) | _______ hours |
| Labour (per hour) | $_______ |
| **Estimated wall cost per m²** | **$_______** |

### Fill formula

```
Concrete volume (m³) = wall_area × extrusion_width × layers_per_m
Concrete cost = volume × cost_per_m³
Labour cost = print_hours × hourly_rate
Total wall cost = concrete + labour + mixing + overhead
Cost per m² = total / wall_area
```

---

## Break-even analysis (for CyBe or Luyten purchase)

| Printer | Purchase cost | Savings vs traditional (per m²) | m² to break even |
|---------|--------------|-------------------------------|:----------------:|
| **CyBe** | $100–120k | $280/m² (wall only) | **357–429 m²** |
| **Luyten** | $345–595k | $280/m² (wall only) | **1,232–2,125 m²** |

> Break-even assumes $280/m² savings vs traditional wall construction at $560/m². At 70 m² per dwelling:
> - **CyBe** breaks even after 5–6 dwellings
> - **Luyten** breaks even after 18–30 dwellings
