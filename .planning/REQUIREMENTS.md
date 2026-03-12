# Requirements: 4-Sphere Explorer v1.2

**Defined:** 2026-03-12
**Core Value:** Navigable, intuitive traversal of S3 -- making 4D geometry feel tangible

## v1.2 Requirements

### Compass Rose

- [x] **COMP-01**: Compass rose in screen corner shows X+, X-, Z+, Z- cardinal labels relative to fixed standard basis axes
- [x] **COMP-02**: Rotating needle indicates camera's heading direction in the XZ plane
- [x] **COMP-03**: Needle rotation uses smooth Lerp animation (~200ms) with angle wraparound handling

### Orientation Indicators

- [x] **ORIE-01**: Vertical bar alongside compass shows camera tilt relative to the Y axis
- [x] **ORIE-02**: Depth gauge shows camera alignment with the W axis (color gradient or small indicator)

### Widget Integration

- [x] **WIDG-01**: Compass widget has semi-transparent background that doesn't obscure the view
- [x] **WIDG-02**: Compass hidden when Gamepedia overlay is open
- [x] **WIDG-03**: Compass renders only in default view mode (mode 0)

## Future Requirements

### Compass Enhancements

- **COMP-04**: 8-point compass rose with intercardinal directions
- **COMP-05**: Numeric heading/angle readouts
- **WIDG-04**: Toggle compass visibility with C key
- **WIDG-05**: Compass resizes with zoom level

## Out of Scope

| Feature | Reason |
|---------|--------|
| Travel target indicator on compass | Separate feature; compass is orientation-only |
| Nearby planet radar pips | Different UI element; not a compass |
| Compass in non-default view modes | Other view modes have their own visual indicators |
| Full overlay / sphere projection | Scope creep; corner widget is the chosen form |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-01 | Phase 7 | Complete |
| COMP-02 | Phase 7 | Complete |
| COMP-03 | Phase 7 | Complete |
| ORIE-01 | Phase 7 | Complete |
| ORIE-02 | Phase 7 | Complete |
| WIDG-01 | Phase 7 | Complete |
| WIDG-02 | Phase 8 | Complete |
| WIDG-03 | Phase 8 | Complete |

**Coverage:**
- v1.2 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 after roadmap creation*
