# Research — Sydney 3D-Printed Housing (mid-2025)

Master index of market research, vendor intelligence, regulatory pathways, and go-to-market artifacts for 3D concrete printing in Sydney, Australia.

---

## Quick navigation

| Document | What it covers | Who it's for |
|----------|---------------|--------------|
| [`vendor-database.md`](vendor-database.md) | Printer vendors, specs, pricing, contacts, demo paths | Procurement / engineering |
| [`decision-matrix.md`](decision-matrix.md) | Vendor comparison (cost × speed × envelope × maturity) | Decision-makers |
| [`lab-certification-directory.md`](lab-certification-directory.md) | Testing labs, certifiers, NCC clause map | Compliance / QA |
| [`software-stack.md`](software-stack.md) | CAD/CAM tools, slicers, libraries, scripting workflows | Design / research |
| [`regulatory-pathway.md`](regulatory-pathway.md) | NCC compliance path, Evidence-of-Suitability, fire/structural | Regulatory |
| [`sydney-market-landscape.md`](sydney-market-landscape.md) | Market context, housing demand, council pilots, cost drivers | Strategy / BD |
| [`pilot-roadmap.md`](pilot-roadmap.md) | 18-month execution plan with milestones and budgets | Project management |
| [`grant-proposal-template.md`](grant-proposal-template.md) | 1-page council/grant pitch | BD / fundraising |
| [`evidence-of-suitability-dossier.md`](evidence-suitability-dossier.md) | EoS template with all required sections | Compliance |

### Financial & planning

| Artifact | Location | Status |
|----------|----------|--------|
| Financial projection template (CAPEX/OPEX) | [`docs/research/financial-model-template.md`](financial-model-template.md) | Ready to use |
| Budget tracker (print-cost-per-m²) | [`docs/research/financial-model-template.md`](financial-model-template.md#per-print-cost-estimator) | Formulas included |
| Grant eligibility matrix | [`docs/research/grant-proposal-template.md`](grant-proposal-template.md#grant-eligibility-matrix) | Template |

---

## How this repo connects to the real world

```
Vendor database ───→ Printer selection ───→ BIM model (IFC/GH)
                                     ↓
                              bim2print pipeline
                              (slicer → toolpath → G-code)
                                     ↓
                            Compliance dossier ─→ Certifier
                                     ↓
                              Pilot build ──→ Council sign-off
```

The research module feeds the pipeline: vendor specs inform print parameters, compliance docs inform material qualification, the G-code goes to the selected printer.

---

## Key contacts (mid-2025)

| Organisation | Role | Contact |
|-------------|------|---------|
| **Contour3D** | Pilot partner — occupied 3DP house, Woolooware | <https://contour3d.com.au> |
| **Luyten 3D** | Gantry printer manufacturer (100m build height) | <https://luyten3d.com> |
| **CyBe Construction** | Fixed-printer systems from €49k | <https://cybe.eu> |
| **ULTRA Labs (Melbourne)** | NATA concrete testing | — |
| **RMIT — Centre for Adv. Manufacturing** | Material characterisation research | — |
| **Warne Properties (NSW Gov)** | Social housing 3DP pilot | — |
| **James Hardie** | Affordable housing program partner | — |
