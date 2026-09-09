"""
Route-following parameter search: emulate the planner's 1 cm waypoint route
and test several autopilot/physics parameter sets for convergence quality.
"""
import math
import sys

DT = 0.02
MASS = 0.03
G = 9.81
MAX_THRUST = 0.032
MAX_SPEED = 0.17
RUDDER_SCALE = 4e-7
LATERAL_DRAG = 3.2
FORWARD_DRAG = 0.22
UPRIGHT = 0.055
ROLL_DAMP = 0.02
HEAVE_DAMP = 0.6
I_YAW = MASS / 12.0 * (0.046 ** 2 + 0.066 ** 2)
BUOY = 1000.0 * G * (0.07 * 0.05 * 0.25)


class Config:
    def __init__(self, name, ang_damp, kp, kd, cruise, err_speed_gain, lookahead, reverse_turn):
        self.name = name
        self.ang_damp = ang_damp
        self.kp = kp
        self.kd = kd
        self.cruise = cruise
        self.err_speed_gain = err_speed_gain   # v = cruise*(1 - |err|*gain), 0 = off
        self.lookahead = lookahead             # aim this many waypoints ahead
        self.reverse_turn = reverse_turn


def build_route(person):
    """Route from origin to person with 1 cm spacing (like the planner)."""
    pts = []
    # a curvy path: forward then diagonal
    x, z = 0.0, 0.0
    for _ in range(14):
        pts.append((x, z)); x += 0.01
    for _ in range(12):
        pts.append((x, z)); x += 0.005; z += 0.00866
    for _ in range(14):
        pts.append((x, z)); z += 0.01
    return pts


def run(config, route, person, seconds=60):
    x, z, y = 0.0, 0.0, -0.005
    vx = vz = vy = 0.0
    yaw = 0.0
    w = 0.0
    idx = 0
    turning = False
    max_err = 0.0
    for step in range(int(seconds / DT)):
        # lookahead waypoint
        target = route[min(idx + config.lookahead, len(route) - 1)]
        dx, dz = target[0] - x, target[1] - z
        dist = math.hypot(dx, dz)
        # advance waypoints
        while idx < len(route):
            wx, wz = route[idx]
            if math.hypot(wx - x, wz - z) <= 0.006:
                idx += 1
            else:
                break
        if idx >= len(route):
            return ("reached", step * DT, max_err, math.hypot(person[0] - x, person[1] - z))
        if dist < 1e-6:
            continue
        desired = (dx / dist, dz / dist)
        heading = math.degrees(yaw)
        desired_heading = math.degrees(math.atan2(desired[1], desired[0]))
        err = (desired_heading - heading + 180) % 360 - 180
        max_err = max(max_err, abs(err))
        fwd = (math.cos(yaw), math.sin(yaw))
        fwd_speed = vx * fwd[0] + vz * fwd[1]
        w_dps = math.degrees(w)

        # rudder with optional D term and optional reverse compensation
        if config.reverse_turn and fwd_speed < -0.01:
            rudder = max(-40, min(40, -err * config.kp - w_dps * config.kd))
        else:
            rudder = max(-40, min(40, err * config.kp - w_dps * config.kd))

        # desired speed: distance-scaled + optional error-scaled
        desired_speed = min(config.cruise, max(0.02, dist * 1.2))
        if config.err_speed_gain > 0:
            desired_speed = min(desired_speed, config.cruise * max(0.15, 1 - abs(err) * config.err_speed_gain))
        if abs(err) > 130:
            turning = True
        elif turning and abs(err) < 110:
            turning = False
        if config.reverse_turn:
            throttle = -0.45 if turning else max(0, min(1, (desired_speed - fwd_speed) * 9))
        else:
            throttle = max(0, min(1, (desired_speed - fwd_speed) * 9))

        # propulsion
        thrust = 0.0
        if throttle > 0.001 and fwd_speed < MAX_SPEED:
            reserve = max(0, min(1, (MAX_SPEED - fwd_speed) / MAX_SPEED))
            scale = 0.25 + 0.75 * reserve
            thrust = throttle * MAX_THRUST * scale * math.cos(math.radians(rudder))
        elif throttle < -0.001 and fwd_speed > -MAX_SPEED * 0.5:
            thrust = throttle * MAX_THRUST * 0.6
        vx += fwd[0] * thrust / MASS * DT
        vz += fwd[1] * thrust / MASS * DT

        # rudder torque
        speed_factor = min(1.0, abs(fwd_speed) / 0.03)
        sign = 1.0 if fwd_speed >= 0 else -1.0
        tau = rudder * RUDDER_SCALE * speed_factor * sign
        w += tau / I_YAW * DT
        w *= (1 - config.ang_damp * DT)

        # resistance
        lat_x = vx - fwd[0] * fwd_speed
        lat_z = vz - fwd[1] * fwd_speed
        vx -= lat_x * LATERAL_DRAG * DT
        vz -= lat_z * LATERAL_DRAG * DT
        vx -= fwd[0] * fwd_speed * FORWARD_DRAG * DT
        vz -= fwd[1] * fwd_speed * FORWARD_DRAG * DT

        # buoyancy + heave
        submerged = max(0.0, min(0.0 - y, 0.018))
        vy += (BUOY * 4 * submerged / MASS - G) * DT
        vy -= vy * HEAVE_DAMP / MASS * DT

        yaw += w * DT
        x += vx * DT
        z += vz * DT
        y += vy * DT
    return ("timeout", seconds, max_err, math.hypot(person[0] - x, person[1] - z))


PERSON = (0.20, 0.20)
ROUTE = build_route(PERSON)

if __name__ == "__main__":
    configs = [
        Config("A current(Kp2.1,rev)", 0.65, 2.1, 0.0, 0.15, 0.0, 0, True),
        Config("B A+errSpeed",         0.65, 2.1, 0.0, 0.15, 1/60.0, 0, True),
        Config("C A+lookahead3",       0.65, 2.1, 0.0, 0.15, 0.0, 3, True),
        Config("D B+lookahead3",       0.65, 2.1, 0.0, 0.15, 1/60.0, 3, True),
        Config("E damp0.35 Kd70 errSp",0.35, 2.1, 70.0, 0.15, 1/60.0, 0, True),
        Config("F E+lookahead3",       0.35, 2.1, 70.0, 0.15, 1/60.0, 3, True),
        Config("G damp0.35 Kd30 errSp",0.35, 2.1, 30.0, 0.15, 1/60.0, 0, True),
        Config("H G+lookahead3",       0.35, 2.1, 30.0, 0.15, 1/60.0, 3, True),
    ]

    for c in configs:
        status, t, maxerr, finaldist = run(c, ROUTE, PERSON)
        print(f"{c.name:26s} {status:8s} t={t:5.2f}s maxErr={maxerr:6.1f}deg finalDist={finaldist*100:5.1f}cm")
