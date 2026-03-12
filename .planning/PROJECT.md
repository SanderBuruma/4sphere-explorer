# 4-Sphere Explorer

## What This Is

An interactive Pygame application for exploring the surface of a 4-dimensional sphere (S3). Users navigate 30,000 uniformly distributed points on S3 via tangent space projection, with slerp-based travel, procedural audio, spatial indexing, bookmarks, search, visual effects, and a detail panel. A solo developer project for visualizing and experiencing higher-dimensional geometry.

## Core Value

Navigable, intuitive traversal of S3 -- making 4D geometry feel tangible through direct interaction rather than static visualization.

## Requirements

### Validated

- v1.0: KDTree spatial indexing for sub-linear visibility queries
- v1.0: Bookmark save/load/restore for revisiting locations
- v1.0: Real-time name search with instant prefix filtering
- v1.0: Tab auto-travel to nearest unvisited visible point
- v1.0: Distance-based glow halos on points
- v1.0: Animated parallax starfield background
- v1.0: Animated travel line to target during movement
- v1.0: Breadcrumb trail of visited points as fading dots
- v1.0: Click-hold radial menu with detail panel (4D coords, name, distance, audio params)
- v1.0: Exploration statistics overlay (visited count, distance, session time)
- existing: 30,000 uniformly distributed points with deterministic naming and coloring
- existing: Tangent space projection with persistent orientation frame (WASD/QE + mouse drag)
- existing: Slerp travel with click-to-travel, travel queue, and snap-on-arrival
- existing: Scrollable distance-sorted point list with hover tooltips
- existing: Two view modes (assigned color vs 4D position-derived color)
- existing: Procedural techno ambient music with 2.1M+ configurations
- existing: Lazy identicon/name generation with LRU eviction
- existing: Planet sprites (10 types, hash-based per point)
- v1.2: Corner compass widget with 4D orientation (compass rose, Y tilt bar, W depth gauge)
- v1.2: Compass rose for X/Z axes with animated Lerp needle
- v1.2: Vertical tilt bar for Y axis
- v1.2: W depth gauge with color interpolation
- v1.2: Compass hidden when Gamepedia overlay is open
- v1.2: Compass visible only in view mode 0 (Assigned colors)

### Active

(None — next milestone not yet defined)

### Out of Scope

- Multiplayer / networking -- solo exploration experience
- 3D rendering engine (OpenGL/Vulkan) -- Pygame 2D projection is the chosen approach
- VR support -- desktop-first
- Custom point placement -- random distribution is core

## Context

- **Inspiration:** YouTube transcript on high-dimensional geometry (sphere volume formulas, S3 properties, SU(2)/quaternion connections)
- **Tech stack:** Python + Pygame + NumPy, standard venv
- **Mathematical foundation:** Unit vectors in R4, 4x4 orthogonal orientation frame, Gram-Schmidt reorthogonalization, slerp interpolation, KDTree spatial index
- **Current state:** v1.2 shipped -- compass widget with conditional rendering
- **Codebase:** ~7,500 LOC Python across main.py, sphere.py, audio.py, lib/*.py, tests/

## Constraints

- **Tech stack**: Python/Pygame/NumPy -- established, no migration
- **Performance**: Must handle 30,000 points with smooth frame rate on standard hardware
- **Math correctness**: 4D rotation math must be numerically stable (drift correction via Gram-Schmidt)
- **Audio**: Procedural synthesis only, no external audio files

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Persistent orientation frame over per-frame Gram-Schmidt | Prevents direction flipping when camera moves away from standard basis axes | Good |
| Tangent space projection over stereographic | More intuitive for navigation -- points cluster around crosshair | Good |
| 30k points with lazy caching | Balance between density and performance; LRU eviction keeps memory bounded | Good |
| Procedural audio over samples | Unique soundscape per point (2.1M+ configs), no file dependencies | Good |
| Narrow FOV (0.116 rad) with high projection scale (2500) | Shows ~10 visible points at once, feels like exploring a vast space | Good |
| KDTree + angular filter for visibility | Sub-linear 4D spatial prune via Euclidean radius, then strict dot-product FOV cone | Good |
| Prefix match for search | Fast and predictable with small visible set (~10 points) | Good |
| Click-hold radial menu for interactions | Non-intrusive, discoverable, extensible context menu | Good |
| Compass: atan2(-z,x) heading, arccos(abs(y)) tilt, dot(w) depth | Natural mapping: XZ=floor, Y=tilt, W=4th dim; fixed standard basis reference | Good |
| Compass: 200ms Lerp with shortest-path wraparound | Responsive feel, prevents needle spinning past ±pi boundary | Good |
| Compass: render before gamepedia block | Z-order means overlay naturally covers widget, no explicit guard yet | Good |

## Shipped Milestones

- **v1.0 Explorer MVP** — KDTree, bookmarks, search, visual effects, radial menu
- **v1.1 Gameplay Prototype** — Traits, reputation, dialogue, persistence
- **v1.2 4S Compass** — 4D orientation compass widget with conditional rendering

---
*Last updated: 2026-03-12 after v1.2 milestone*
