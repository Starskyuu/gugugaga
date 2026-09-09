"""
Route-following parameter search v2: no reverse-turn (no sign inversions),
speed-factor floor, tunable waypoint tolerance, D gain, err-scaled speed,
capture distance (aim straight at near waypoints), low speed floors to
break the circular-orbit limit cycle.
"""
import math

DT = 0.02
MASS = 0.03
G = 9.81
MAX_THRUST = 0.032
MAX_SPEED = 0.17
RUDDER_SCALE = 4e-7
LATERAL_DRAG = 3.2
FORWARD_DRAG = 0.22
I_YAW = MASS / 12.0 * (0.046 ** 2 + 0.066 ** 2)
BUOY = 1000.0 * G * (0.07 * 0.05 * 0.25)
HEAVE_DAMP = 0.6


class Config:
    def __init__(self, name, ang_damp=0.65, kp=2.1, kd=1.2, cruise=0.15,
                 err_speed_gain=1.0 / 40.0, lookahead=3, tol=0.015,
                 speed_floor=0.25, err_speed_floor=0.03, dist_floor=0.002,
                 capture=0.05, lookahead_dist=None):
        self.name = name
        self.ang_damp = ang_damp
        self.kp = kp
        self.kd = kd
        self.cruise = cruise
        self.err_speed_gain = err_speed_gain
        self.lookahead = lookahead
        self.tol = tol
        self.speed_floor = speed_floor
        self.err_speed_floor = err_speed_floor
        self.dist_floor = dist_floor
        self.capture = capture
        self.lookahead_dist = lookahead_dist


def build_route(person):
    """Waypoints at 1 cm spacing from origin to the person (2 turns)."""
    pts = []
    x, z = 0.0, 0.0
    for _ in range(14):           # east
        pts.append((x, z)); x += 0.01
    for _ in range(10):           # diagonal NE
        pts.append((x, z)); x += 0.006; z += 0.008
    for _ in range(10):           # north, ends near (0.2, 0.2)
        pts.append((x, z)); z += 0.01
    pts.append(person)
    return pts


def advance_idx(route, idx, x, z, tol, window=8):
    """Consume waypoints: sequential within tol, plus the furthest waypoint
    within tol inside a window (covers corner cuts so skipped waypoints can
    never wedge the route open)."""
    while idx < len(route):
        if math.hypot(route[idx][0] - x, route[idx][1] - z) <= tol:
            idx += 1
            continue
        furthest = -1
        for i in range(idx + 1, min(idx + window + 1, len(route))):
            if math.hypot(route[i][0] - x, route[i][1] - z) <= tol:
                furthest = i
        if furthest > idx:
            idx = furthest + 1
            continue
        break
    return idx


def run(config, route, person, seconds=60):
    x, z = 0.0, 0.0
    vx = vz = 0.0
    yaw = 0.0
    w = 0.0
    idx = 0
    max_err = 0.0
    for step in range(int(seconds / DT)):
        idx = advance_idx(route, idx, x, z, config.tol)
        if idx >= len(route):
            return ("reached", step * DT, max_err, math.hypot(person[0] - x, person[1] - z))

        # Distance-based lookahead: first waypoint at least lookahead_dist
        # ahead of the boat (spacing-independent behaviour).
        nxt = route[idx]
        d_next = math.hypot(nxt[0] - x, nxt[1] - z)
        if d_next >= config.lookahead_dist:
            target = nxt
        else:
            acc = d_next
            prev = nxt
            target = route[-1]
            for i in range(idx + 1, len(route)):
                p = route[i]
                acc += math.hypot(p[0] - prev[0], p[1] - prev[1])
                if acc >= config.lookahead_dist:
                    target = p
                    break
                prev = p

        dx, dz = target[0] - x, target[1] - z
        dist = math.hypot(dx, dz)
        if dist < 1e-9:
            continue
        desired = (dx / dist, dz / dist)
        heading = math.degrees(yaw)
        dh = math.degrees(math.atan2(desired[1], desired[0]))
        err = (dh - heading + 180) % 360 - 180
        max_err = max(max_err, abs(err))
        fwd = (math.cos(yaw), math.sin(yaw))
        fs = vx * fwd[0] + vz * fwd[1]
        w_dps = math.degrees(w)

        rudder = max(-40, min(40, err * config.kp - w_dps * config.kd))

        desired_speed = min(config.cruise, max(config.dist_floor, dist * 1.2))
        if config.err_speed_gain > 0:
            desired_speed = min(
                desired_speed,
                config.cruise * max(config.err_speed_floor,
                                    1 - abs(err) * config.err_speed_gain))
        throttle = max(0.0, min(1.0, (desired_speed - fs) * 9))

        thrust = 0.0
        if throttle > 0.001 and fs < MAX_SPEED:
            reserve = max(0.0, min(1.0, (MAX_SPEED - fs) / MAX_SPEED))
            scale = 0.25 + 0.75 * reserve
            thrust = throttle * MAX_THRUST * scale * math.cos(math.radians(rudder))
        vx += fwd[0] * thrust / MASS * DT
        vz += fwd[1] * thrust / MASS * DT

        speed_factor = max(config.speed_floor, min(1.0, abs(fs) / 0.03))
        tau = rudder * RUDDER_SCALE * speed_factor
        w += tau / I_YAW * DT
        w *= (1 - config.ang_damp * DT)

        lat_x = vx - fwd[0] * fs
        lat_z = vz - fwd[1] * fs
        vx -= lat_x * LATERAL_DRAG * DT
        vz -= lat_z * LATERAL_DRAG * DT
        vx -= fwd[0] * fs * FORWARD_DRAG * DT
        vz -= fwd[1] * fs * FORWARD_DRAG * DT

        yaw += w * DT
        x += vx * DT
        z += vz * DT
    return ("timeout", seconds, max_err, math.hypot(person[0] - x, person[1] - z))


def resample(route, spacing=0.03):
    """Reduce waypoint density: keeps turns but drops intermediate points."""
    out = [route[0]]
    last = route[0]
    for p in route[1:]:
        if math.hypot(p[0] - last[0], p[1] - last[1]) >= spacing:
            out.append(p)
            last = p
    if out[-1] != route[-1]:
        out.append(route[-1])
    return out


PERSON = (0.20, 0.20)
ROUTE = build_route(PERSON)
ROUTE3 = resample(ROUTE, 0.03)

if __name__ == "__main__":
    configs = [
        Config("R1cm LD.09 g1/40", lookahead_dist=0.09),
        Config("R1cm LD.12 g1/40", lookahead_dist=0.12),
        Config("R1cm LD.15 g1/40", lookahead_dist=0.15),
        Config("R3cm LD.09 g1/40", lookahead_dist=0.09),
        Config("R3cm LD.12 g1/40", lookahead_dist=0.12),
        Config("R3cm LD.15 g1/40", lookahead_dist=0.15),
        Config("R1cm LD.09 g1/30", lookahead_dist=0.09, err_speed_gain=1.0 / 30.0),
        Config("R1cm LD.12 g1/30", lookahead_dist=0.12, err_speed_gain=1.0 / 30.0),
        Config("R3cm LD.09 g1/30", lookahead_dist=0.09, err_speed_gain=1.0 / 30.0),
        Config("R3cm LD.12 g1/30", lookahead_dist=0.12, err_speed_gain=1.0 / 30.0),
        Config("R1cm LD.09 g1/50", lookahead_dist=0.09, err_speed_gain=1.0 / 50.0),
        Config("R3cm LD.09 g1/50", lookahead_dist=0.09, err_speed_gain=1.0 / 50.0),
        Config("R1cm LD.12 esf.05 g1/40", lookahead_dist=0.12, err_speed_floor=0.05),
        Config("R3cm LD.12 esf.05 g1/40", lookahead_dist=0.12, err_speed_floor=0.05),
        Config("R1cm LD.09 tol2.0 g1/40", lookahead_dist=0.09, tol=0.020),
        Config("R3cm LD.09 tol2.0 g1/40", lookahead_dist=0.09, tol=0.020),
        Config("R1cm LD.12 kd0.8 g1/40", lookahead_dist=0.12, kd=0.8),
        Config("R1cm LD.09 kd0.8 g1/40", lookahead_dist=0.09, kd=0.8),
    ]
    for c in configs:
        route = ROUTE if "R1cm" in c.name else ROUTE3
        status, t, maxerr, finaldist = run(c, route, PERSON)
        print(f"{c.name:30s} {status:8s} t={t:5.2f}s maxErr={maxerr:6.1f} finalDist={finaldist*100:5.1f}cm")
