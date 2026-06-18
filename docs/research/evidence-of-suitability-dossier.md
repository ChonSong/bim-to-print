# Evidence-of-Suitability dossier template — 3D-printed concrete

Structured template for compiling the evidence package required under NCC A2G2 (Performance Solution) for a 3D-printed concrete dwelling.

---

## Document overview

| Field | Value |
|-------|-------|
| **Project** | [Project name] |
| **Applicant** | [Your organisation] |
| **Print system** | [Vendor, printer model] |
| **Concrete mix** | [Mix designation] |
| **NCC pathway** | Performance Solution (A2G2) |
| **Certifier** | [Name of certifier] |
| **Date** | [Date] |
| **Version** | 0.1 |

---

## Section 1 — Project description

> **Instructions:** Summarise the building, its use (e.g., single dwelling), size (floor area, wall area), number of storeys, and all structural building elements that will be 3D-printed.

---

## Section 2 — Performance Requirement matrix

| NCC Clause | Performance Requirement | How 3DCP meets it | Evidence ref |
|-----------|----------------------|-------------------|-------------|
| **H1P1** | Structural capacity to resist loads | Structural engineer calculation + inter-layer bond test | Sec 3.1, Sec 7 |
| **H1D4** | Robustness / disproportionate collapse | Monolithic printed wall behaviour; continuous print path | Sec 3.1, Sec 7 |
| **H2P1** | Fire resistance (FRL) | NATA fire test report on printed wall panel | Sec 3.3 |
| **H3P1** | Weatherproofing | Water penetration test (ASTM E514) | Sec 3.4 |
| **H4P1** | Energy efficiency (R-value) | Thermal conductivity (λ) test + calculation | Sec 3.5 |
| **H5P1** | Sound insulation (Rw) | Airborne sound test on printed wall assembly | Sec 3.6 |

---

## Section 3 — Material qualification reports

### 3.1 Structural / compressive strength

- **Test standard:** AS 1012.9 / AS 1012.14
- **Lab:** [Lab name — e.g., ULTRA Labs]
- **Sample:** 3D-printed wall panel, ~300 mm × 300 mm × [t] mm
- **Result:** [MPa at 7 days / 28 days]
- **Report ref:** [Lab report number]
- **Status:** ☐ Pending ☐ In progress ☐ Complete

### 3.2 Inter-layer bond strength

- **Test standard:** ASTM C1583 / custom pull-off test
- **Sample:** Core samples taken from printed panel
- **Result:** [MPa bond strength]
- **Report ref:** [Lab report number]
- **Status:** ☐ Pending ☐ In progress ☐ Complete

### 3.3 Fire resistance (FRL)

- **Test standard:** AS 1530.4
- **Configuration:** [Wall thickness — e.g., 200 mm printed panel]
- **Result:** [FRL — e.g., 60/60/60]
- **Report ref:** [Lab report number]
- **Status:** ☐ Pending ☐ In progress ☐ Complete

### 3.4 Water penetration / weatherproofing

- **Test standard:** ASTM E514
- **Configuration:** Printed wall panel, finished + unfinished
- **Result:** [Leakage observed / not observed]
- **Report ref:** [Lab report number]
- **Status:** ☐ Pending ☐ In progress ☐ Complete

### 3.5 Thermal conductivity

- **Test standard:** AS 2464.1 / ASTM C518
- **Result:** λ = [X] W/m·K
- **Calculated R-value for [t] mm wall:** R = [X]
- **Report ref:** [Lab report number]
- **Status:** ☐ Pending ☐ In progress ☐ Complete

### 3.6 Airborne sound insulation

- **Test standard:** AS 1191 / ISO 717-1
- **Configuration:** [Thickness + any surface treatment]
- **Result:** Rw = [X] dB
- **Report ref:** [Lab report number]
- **Status:** ☐ Pending ☐ In progress ☐ Complete

---

## Section 4 — G-code & print specification

- **Printer model:** [Vendor, model]
- **Software pipeline:** `bim-to-print` v[X.X]
- **Layer height:** [X] mm
- **Nozzle diameter:** [X] mm
- **Extrusion width:** [X] mm
- **Perimeter count:** [X]
- **Infill pattern:** [lines / grid / none]
- **Infill density:** [X]%
- **Print speed:** [X] mm/min
- **Travel speed:** [X] mm/min
- **Print file ref:** [`pilot-build-v1.gcode`]
- **Verification:** G-code checked for: ☐ Collisions ☐ Over-extrusion ☐ Underextrusion

---

## Section 5 — Quality assurance plan

### Print-time QA checks

| Check | Frequency | Method | Acceptable tolerance |
|-------|-----------|--------|---------------------|
| Layer height | Every 10 layers | Calliper measurement | ±1 mm |
| Extrusion width | Every 10 layers | Visual + width gauge | ±2 mm |
| Plumb / verticality | Each wall | Laser level | ±3 mm per 3 m |
| Inter-layer bond > goal | Each shift | Pull-off test on test coupon | X MPa |

### Post-print verification

| Check | Method | NCC clause |
|-------|--------|-----------|
| Core compressive strength | AS 1012.14 coring + AS 1012.9 test | H1P1 |
| Dimensional compliance | As-built survey vs BIM model | CC conditions |
| Weatherproofing | Hose test / visual | H3P1 |

---

## Section 6 — Structural engineer's certificate

> **Instructions:** To be completed and signed by a registered structural engineer.

- Engineer: [Name], CPEng NER
- Registration: [MIEAust / FIEAust, NER number]
- Statement: *"I have reviewed the design, material test results, print path, and QA plan for the 3D-printed concrete walls at [project]. In my opinion, the printed wall system meets the structural performance requirements of NCC Clause H1P1."*
- Signature: _______
- Date: _______

---

## Section 7 — References

- [ ] NATA test report — Compressive strength (ref: _____)
- [ ] NATA test report — Fire resistance (ref: _____)
- [ ] NATA test report — Water penetration (ref: _____)
- [ ] NATA test report — Thermal conductivity (ref: _____)
- [ ] NATA test report — Sound insulation (ref: _____)
- [ ] Structural engineer certificate
- [ ] BIM model (.ifc)
- [ ] Production G-code (ref: _____)
- [ ] Print QA log (ref: _____)
- [ ] Certifier pre-print inspection report

---

## Section 8 — Version history

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | [date] | Initial template | — |
