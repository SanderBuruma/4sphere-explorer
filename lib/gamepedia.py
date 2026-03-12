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
Tab   Jump to the closest unvisited planet
/ F   Open the name search bar
F1    Open/close this screen
Ctrl +/-  Zoom in/out"""),
        ("Mouse", """\
Click a planet in the viewport to fly there. Hold-click to open the \
radial menu instead.

The radial menu has two active wedges: "Info" (right) opens the detail \
panel, and "Talk" (top) starts a conversation with the creature. Move \
to a wedge and release the mouse button to select it.

Click a name in the sidebar to fly to that planet.

Drag anywhere in the viewport to rotate your view freely.

Mouse wheel zooms in any view mode."""),
        ("View Modes", """\
Press V to cycle through four coloring modes:

Assigned: Every planet keeps one random color forever. Good for \
recognizing individual planets at a glance.

4D Position: Color is computed from the direction to each planet in \
4D space. Nearby planets look similar; far-away planets look different.

XYZ Projection: Planets are plotted by their 3D position relative to \
you. The hidden 4th coordinate (W) becomes a blue-to-white-to-red \
color gradient. Scroll to zoom.

XYZ Fixed-Y: Same as XYZ Projection, but the vertical axis is locked \
to an absolute "up" direction instead of rotating with you."""),
    ]),
    ("Navigation", [
        ("Travel & Slerp", """\
Click any planet to travel to it. You don't fly in a straight line — \
you slide along the curved surface of the 4-sphere, following the \
shortest path (a "great circle arc"). This curved motion is called \
slerp (spherical linear interpolation).

When you get close enough (within 0.02 rad), you snap onto the planet \
and a blue ring pops outward to confirm arrival.

Your entire view frame travels with you, so the camera smoothly \
rotates as you move. Nothing jumps or flickers."""),
        ("Travel Queue", """\
Already flying somewhere? Click another planet to queue it up. You'll \
automatically continue to the queued destination after arriving.

The sidebar marks your current target with < and your queued target \
with << in blue."""),
        ("Auto-Travel (Tab)", """\
Press Tab to auto-travel to the nearest visible planet you haven't \
visited yet. If you're mid-flight, it queues instead.

Visited planets are tracked for the whole session. The sidebar dims \
planets you've already been to, and a trail of fading dots shows your \
recent path through the viewport."""),
        ("Search & Filter", """\
Press / or F to open the search bar at the top of the sidebar. Start \
typing a name and the list filters in real-time (case-insensitive, \
prefix match).

Press Escape to clear the filter and close the search bar. You can \
still scroll the filtered list with UP/DOWN while typing."""),
    ]),
    ("World", [
        ("Planets & Names", """\
There are 30,000 planets scattered uniformly across the surface of \
the 4-sphere. Each one has a unique name built from syllable chunks — \
a core, an ending, sometimes a suffix or number. The name space holds \
11.8 million possibilities, so every planet gets something distinct.

Names are generated from a fixed random seed (42), so they're always \
the same between sessions."""),
        ("Planet Types", """\
Each planet is drawn as a tiny rotating sphere. Surfaces are procedurally \
generated from smooth gradient noise — no two planets look alike. There \
are 12 color palettes (Sunset, Deep Sea, Aurora, Ember, Arctic, etc.) \
and unique noise offsets per planet, producing millions of variations.

Planets spin slowly (one full rotation every 20 seconds) with a \
per-planet phase offset so they're not all synchronized. The detail \
panel (hold-click > Info) shows a larger spinning version."""),
        ("Colors & View Modes", """\
In Assigned mode every planet picks a random HSV color at startup and \
keeps it forever. In 4D Position mode, the color is computed from the \
relative direction vector in 4D — similar directions get similar hues.

In the two XYZ modes, the 4th coordinate (W) maps to a gradient: \
blue for negative W, white near zero, red for positive.

Whichever mode you're in, the sidebar, tooltip, and detail panel all \
use the exact same color as the viewport dot."""),
        ("Creatures", """\
Every planet has a unique creature avatar. You'll see it in the sidebar \
next to each name, in hover tooltips, and at large size in the detail panel.

Each creature has a distinct body shape, appendages (horns, fins, limbs, \
spikes), accent-colored markings, and eyes. No two look alike.

Every creature also has four personality traits (aggressive-passive, \
curious-aloof, friendly-hostile, brave-fearful) that influence how \
they look and what they say when you talk to them."""),
        ("Dialogue", """\
Hold-click a planet and select the "Talk" wedge to have a conversation \
with its creature. Each creature speaks differently based on its \
personality traits and how well it knows you.

Friendly creatures greet you warmly; hostile ones may tell you to leave. \
Curious creatures ask questions about your travels; aloof ones stay \
silent. The creature's bravery and aggression shape their tone and \
word choice.

When you first arrive at a planet, the creature gives a brief greeting \
automatically. Use Talk from the radial menu for deeper conversation.

At high reputation (Devoted tier), creatures share lore about the \
4-sphere's geometry and the nature of S3 space."""),
        ("Reputation", """\
Each creature tracks how well it knows you on a scale from 0 to 10. \
Your reputation increases by visiting and talking.

The five reputation tiers are:
  0        Stranger   -- wary, short responses
  1-2      Acquaintance  -- polite but distant
  3-5      Familiar   -- comfortable, more talkative
  6-8      Friend     -- warm, shares thoughts
  9-10     Devoted    -- deep connection, shares lore

Your first visit to a planet grants +1 reputation. Using the Talk \
wedge grants another +1 per visit (once per visit only). Reputation \
is shown as stars in the detail panel.

A brief "+1" flash appears whenever your reputation increases."""),
    ]),
    ("Audio", [
        ("Procedural Music", """\
Every planet emits its own ambient sound — a 15-second looping \
soundscape generated entirely from its name key. No two planets sound \
the same. There are over 2 million possible combinations of timbre, \
scale, root note, and tempo.

You can only hear planets within 10 mrad of your position. Volume \
fades linearly as you move away, so traveling through a cluster of \
planets creates a shifting mix."""),
        ("Timbres & Scales", """\
Each planet's sound picks one of 10 timbres: supersaw pad, acid bass, \
synth pluck, FM bass, noise drone, ring modulation, pulse-width \
modulation, organ, wavefold, or stutter.

The melody follows one of 12 scales (pentatonic, dorian, blues, \
harmonic minor, etc.) with a root note anywhere from a deep 33 Hz \
rumble up to a bright 466 Hz tone. Tempo ranges from a slow drone \
(5 seconds per note) to rapid pulses (0.08 seconds)."""),
        ("Spatial Mixing", """\
As you fly around, sounds crossfade naturally — nearby planets get \
louder, distant ones disappear. Each loop crossfades its own start \
and end so there's no click or gap.

High harmonics roll off above 580 Hz to keep everything warm and \
blendable. All loops are volume-normalized so no single planet blasts \
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
that just barely touches the sphere at your position (like a table \
touching a basketball). The camera uses three perpendicular direction \
vectors in this tangent plane as its local X/Y/Z axes.

Nearby planets get projected onto these axes, giving 3D coordinates \
that get drawn on screen. Planets farther away in angular distance \
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
The right panel lists every visible planet, sorted nearest-first. Each \
row shows the planet's identicon, name, and distance (in milliradians \
for close planets, radians for far ones).

Scroll with UP/DOWN. Click any row to fly there. Already-visited \
planets appear dimmed. The header shows how many planets are visible \
and how many you've visited this session."""),
        ("Tooltip", """\
Hover your mouse over any planet in the viewport to see a floating \
tooltip with the planet's identicon, name, and distance. The border \
color matches the planet's display color in the current view mode.

Hovering a name in the sidebar highlights the matching planet in the \
viewport with a white circle outline."""),
        ("Detail Panel & Radial Menu", """\
Hold-click (don't release immediately) on a planet to pop open a \
radial menu. Move to the "Info" wedge and release to open the detail \
panel. Move to the "Talk" wedge to start a conversation.

The detail panel shows a large planet sprite and identicon, the \
planet's name, exact distance, full 4D coordinates (x, y, z, w), \
and your reputation with that creature (shown as stars).

Click anywhere else to dismiss the panel."""),
        ("Saving", """\
Your progress saves automatically when you close the game. This includes \
your position, orientation, reputation with creatures, and visit history. \
The next time you launch, you'll resume exactly where you left off.

If the save file is missing or corrupted, the game starts fresh with \
defaults — it will never crash on a bad save."""),
        ("Compass", """\
The compass widget (top-left corner) shows your absolute 4D orientation on S3.

Compass Rose: The rotating needle points toward X+ in the XZ plane. \
Cardinal labels X+, X-, Z+, Z- mark the fixed standard basis directions.

Tilt Bar: The vertical bar on the right of the widget shows your Y-axis alignment. \
Indicator at top = aligned with Y axis, at bottom = perpendicular.

W Gauge: The small circle (top-left of widget) changes color based on your \
W-axis alignment. Blue = pointing toward -W, red = toward +W, grey = perpendicular.

All indicators use fixed reference axes, not your local camera frame -- \
so the compass always shows where you are on S3 in absolute terms."""),
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
