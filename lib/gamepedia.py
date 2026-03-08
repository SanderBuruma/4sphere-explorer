"""Gamepedia content, layout constants, and word-wrap utility."""

# Layout constants (shared between click handling and rendering)
GP_LEFT_X = 40
GP_LEFT_W = 280
GP_TOP_Y = 56
GP_LINE_H = 24

GAMEPEDIA_CONTENT = [
    ("Controls", [
        ("Keyboard", """\
WASD  Rotate your view up/down/left/right
Q/E   Rotate along the 4th axis (the "depth" you can't normally see)
V     Switch coloring mode (4 modes — see View Modes)
Tab   Jump to the closest unvisited point
/ F   Open the name search bar
F1    Open/close this screen
Ctrl +/-  Zoom in XYZ projection modes"""),
        ("Mouse", """\
Click a point in the viewport to fly there. Hold-click to open the \
radial menu instead.

Click a name in the sidebar to fly to that point.

Drag anywhere in the viewport to rotate your view freely.

Mouse wheel zooms when in XYZ projection modes (2 and 3)."""),
        ("View Modes", """\
Press V to cycle through four coloring modes:

Assigned: Every point keeps one random color forever. Good for \
recognizing individual points at a glance.

4D Position: Color is computed from the direction to each point in \
4D space. Nearby points look similar; far-away points look different.

XYZ Projection: Points are plotted by their 3D position relative to \
you. The hidden 4th coordinate (W) becomes a blue-to-white-to-red \
color gradient. Scroll to zoom.

XYZ Fixed-Y: Same as XYZ Projection, but the vertical axis is locked \
to an absolute "up" direction instead of rotating with you."""),
    ]),
    ("Navigation", [
        ("Travel & Slerp", """\
Click any point to travel to it. You don't fly in a straight line — \
you slide along the curved surface of the 4-sphere, following the \
shortest path (a "great circle arc"). This curved motion is called \
slerp (spherical linear interpolation).

When you get close enough (within 0.02 rad), you snap onto the point \
and a blue ring pops outward to confirm arrival.

Your entire view frame travels with you, so the camera smoothly \
rotates as you move. Nothing jumps or flickers."""),
        ("Travel Queue", """\
Already flying somewhere? Click another point to queue it up. You'll \
automatically continue to the queued destination after arriving.

The sidebar marks your current target with < and your queued target \
with << in blue."""),
        ("Auto-Travel (Tab)", """\
Press Tab to auto-travel to the nearest visible point you haven't \
visited yet. If you're mid-flight, it queues instead.

Visited points are tracked for the whole session. The sidebar dims \
points you've already been to, and a trail of fading dots shows your \
recent path through the viewport."""),
        ("Search & Filter", """\
Press / or F to open the search bar at the top of the sidebar. Start \
typing a name and the list filters in real-time (case-insensitive, \
prefix match).

Press Escape to clear the filter and close the search bar. You can \
still scroll the filtered list with UP/DOWN while typing."""),
    ]),
    ("World", [
        ("Points & Names", """\
There are 30,000 points scattered uniformly across the surface of \
the 4-sphere. Each one has a unique name built from syllable chunks — \
a core, an ending, sometimes a suffix or number. The name space holds \
11.8 million possibilities, so every point gets something distinct.

Names are generated from a fixed random seed (42), so they're always \
the same between sessions."""),
        ("Planet Types", """\
Each point is drawn as a tiny planet sprite. There are 10 types:

Earth, Mars, Jupiter, Frost, Inferno, Desert, Jungle, Methane, \
Saturn, and Void.

Which type a point gets is determined by a hash of its index — always \
the same point, always the same planet. The detail panel (hold-click \
> Info) shows a bigger version with a random rotation and mirror flip \
unique to that point."""),
        ("Colors & View Modes", """\
In Assigned mode every point picks a random HSV color at startup and \
keeps it forever. In 4D Position mode, the color is computed from the \
relative direction vector in 4D — similar directions get similar hues.

In the two XYZ modes, the 4th coordinate (W) maps to a gradient: \
blue for negative W, white near zero, red for positive.

Whichever mode you're in, the sidebar, tooltip, and detail panel all \
use the exact same color as the viewport dot."""),
        ("Identicons", """\
Every point has a small pixel-art avatar (identicon) generated from \
its name hash. You'll see it in the sidebar next to each name, in \
hover tooltips, and at large size in the detail panel.

They also have googly eyes that follow your mouse cursor."""),
    ]),
    ("Audio", [
        ("Procedural Music", """\
Every point emits its own ambient sound — a 15-second looping \
soundscape generated entirely from its name key. No two points sound \
the same. There are over 2 million possible combinations of timbre, \
scale, root note, and tempo.

You can only hear points within 10 mrad of your position. Volume \
fades linearly as you move away, so traveling through a cluster of \
points creates a shifting mix."""),
        ("Timbres & Scales", """\
Each point's sound picks one of 10 timbres: supersaw pad, acid bass, \
synth pluck, FM bass, noise drone, ring modulation, pulse-width \
modulation, organ, wavefold, or stutter.

The melody follows one of 12 scales (pentatonic, dorian, blues, \
harmonic minor, etc.) with a root note anywhere from a deep 33 Hz \
rumble up to a bright 466 Hz tone. Tempo ranges from a slow drone \
(5 seconds per note) to rapid pulses (0.08 seconds)."""),
        ("Spatial Mixing", """\
As you fly around, sounds crossfade naturally — nearby points get \
louder, distant ones disappear. Each loop crossfades its own start \
and end so there's no click or gap.

High harmonics roll off above 580 Hz to keep everything warm and \
blendable. All loops are volume-normalized so no single point blasts \
over the others."""),
    ]),
    ("4D Geometry", [
        ("What is S3?", """\
S3 is the "3-sphere" — the 4D equivalent of a regular sphere. Just \
as a normal sphere (S2) is the set of all points at distance 1 from \
the center in 3D space, S3 is the set of all points at distance 1 \
from the center in 4D space:

  x*x + y*y + z*z + w*w = 1

It's a closed, finite 3D space with no edges or boundaries. If you \
travel in any direction long enough, you come back to where you started \
— like walking around the Earth, but in one more dimension.

S3 shows up in physics (quaternion rotations, particle spin states) \
and topology. This explorer lets you actually walk around on it."""),
        ("Tangent Space Projection", """\
You can't see 4D directly, so the game projects everything onto a \
flat screen. Here's how:

At your position on S3, there's a 3D "tangent plane" — the flat space \
that just barely touches the sphere at that point (like a table \
touching a basketball). The camera uses three perpendicular direction \
vectors in this tangent plane as its local X/Y/Z axes.

Nearby points get projected onto these axes, giving 3D coordinates \
that get drawn on screen. Points farther away in angular distance \
appear smaller and dimmer — like depth fog, but on a curved surface."""),
        ("Orientation Frame", """\
Your camera state is stored as four 4D vectors bundled into a matrix:

Row 0: your position on S3 (a unit vector in 4D).
Rows 1-3: three perpendicular directions in the tangent plane (your \
local right, up, and "into the screen" axes).

When you press WASD or QE, the game rotates your position and one \
of these axes together in a 2D plane — that's how you turn without \
leaving the sphere's surface.

After each rotation, Gram-Schmidt correction keeps all four vectors \
exactly perpendicular and unit-length, preventing drift from piling \
up over thousands of frames."""),
    ]),
    ("UI", [
        ("Sidebar", """\
The right panel lists every visible point, sorted nearest-first. Each \
row shows the point's identicon, name, and distance (in milliradians \
for close points, radians for far ones).

Scroll with UP/DOWN. Click any row to fly there. Already-visited \
points appear dimmed. The header shows how many points are visible \
and how many you've visited this session."""),
        ("Tooltip", """\
Hover your mouse over any point in the viewport to see a floating \
tooltip with the point's identicon, name, and distance. The border \
color matches the point's display color in the current view mode.

Hovering a name in the sidebar highlights the matching point in the \
viewport with a white circle outline."""),
        ("Detail Panel & Radial Menu", """\
Hold-click (don't release immediately) on a point to pop open a \
radial menu. Move to the "Info" wedge and release to open the detail \
panel.

The panel shows a large planet sprite and identicon, the point's \
name, exact distance, full 4D coordinates (x, y, z, w), and its \
audio parameters: which timbre and scale it uses, root frequency, \
and tempo.

Click anywhere else to dismiss the panel."""),
    ]),
]

# Flatten topics for indexed access: list of (group_name, title, text)
_gamepedia_flat = []
for _gname, _topics in GAMEPEDIA_CONTENT:
    for _title, _text in _topics:
        _gamepedia_flat.append((_gname, _title, _text))


def word_wrap_text(text, max_width, render_font):
    """Split text into lines that fit within max_width pixels."""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(" ")
        current = words[0]
        for word in words[1:]:
            test = current + " " + word
            if render_font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines
