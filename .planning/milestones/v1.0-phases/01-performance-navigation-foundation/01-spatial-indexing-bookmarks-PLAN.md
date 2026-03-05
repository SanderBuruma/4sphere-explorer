---
phase: 01-performance-navigation-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [sphere.py, main.py]
autonomous: true
requirements: [PERF-01, NAV-01]

must_haves:
  truths:
    - "Visibility queries complete sub-linearly without perceptible lag when rotating through dense regions"
    - "User can bookmark current position and see saved positions in a persistent menu"
    - "User can click a bookmark to instantly restore that position and orientation"
  artifacts:
    - path: "sphere.py"
      provides: "KDTree spatial index for 4D points, build/query interface"
      exports: ["build_visibility_kdtree", "query_visible_kdtree"]
    - path: "main.py"
      provides: "Bookmark UI (save/load/restore), persistent state tracking"
      section: "Bookmark system integration (lines ~100-150, ~500-550)"
  key_links:
    - from: "main.py:update_visible()"
      to: "sphere.py:query_visible_kdtree()"
      via: "Replace dot-product scan with KDTree lookup"
      pattern: "visible_points.*camera_pos.*points"
    - from: "main.py:sidebar rendering"
      to: "Bookmark menu section"
      via: "Draw saved bookmarks above point list"
      pattern: "LIST_BG.*LIST_ITEM"
---

<objective>
Implement spatial indexing to replace O(n) visibility scan with sub-linear KDTree queries, and add a persistent bookmark system to save/restore exploration positions.

Purpose: Eliminate O(n) dot-product bottleneck during rotation/dense regions; provide convenient way to mark and return to interesting locations.

Output:
- KDTree spatial index for fast visibility queries (sphere.py)
- Bookmark save/load/restore UI with persistent state (main.py)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Current visibility implementation (O(n) dot product scan):
```python
# sphere.py:114-120
def visible_points(camera_pos, points, fov_angle=np.pi / 2):
    """Filter points visible from camera position within FOV angle."""
    dots = np.dot(points, camera_pos)
    cos_fov = np.cos(fov_angle)
    visible = dots > cos_fov
    return points[visible], np.where(visible)[0]
```

Current UI integration point in main.py:
```python
# main.py:142-156
def update_visible():
    global visible_indices, visible_distances, point_identicon_cache
    prev_set = set(visible_indices)
    vis_points, indices = visible_points(player_pos, points, FOV_ANGLE)
    distances = [angular_distance(player_pos, points[i]) for i in indices]
    sorted_pairs = sorted(zip(indices, distances), key=lambda x: x[1])
    visible_indices = [p[0] for p in sorted_pairs]
    visible_distances = [p[1] for p in sorted_pairs]
```

Sidebar rendering (main.py:486-524) — bookmark section will be inserted before point list.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build KDTree spatial index and visibility query interface</name>
  <files>sphere.py</files>
  <action>
    Add to sphere.py:

    1. Import scipy.spatial.KDTree at top:
       ```python
       from scipy.spatial import KDTree
       ```

    2. Add module-level function to build the index:
       ```python
       def build_visibility_kdtree(points):
           """Build a KDTree index on points for fast spatial queries.

           Returns KDTree object for use in query_visible_kdtree().
           """
           return KDTree(points)
       ```

    3. Add query function:
       ```python
       def query_visible_kdtree(kdtree, camera_pos, points, fov_angle):
           """Query visible points using KDTree and angular FOV constraint.

           Uses KDTree radius search in 4D space, then filters by dot-product
           (angular distance) to enforce FOV cone. Returns indices and coordinates
           of visible points.

           Args:
               kdtree: Precomputed KDTree(points)
               camera_pos: Camera position on S³ (unit 4D vector)
               points: Original point array (for filtering, returned visible subset)
               fov_angle: Field-of-view angle in radians

           Returns:
               (visible_points_array, indices_array) matching visible_points() signature
           """
           # FOV constraint: cos(fov_angle) bounds the dot product
           cos_fov = np.cos(fov_angle)

           # Euclidean radius in 4D corresponding to angular FOV
           # For points p on unit sphere with camera c, angular distance θ relates to
           # Euclidean via: ||p - c||² = 2(1 - cos(θ))
           # Max Euclidean distance for visible points:
           max_euclidean = np.sqrt(2 * (1 - cos_fov))

           # Query KDTree for all points within Euclidean radius
           indices = kdtree.query_ball_point(camera_pos, max_euclidean)

           # Filter by angular FOV constraint (dot product > cos_fov)
           dots = np.dot(points[indices], camera_pos)
           angular_visible = dots > cos_fov
           filtered_indices = np.array(indices)[angular_visible]

           return points[filtered_indices], filtered_indices
       ```

    4. Update visible_points() to remain backward-compatible but note it's O(n):
       Keep existing implementation — it will be called less frequently after integration.

    Design rationale: KDTree.query_ball_point() performs sub-linear spatial pruning
    in 4D, then we apply angular constraint to enforce strict FOV cone. This avoids
    full dot-product scan while remaining mathematically correct for the narrow FOV case.
  </action>
  <verify>
    <automated>
      cd /home/sanderburuma/Projects/4sphere-explorer && \
      python3 -c "
from sphere import build_visibility_kdtree, query_visible_kdtree, random_point_on_s3
import numpy as np

# Test with small point set
points = random_point_on_s3(100)
kdtree = build_visibility_kdtree(points)
camera = points[0]
fov = 0.2

vis_points, indices = query_visible_kdtree(kdtree, camera, points, fov)

# Verify: all returned indices have dot product > cos(fov)
cos_fov = np.cos(fov)
for idx in indices:
    dot = np.dot(points[idx], camera)
    assert dot > cos_fov - 1e-6, f'Index {idx} has dot {dot}, expected > {cos_fov}'

print(f'✓ KDTree query test passed: {len(indices)} visible out of 100')
" 2>&1
    </automated>
  </verify>
  <done>
    - KDTree functions added to sphere.py (build_visibility_kdtree, query_visible_kdtree)
    - Functions accept same interface as existing visible_points() for drop-in replacement
    - Verified angular constraint correctly filters results
  </done>
</task>

<task type="auto">
  <name>Task 2: Integrate KDTree into main loop and refactor update_visible()</name>
  <files>main.py</files>
  <action>
    1. Add imports at top of main.py (after existing sphere imports):
       ```python
       from sphere import (
           # ... existing imports ...
           build_visibility_kdtree,
           query_visible_kdtree,
       )
       ```

    2. After `points = random_point_on_s3(NUM_POINTS)` (line ~89), build the index:
       ```python
       # Build spatial index for fast visibility queries
       visibility_kdtree = build_visibility_kdtree(points)
       ```

    3. Refactor `update_visible()` (lines 142-156) to use KDTree:
       ```python
       def update_visible():
           global visible_indices, visible_distances, point_identicon_cache
           prev_set = set(visible_indices)

           # Use KDTree for sub-linear visibility query
           vis_points, indices = query_visible_kdtree(visibility_kdtree, player_pos, points, FOV_ANGLE)
           distances = [angular_distance(player_pos, points[i]) for i in indices]
           sorted_pairs = sorted(zip(indices, distances), key=lambda x: x[1])
           visible_indices = [p[0] for p in sorted_pairs]
           visible_distances = [p[1] for p in sorted_pairs]

           # Evict caches for points no longer visible
           new_set = set(visible_indices)
           for idx in prev_set - new_set:
               point_identicon_cache.pop(idx, None)
               point_name_cache.pop(idx, None)
       ```

    This is a drop-in replacement — rest of update_visible() logic (distance sorting, cache eviction) remains unchanged.
  </action>
  <verify>
    <automated>
      cd /home/sanderburuma/Projects/4sphere-explorer && \
      python3 venv/bin/python -c "
import pygame
pygame.mixer.pre_init(44100, -16, 2)
pygame.init()

# Import to check syntax
from main import update_visible

# Run one update to verify it executes without error
update_visible()

print('✓ update_visible() integrates KDTree successfully')
" 2>&1 | head -20
    </automated>
  </verify>
  <done>
    - KDTree imported and built after point generation
    - update_visible() refactored to use query_visible_kdtree()
    - Visibility filtering now sub-linear instead of O(n)
    - Cache eviction logic preserved
  </done>
</task>

<task type="auto">
  <name>Task 3: Implement bookmark save/load/restore system</name>
  <files>main.py</files>
  <action>
    1. Add bookmark state after game state initialization (around line ~130):
       ```python
       # Bookmark system: list of (player_pos, orientation, name) tuples
       bookmarks = []  # [(pos, frame, name), ...]

       def save_bookmark(name_str=None):
           """Save current position and orientation as a bookmark."""
           global bookmarks
           if name_str is None:
               # Auto-generate bookmark name from current position index
               name_str = f"Bookmark {len(bookmarks) + 1}"
           bookmark = (player_pos.copy(), orientation.copy(), name_str)
           bookmarks.append(bookmark)
           print(f"Saved bookmark: {name_str}")

       def restore_bookmark(bookmark_idx):
           """Restore player position and orientation from a saved bookmark."""
           global player_pos, orientation, camera_pos, traveling, travel_target
           if 0 <= bookmark_idx < len(bookmarks):
               pos, frame, name = bookmarks[bookmark_idx]
               player_pos = pos.copy()
               orientation = frame.copy()
               camera_pos = orientation[0]
               # Cancel any in-progress travel when jumping to bookmark
               traveling = False
               travel_target = None
               travel_target_idx = None
               update_visible()
               print(f"Restored bookmark: {name}")
       ```

    2. Add keyboard bindings for bookmark actions (in event loop, around line ~208):
       In the `elif event.type == pygame.KEYDOWN:` block, add:
       ```python
       elif event.key == pygame.K_b:
           # B key: save bookmark
           save_bookmark()
       elif event.key == pygame.K_1:
           # Number keys 1-5: restore bookmark 0-4
           restore_bookmark(0)
       elif event.key == pygame.K_2:
           restore_bookmark(1)
       elif event.key == pygame.K_3:
           restore_bookmark(2)
       elif event.key == pygame.K_4:
           restore_bookmark(3)
       elif event.key == pygame.K_5:
           restore_bookmark(4)
       ```
       (Or use a loop: for key, idx in zip([K_1, K_2, K_3, K_4, K_5], range(5)))

    3. Update UI sidebar to show bookmarks (in render loop, around line ~500):
       In the sidebar rendering section, before the point list header, add:
       ```python
       # Render bookmark section header
       bookmark_y = 100
       pygame.draw.line(screen, TEXT_COLOR, (SCREEN_WIDTH - 300, bookmark_y), (SCREEN_WIDTH, bookmark_y))
       bookmark_label = font.render("BOOKMARKS (B/1-5)", True, TEXT_COLOR)
       screen.blit(bookmark_label, (SCREEN_WIDTH - 290, bookmark_y + 5))

       bookmark_y += 30
       for i, (_, _, bm_name) in enumerate(bookmarks[:5]):
           bm_rect = pygame.Rect(SCREEN_WIDTH - 290, bookmark_y, 280, 25)
           pygame.draw.rect(screen, LIST_ITEM_BG, bm_rect)
           bm_text = font.render(f"{i+1}: {bm_name}", True, TEXT_COLOR)
           screen.blit(bm_text, (SCREEN_WIDTH - 280, bookmark_y + 5))
           bookmark_y += 28

       # Divider before point list
       pygame.draw.line(screen, TEXT_COLOR, (SCREEN_WIDTH - 300, bookmark_y + 5), (SCREEN_WIDTH, bookmark_y + 5))
       list_header_y = bookmark_y + 15
       ```

       Adjust the list header and items to start at `list_header_y` instead of hardcoded 100.
       Update point list rendering loop to account for offset from bookmarks section.

    Design rationale: Bookmarks store full position + orientation frame for deterministic restore.
    B key saves, number keys 1-5 restore. UI shows up to 5 recent bookmarks in sidebar.
  </action>
  <verify>
    <automated>
      cd /home/sanderburuma/Projects/4sphere-explorer && \
      timeout 5 python3 venv/bin/python -c "
import pygame
import numpy as np
pygame.mixer.pre_init(44100, -16, 2)
pygame.init()
pygame.display.set_mode((1200, 800))

# Minimal main.py import check
exec(open('main.py').read().replace('while running:', 'running = False; pass #'))
print('✓ Bookmark system syntax valid')
" 2>&1 | grep -E "(✓|Error)" | head -5
    </automated>
  </verify>
  <done>
    - Bookmark save/load functions implemented
    - B key binding saves bookmark with auto-name
    - Number keys 1-5 restore first 5 bookmarks
    - UI section displays saved bookmarks above point list
    - Restoring bookmark cancels in-progress travel and updates view
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:

1. **Spatial indexing reduces frame time:** Measure FPS during heavy rotation (Q/E keys) before/after. Expected: no perceptible lag in dense regions.

2. **Bookmarks persist during session:**
   - Press B to save bookmark
   - Rotate to a different location
   - Press 1 to restore — should snap back to exact position/orientation

3. **Integration test:** Run main.py, confirm:
   - Can rotate smoothly without visible frame drops
   - Point list updates as expected
   - Bookmarks appear in sidebar
   - Bookmark restore works instantly
</verification>

<success_criteria>
- KDTree spatial index built at startup from 30k points
- Visibility queries use query_visible_kdtree() instead of O(n) dot product scan
- update_visible() completes sub-linearly with no perceptible lag during rotation
- Bookmarks save/restore full player position and orientation frame
- Bookmark UI shows in sidebar with B key save, 1-5 key restore bindings
- All 5 bookmarks display correctly in sidebar
- Restoring bookmark snaps player to exact saved state immediately
</success_criteria>

<output>
After completion, create `.planning/phases/01-performance-navigation-foundation/01-SUMMARY.md`
</output>
