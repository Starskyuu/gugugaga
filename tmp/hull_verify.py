# -*- coding: utf-8 -*-
"""Generate the rescue boat hull mesh (5 stations) and verify Unity winding order.

Unity front-face rule (verified against Unity's built-in Plane mesh):
for a visible triangle, cross(b - a, c - a) points OUTWARD from the surface.
Each triangle is checked against the hull center; flipped where needed.
Output is C# array literals ready to paste into ProceduralRescueModels.cs.
"""

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])

def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

# stations: (z, deckHalfW, deckY, chineHalfW, chineY, keelY)
stations = [
    (-0.035, 0.0230, 0.014, 0.0190, -0.0015, -0.0040),  # transom
    (-0.015, 0.0250, 0.014, 0.0210, -0.0020, -0.0050),  # stern
    ( 0.005, 0.0250, 0.014, 0.0210, -0.0020, -0.0050),  # midship
    ( 0.024, 0.0160, 0.013, 0.0110, -0.0010, -0.0030),  # bow taper
    ( 0.035, 0.0040, 0.012, 0.0025, -0.0005, -0.0010),  # bow tip
]

verts = []
for z, dhw, dy, chw, cy, ky in stations:
    verts.append((-dhw, dy, z))   # slot 0: deck port
    verts.append(( dhw, dy, z))   # slot 1: deck starboard
    verts.append((-chw, cy, z))   # slot 2: chine port
    verts.append(( chw, cy, z))   # slot 3: chine starboard
    verts.append(( 0.0, ky, z))   # slot 4: keel

def vi(i, j):
    return i * 5 + j

tris = []
for i in range(4):
    dL0, dR0, cL0, cR0, k0 = (vi(i, j) for j in range(5))
    dL1, dR1, cL1, cR1, k1 = (vi(i + 1, j) for j in range(5))
    tris += [
        (dL0, dR1, dR0), (dL0, dL1, dR1),   # deck band (top)
        (dL0, cL0, cL1), (dL0, cL1, dL1),   # port side
        (dR0, cR1, cR0), (dR0, dR1, cR1),   # starboard side
        (cL0, k1, k0), (cL0, cL1, k1),      # bottom port
        (cR0, k0, k1), (cR0, k1, cR1),      # bottom starboard
    ]
# transom cap (station 0, faces -Z)
dL, dR, cL, cR, k = (vi(0, j) for j in range(5))
tris += [(dL, dR, cR), (dL, cR, k), (dL, k, cL)]
# bow cap (station 4, faces +Z)
dL, dR, cL, cR, k = (vi(4, j) for j in range(5))
tris += [(dL, cR, dR), (dL, k, cR), (dL, cL, k)]

center = (0.0, 0.0045, 0.0)
fixed = []
flips = 0
for t in tris:
    a, b, c = verts[t[0]], verts[t[1]], verts[t[2]]
    n = cross(sub(b, a), sub(c, a))
    centroid = ((a[0] + b[0] + c[0]) / 3.0,
                (a[1] + b[1] + c[1]) / 3.0,
                (a[2] + b[2] + c[2]) / 3.0)
    if dot(n, sub(centroid, center)) < 0:
        t = (t[0], t[2], t[1])
        flips += 1
    fixed.append(t)

print("vertices:", len(verts), " triangles:", len(fixed), " flipped:", flips)
print("--- C# vertices ---")
for v in verts:
    print("new Vector3({:.5f}f, {:.5f}f, {:.5f}f),".format(v[0], v[1], v[2]))
print("--- C# triangles ---")
for t in fixed:
    print("{},{},{},".format(t[0], t[1], t[2]))
