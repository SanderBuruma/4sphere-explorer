# Roadmap: 4-Sphere Explorer

## Milestones

- v1.0 Explorer MVP -- Phases 1-3 (shipped 2026-03-05)
- v1.1 Gameplay Prototype -- Phases 4-6 (shipped 2026-03-11)
- v1.2 4S Compass -- Phases 7-8 (active)

## Phases

### v1.2 4S Compass (Phases 7-8)

- [x] **Phase 7: Compass Widget** - Build and render the full 4D orientation widget (compass rose, Y bar, W gauge) (completed 2026-03-12)
- [ ] **Phase 8: Game Integration** - Wire conditional rendering into game state (Gamepedia interop, view mode gate)

## Phase Details

### Phase 7: Compass Widget
**Goal**: Players can see their 4D orientation at a glance via a corner widget with all three indicators
**Depends on**: Nothing (self-contained new module)
**Requirements**: COMP-01, COMP-02, COMP-03, ORIE-01, ORIE-02, WIDG-01
**Success Criteria** (what must be TRUE):
  1. A compass rose in the corner shows X+, X-, Z+, Z- labels positioned correctly relative to fixed standard basis axes
  2. The needle rotates smoothly (Lerp ~200ms) to indicate camera heading in the XZ plane, with correct wraparound at 0/360 degrees
  3. A vertical bar alongside the compass reflects camera tilt relative to the Y axis, moving up/down as the player pitches
  4. A W depth gauge (color gradient or indicator) responds visibly when the player rotates with Q/E keys
  5. The widget has a semi-transparent background that does not obscure points or UI behind it
**Plans**: 2 plans

Plans:
- [ ] 07-01-PLAN.md -- Create lib/compass.py with angle calculations, Lerp animation, and render_compass()
- [ ] 07-02-PLAN.md -- Wire render_compass into main.py render loop and add Gamepedia Compass entry

### Phase 8: Game Integration
**Goal**: The compass respects game state -- hidden when it would conflict, visible only in the appropriate view mode
**Depends on**: Phase 7
**Requirements**: WIDG-02, WIDG-03
**Success Criteria** (what must be TRUE):
  1. Opening the Gamepedia overlay (F1) causes the compass to disappear; closing it makes the compass reappear
  2. Cycling view modes with V shows the compass only in mode 0 (Assigned colors); switching to modes 1-3 hides it
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 7. Compass Widget | 2/2 | Complete   | 2026-03-12 |
| 8. Game Integration | 0/? | Not started | - |

---

<details>
<summary>v1.1 Gameplay Prototype (Phases 4-6) -- SHIPPED 2026-03-11</summary>

- [x] Phase 4: Trait System (2/2 plans) -- completed
- [x] Phase 5: Reputation & Dialogue (3/3 plans) -- completed 2026-03-11
- [x] Phase 6: Persistence (1/1 plans) -- completed 2026-03-11

</details>

<details>
<summary>v1.0 Explorer MVP (Phases 1-3) -- SHIPPED 2026-03-05</summary>

- [x] Phase 1: Performance & Navigation Foundation (3/3 plans) -- completed 2026-03-05
- [x] Phase 2: Visual Polish & Immersion (4/4 plans) -- completed 2026-03-05
- [x] Phase 3: Information & Context (2/2 plans) -- completed 2026-03-05

</details>
