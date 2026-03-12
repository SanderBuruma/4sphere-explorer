# Plan 03: UI Integration — Talk Wedge & Dialogue Display

**Phase:** 5 — Reputation & Dialogue
**Requirements:** DIAL-01, DIAL-02, REP-02, REP-03
**Goal:** Player can trigger dialogue via radial menu, see speech bubbles, and observe reputation-driven behavior changes in the UI

---

## Tasks

### 1. Activate "Talk" wedge in radial menu (`main.py`)

Currently: wedge labels are `["Info", "A", "B", "C"]`, only wedge 0 (Info/right) is active.

Change:
- Rename wedge 3 (top position) to "Talk"
- Give it an active color: `(255, 200, 100)` (warm yellow)
- On release in Talk wedge: trigger dialogue generation and display

```python
wedge_labels = ["Info", "A", "B", "Talk"]
wedge_colors = [(100, 200, 255), (100, 100, 120), (100, 100, 120), (255, 200, 100)]
```

In the wedge release handler (line ~385):
```python
elif wedge == 3:  # Talk wedge (top)
    talk_target_idx = menu_point_idx
    # Generate dialogue
    traits = generate_traits(int(_name_keys[talk_target_idx]))
    rep = get_reputation(reputation_store, talk_target_idx)
    record_talk(reputation_store, talk_target_idx)
    dialogue_text = generate_dialogue(int(_name_keys[talk_target_idx]), traits, rep["score"])
    dialogue_show_time = pygame.time.get_ticks()
    dialogue_point_idx = talk_target_idx
```

### 2. Add dialogue display state variables

```python
dialogue_text = None         # Current dialogue string or None
dialogue_show_time = None    # Tick when dialogue was triggered
dialogue_point_idx = None    # Point index the dialogue is for
DIALOGUE_DURATION = 5000     # ms before dialogue fades
DIALOGUE_FADE = 1000         # ms fade-out duration
```

### 3. Render speech bubble near creature

In the rendering section (after detail panel, before divider):

1. If `dialogue_text` is not None and within display duration:
   - Find screen position of `dialogue_point_idx` from `last_projected_points`
   - Draw semi-transparent rounded rect above the creature
   - Render dialogue text with word-wrap (reuse `word_wrap_text` from gamepedia)
   - Opacity fades during last `DIALOGUE_FADE` ms
   - If creature is off-screen: show centered overlay instead

2. Clear dialogue after `DIALOGUE_DURATION + DIALOGUE_FADE` ms

**Speech bubble style:**
- Background: `(30, 30, 50, 180)` with 4px border radius
- Border: creature's point color at 50% alpha
- Text: `TEXT_COLOR` (200, 200, 200)
- Max width: 250px, word-wrapped
- Small triangle pointer toward creature position

### 4. Add dialogue-on-arrival option

When the player arrives at a creature (travel completion), automatically show a brief greeting if:
- This is the first visit (reputation score was 0 before arrival)
- Use the stranger-tier dialogue

This gives passive feedback without requiring manual Talk interaction. The Talk wedge is for deeper/repeated conversations.

Implementation: in the travel completion block, after `record_visit`:
```python
if rep_before_visit["visits"] == 0:
    # First meeting — auto-greet
    traits = generate_traits(int(_name_keys[travel_target_idx]))
    dialogue_text = generate_dialogue(int(_name_keys[travel_target_idx]), traits, 0)
    dialogue_show_time = pygame.time.get_ticks()
    dialogue_point_idx = travel_target_idx
```

### 5. Show reputation change feedback

When reputation changes (visit or talk), briefly flash a small `+1` near the reputation display or speech bubble:
- `+1 ★` in gold text, fades over 1 second
- Only shown when score actually changes (not on repeat visits with no effect)

State: `rep_feedback_text`, `rep_feedback_time`, positioned near speech bubble or detail panel.

### 6. Update Gamepedia entries (`lib/gamepedia.py`)

Add new topic under appropriate group:
- **Controls > Mouse**: Update to mention Talk wedge in radial menu
- **New group "Creatures"** or extend existing: Add topics for "Dialogue", "Reputation"
  - Dialogue: explain trait influence, tier differences
  - Reputation: explain score 0-10, tiers, how to increase

Update `tests/test_gamepedia.py` if group/topic counts change.

### 7. Add `DIALOGUE_DURATION` constant to `lib/constants.py`

```python
DIALOGUE_DURATION = 5000  # ms speech bubble display
DIALOGUE_FADE = 1000      # ms fade-out
```

---

## Acceptance Criteria (maps to success criteria)

- [SC-1] Talk wedge in radial menu produces visible dialogue that varies by creature
- [SC-2] First-visit auto-greeting differs from high-reputation Talk dialogue
- [SC-3] Reputation score visible and changes after Talk action
- [SC-4] Tier label changes at defined thresholds (player can observe without inspecting state)
- Gamepedia documents new features

---

## Files Modified

| File | Change |
|------|--------|
| `main.py` | Talk wedge handler, dialogue state, speech bubble rendering, auto-greet on arrival, rep feedback |
| `lib/constants.py` | `DIALOGUE_DURATION`, `DIALOGUE_FADE` constants |
| `lib/gamepedia.py` | New Dialogue + Reputation topics |
| `tests/test_gamepedia.py` | Update topic/group counts |
