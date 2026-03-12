# Research Summary: 4D Compass Widget for 4-Sphere Explorer

**Project:** 4-Sphere Explorer (Pygame-based S³ navigation)
**Milestone:** v1.2 (Adding 4D orientation compass widget)
**Researched:** 2026-03-12
**Overall Confidence:** MEDIUM-HIGH (math principles are high-confidence; 4D-specific UX patterns are lower confidence)

---

## Executive Summary

A 4D compass widget must display the player's orientation relative to **fixed standard basis axes** (X, Y, Z, W), not relative to the player's own orientation frame. This is the critical distinction that makes it a compass (absolute reference) rather than a gyroscope (relative indicator).

The main technical challenges are:

1. **Math correctness:** Computing compass output requires careful projection of 4D basis axes into 3D tangent space, with special handling for the W axis (which doesn't fit naturally into a 2D display).
2. **Numerical stability:** The player's orientation frame undergoes Gram-Schmidt reorthogonalization to correct drift; the compass must use *exact* basis axis vectors, never reorthogonalized versions.
3. **Visual clarity:** Displaying 4D orientation in a small corner widget requires hierarchical design (primary 2D compass for X/Z, secondary indicators for Y and W) to avoid clutter.
4. **Performance:** Per-frame compass computation must stay under 0.2ms to maintain 60 FPS with the existing 30k-point render pipeline.

**Recommended minimum implementation:**
- Compass rose showing X/Z axes (horizontal plane) with cardinal directions
- Vertical bar for Y axis alignment
- Separate W-axis indicator (color gradient or glow) to show depth orientation
- No animations; clear text labels; standard RGB axis colors
- Unit tests validating invariant: "compass output doesn't change when player rotates in place"

---

## Key Findings

### Stack: No new dependencies required
- **Math:** NumPy (existing) for vectorized dot products and normalization
- **Graphics:** pygame.draw (existing) for 2D shapes
- **No C extensions, GPU, or external libraries needed**

### Architecture: Two distinct reference frames
```
orientation[0]     = player's camera direction
orientation[1:4]   = player's local tangent basis (changes with player rotation)

STANDARD_BASIS = [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]
                = fixed absolute 4D axes (NEVER changes)

Compass computation:
  1. Take each standard axis (e.g., [1,0,0,0])
  2. Compute dot products with player's frame to get relative alignment
  3. Render based on these alignments
  4. Never project standard axes through player frame
```

### Features: Minimal viable compass
| Feature | Priority | Implementation |
|---------|----------|-----------------|
| X/Z horizontal compass rose | MVP | 4-direction rose (E/W/F/B labels) in 2D screen space |
| Y vertical indicator | MVP | Up/down bar showing Y-axis alignment |
| W depth indicator | MVP | Color gradient (blue -W, red +W) or separate glow |
| Cardinal direction labels | MVP | Text: "E" for +X, "W" for -X, "F" for +Z, "B" for -Z |
| Standard RGB colors | MVP | Red=X, Green=Y, Blue=Z, Cyan=W |
| Edge case handling | MVP | Graceful fallback when camera aligns with axes (NaN safety) |
| Animation | Deferred | No real-time needle rotation; static widget |
| Perspective shift | Deferred | No viewcube-style 3D rotation; 2D only |

### Pitfalls: 7 critical, 3 moderate, 1 minor
See PITFALLS_COMPASS.md for detailed analysis. Top three:

1. **Basis vector misalignment** (CRITICAL) — Using player frame as reference instead of fixed axes → compass rotates with player
2. **W-axis tangent space collapse** (CRITICAL) — W-axis invisible in 3D tangent space projection → need separate display
3. **Numerical drift cascade** (CRITICAL) — Reorthogonalization of player frame affecting compass → slow creep over 30+ minute sessions

Prevention: Never reorthogonalize compass axes. Use exact `[1,0,0,0]` vectors. Test invariant before rendering.

---

## Implications for Roadmap

### Recommended Phase Structure

**Phase 1: Math & Design (2-3 days)**
- [ ] Define compass coordinate system and reference frame (fixed axes, not player frame)
- [ ] Design W-axis visualization (choose one: color, slider, glow, separate gauge)
- [ ] Create visual wireframe/mockup of compass layout
- [ ] Write unit tests for math invariants:
  - `test_compass_invariant_under_rotation()` — compass output unchanged when player spins
  - `test_w_axis_responds_to_qe()` — W indicator changes with Q/E key presses
  - `test_edge_case_axis_alignment()` — compass sensible when camera aligned with X/Y/Z/W
- [ ] Get feedback on clarity from co-worker or early tester

**Phase 2: Implementation (3-4 days)**
- [ ] Implement compass projection math (vectorized NumPy)
- [ ] Implement compass rendering (pygame.draw shapes + text)
- [ ] Add performance profiling; verify <0.2ms overhead
- [ ] Test edge cases and numerical stability
- [ ] Verify color scheme matches standards (Red=X, Green=Y, Blue=Z, Cyan=W)
- [ ] Ensure cache invalidation after frame rotations
- [ ] Code review focusing on math correctness

**Phase 3: Testing & Integration (2 days)**
- [ ] Playtesting: new player feedback on compass clarity
- [ ] Long-session testing: 30+ minutes, verify no numerical drift
- [ ] Integration with existing UI (check for visual clutter, color conflicts)
- [ ] Accessibility: test with colorblind simulation
- [ ] Polish and iterate based on feedback

### Estimated Effort
- **Math & Unit Tests:** 8-10 hours
- **Implementation & Profiling:** 10-12 hours
- **Testing & Iteration:** 6-8 hours
- **Total:** 24-30 hours (3-4 days full-time equivalent)

### Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|-----------|
| W-axis visualization unclear | MEDIUM | Prototype 2-3 options in Phase 1; get feedback before committing |
| Performance regression | MEDIUM | Profile early; vectorize computation; test on target hardware |
| Numerical drift over time | MEDIUM | Test for 30+ minutes; compare compass to analytical frame state |
| Coordinate system confusion | MEDIUM | Use standard RGB colors + clear text labels; document in F1 help |
| Gimbal-lock-like singularities | LOW | Edge cases rare; add explicit handling; test all 4 axis alignments |

### Validation Checklist (Phase 3 exit criteria)
- [ ] Compass reads fixed standard axes, not player frame (test: player rotates, compass unchanged)
- [ ] W-axis visualization updates with Q/E input (test: press Q/E, watch W indicator change)
- [ ] Performance <0.2ms overhead per frame (test: profile with compass on/off)
- [ ] No numerical drift after 30+ minutes (test: long session, verify compass stable)
- [ ] Clear visual hierarchy: primary 2D rose, secondary Y bar, tertiary W gauge
- [ ] Standard RGB colors used (Red=X, Green=Y, Blue=Z, Cyan=W)
- [ ] Text labels clear ("E" for +X, "Y" for +Y, etc.)
- [ ] Edge cases handled (camera aligned with axis, NaN/inf safe)
- [ ] Player feedback: "Compass helps me understand my 4D orientation" (>80% yes)

---

## Research Gaps

1. **Best practice for W-axis visualization in 4D UIs:** Literature sparse. Phase 1 prototyping with player feedback essential.
2. **Performance baseline for compass in pygame:** No existing benchmark. Phase 2 profiling will establish baseline.
3. **Long-session numerical stability:** No 30+ minute test yet. Phase 3 validation required.
4. **Colorblind accessibility:** Not tested yet. Phase 3 should include colorblind simulation test.
5. **Player preference for orientation reference:** No UX research. Early playtesting feedback crucial.

---

## Next Steps

1. **Immediately (Pre-Phase 1):**
   - Confirm scope: Is compass essential to gameplay, or nice-to-have?
   - Get rough consensus on W-axis visualization (color? slider? glow?)
   - Reserve 3-4 days for v1.2 milestone

2. **Phase 1 (Design):**
   - Define fixed vs. player frame explicitly in code comments
   - Create visual mockup (even on paper is fine)
   - Write math unit tests before implementation
   - Get feedback from player(s)

3. **Phase 2 (Implementation):**
   - Build compass using findings from research
   - Profile early; fix performance issues before polish
   - Test edge cases thoroughly

4. **Phase 3 (Validation):**
   - Playtesting; iterate based on feedback
   - Long-session testing for numerical stability
   - Polish and release

---

## Confidence Assessment

| Area | Level | Justification |
|------|-------|---------------|
| **Stack** | HIGH | No new dependencies; uses existing NumPy + pygame + codebase patterns |
| **Math correctness** | MEDIUM-HIGH | 4D projection principles sound; implementation requires careful testing |
| **Architecture** | HIGH | Clear separation of fixed axes (constant) from player frame (variable) |
| **Pitfalls** | MEDIUM | Identified from codebase analysis + 4D visualization theory; severity depends on implementation |
| **UX/Visual design** | MEDIUM | General widget design well-understood; 4D-specific visualization is newer (needs playtesting) |
| **Performance** | MEDIUM-HIGH | pygame overhead predictable; profiling will validate |
| **Numerical stability** | MEDIUM | Gram-Schmidt reorthogonalization is standard; interaction with compass needs testing |

---

## Sources & References

- **Codebase:**
  - `sphere.py`: `rotate_frame()`, `reorthogonalize_frame()`, `tangent_basis()`, `project_to_tangent()`
  - `main.py`: `orientation` frame structure, `update_visible()` render loop
  - `.planning/PROJECT.md`: Compass widget requirements

- **Mathematical references:**
  - [Rotations in 4D - Wikipedia](https://en.wikipedia.org/wiki/Rotations_in_4-dimensional_Euclidean_space)
  - [4D Visualization: Rotations - qfbox.info](https://www.qfbox.info/4d/vis/10-rot-1)
  - [Numerical stability of orthogonalization - Springer](https://link.springer.com/article/10.1007/s10543-012-0398-9)

- **UI/Graphics references:**
  - [ViewCube: 3D orientation indicator - ResearchGate](https://www.researchgate.net/publication/220792070_ViewCube_A_3D_orientation_indicator_and_controller)
  - [Game HUD UI Design - Medium](https://medium.com/design-bootcamp/7-obvious-beginner-mistakes-with-your-games-hud-from-a-ui-ux-art-director-d852e255184a)
  - [Coordinate Systems - O'Reilly](https://www.oreilly.com/library/view/fundamentals-of-data/9781492031079/ch03.html)

---

## Files Created

- **PITFALLS_COMPASS.md** — Detailed pitfall analysis (10 pitfalls: 4 critical, 3 moderate, 3 minor)
- **COMPASS_RESEARCH_SUMMARY.md** — This file; executive summary with roadmap implications

---

*Research completed: 2026-03-12*
*Researched by: Claude Agent (Phase 6: Research)*
*Downstream consumer: Roadmap planning for v1.2 milestone*
