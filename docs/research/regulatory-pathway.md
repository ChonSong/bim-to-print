# Regulatory pathway — NCC compliance for 3D-printed concrete in NSW

How to navigate the National Construction Code (NCC) to obtain approval for a 3D-printed dwelling in New South Wales.

---

## The compliance framework

For a 3D-printed concrete house, the NCC qualifies it as an **innovative / non‑standard construction method**. Since the NCC does not yet have a *Deemed-to-Satisfy* (DTS) solution for 3DCP, you must take the **Performance Solution** path — formally called an **Evidence of Suitability** (EoS) dossier.

```
┌─────────────────────────────────────────────────────────────┐
│ PERFORMANCE SOLUTION PATH (NCC A2G2)                        │
│                                                             │
│ Step 1: Identify applicable Performance Requirements (HxPx) │
│ Step 2: Propose a Performance Solution (your 3DCP method)   │
│ Step 3: Build Evidence of Suitability dossier               │
│ Step 4: Engage a registered certifier for assessment        │
│ Step 5: Obtain approval                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1 — Identify applicable Performance Requirements

These are the same for any residential building. The key clauses for a 3D-printed wall system:

| NCC Clause | Performance Requirement | 3DCP-specific concern |
|-----------|----------------------|----------------------|
| **H1P1** | A building must have structural capacity to resist loads. | **Inter-layer bond strength**; monolithic vs segmented behaviour |
| **H1D4** | Structural robustness: ability to withstand disproportionate collapse. | Print-path continuity; cold joints between print sessions |
| **H2P1** | Fire resistance: elements must achieve the required FRL. | **Layered construction** vs monolithic concrete FRL |
| **H3P1** | Weatherproofing: exterior walls must resist moisture penetration. | **Layer lines** as potential water ingress paths |
| **H4P1** | Energy efficiency: thermal performance (total R-value). | **Thermal mass** of printed concrete; cavity vs solid fill |
| **H5P1** | Sound insulation: walls must achieve Rw + Ctr ≥ 50 (adjacent dwellings). | **Mass law** — solid 3DCP walls perform well inherently |

---

## Step 2 — EoS methods (NCC Schedule 2, A2G2)

You can satisfy the evidence requirement through any combination of:

| Method | What it is | For 3DCP applicability |
|--------|-----------|----------------------|
| **A2G2(a)** | Documentary evidence (NATA test reports, prior approvals) | **Primary route** — lab tests for structure/fire/weather |
| **A2G2(b)** | Comparison with a DTS solution (e.g., concrete blockwork) | Can argue 3DCP performs equivalently to 250mm concrete wall |
| **A2G2(c)** | Expert judgment (registered engineer's statement) | Structural engineer declaration on wall adequacy |
| **A2G2(d)** | Verification methods (testing, inspection, calculation) | Load testing in-situ + calculation report |

---

## Step 3 — Build the EoS dossier

The dossier structure is documented in [`evidence-of-suitability-dossier.md`](evidence-of-suitability-dossier.md). In summary:

1. Project description & model
2. Performance Requirement matrix (HxPx → your evidence)
3. Material qualification reports (compressive, flexural, bond)
4. Fire-resistance test report
5. Weatherproofing / moisture ingress report
6. Thermal performance calculation
7. Structural engineer's certificate
8. Inspector sign-off (during/after print)

---

## Step 4 — Engage a certifier

| Certifier type | Role | Who to contact |
|---------------|------|----------------|
| **Principal Certifier** (private) | Assesses and approves the Performance Solution | CertiBuild or similar |
| **NSW Warne Properties Unit** | Government 3DP pilot experts — can recommend certifiers | Reach out via NSW Planning |
| **Registered Building Surveyor** | Issues Construction Certificate (CC) and Occupation Certificate (OC) | Must be registered with NSW Fair Trading |

> **Key advice:** Engage a certifier *before* you start designing. This is the most common failure mode — designing to a DTS standard then hoping the certifier will accept a Performance Solution late in the process.

---

## Step 5 — Obtain approval

1. **Development Application (DA)** — Council approval for land use
2. **Construction Certificate (CC)** — Detailed compliance assessment by certifier
3. **Pre-print inspection** — Certifier reviews G-code, layering strategy, material properties
4. **In-process inspection** — Monitor layer adhesion, dimensions, tolerances
5. **Post-print verification** — Core samples tested; structural check
6. **Occupation Certificate (OC)** — Final sign-off

---

## Timeline estimate

| Phase | Duration | Notes |
|-------|----------|-------|
| Pre-certifier engagement | Month 1–2 | Can overlap with lab testing |
| Lab testing (full suite) | Month 2–6 | Concrete curing (28 days) is the bottleneck |
| Dossier compilation | Month 4–6 | Overlaps with testing |
| DA submission → approval | Month 6–10 | Council-dependent (3–4 months typical) |
| CC approval | Month 10–12 | Certifier review time |
| Print + inspect | Month 12–16 | Pilot build |
| Final sign-off (OC) | Month 16–18 | Post-print testing |

**Total: 12–18 months from start to occupation.**

---

## Key contacts for regulatory navigation

| Organisation | Role | How to approach |
|-------------|------|-----------------|
| **Warne Properties Unit** (NSW Planning) | Government pilot lead | Cold outreach — reference Contour3D pilot |
| **NSW Building Commissioner** | Regulatory oversight | Formal guidance may exist for 3DCP |
| **Engineers Australia** | Professional body | Find a structural engineer experienced in 3DCP |
| **Australian Certifiers Institute** | Certifier network | Find a certifier willing to assess 3DCP |
