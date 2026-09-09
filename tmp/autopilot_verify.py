"""
Offline verification of the BoatPhysics + BoatController control loop.
Replicates the exact C# math (mass, thrust, drag, rudder torque, autopilot
gains) with plain Python to check whether a boat converges to a waypoint.
"""
import math

DT = 0.02
MASS = 0.03
G = 9.81

# BoatPhysics
MAX_THRUST = 0.032
MAX_SPEED = 0.17
RUDDER_TORQUE_SCALE = 4e-7          # candidate fix value
LATERAL_DRAG = 3.2                  # acceleration
FORWARD_DRAG = 0.22                 # acceleration
ANGULAR_DAMPING = 0.65              # per-second decay
UPRIGHT_TORQUE = 0.055              # per rad
ROLL_DAMP_TORQUE = 0.02
HEAVE_DAMPING = 0.6                 # candidate addition
BUOY_STIFFNESS_PER_POINT = 1000.0 * G * (0.07 * 0.05 * 0.25)
HULL_SIDE_DEPTH = 0.018
# inertias from the box collider 0.046 x 0.020 x 0.066
I_YAW = MASS / 12.0 * (0.046 ** 2 + 0.066 ** 2)

# BoatController
WAYPOINT_TOL = 0.006
CRUISE_SPEED = 0.15
RUDDER_GAIN = 2.1
RUDDER_DAMP = 3.5      # derivative gain: rudder deg per deg/s of yaw rate


class Boat:
    def __init__(self, x, z, yaw):
        self.x = x
        self.z = z
        self.y = -0.005
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.yaw = yaw          # radians, 0 = +Z? use standard: heading of +X
        self.w_yaw = 0.0
        self.w_pitch = 0.0
        self.w_roll = 0.0
        self.turning = False

    def forward(self):
        return (math.cos(self.yaw), math.sin(self.yaw))

    def step(self, target):
        # ---- autopilot ----
        dx, dz = target[0] - self.x, target[1] - self.z
        dist = math.hypot(dx, dz)
        if dist <= WAYPOINT_TOL:
            return True
        desired = (dx / dist, dz / dist)
        heading = math.degrees(self.yaw)
        desired_heading = math.degrees(math.atan2(desired[1], desired[0]))
        err = (desired_heading - heading + 180) % 360 - 180
        fwd = (math.cos(self.yaw), math.sin(self.yaw))
        fwd_speed = self.vx * fwd[0] + self.vz * fwd[1]
        # Spin-in-place strategy: no reversing, so no rudder sign inversion.
        yaw_rate_dps = math.degrees(self.w_yaw)
        rudder = max(-40, min(40, err * RUDDER_GAIN - yaw_rate_dps * RUDDER_DAMP))
        desired_speed = min(CRUISE_SPEED, max(0.02, dist * 1.2))
        if abs(err) > 75:
            desired_speed = min(desired_speed, 0.03)
        if abs(err) > 130:
            self.turning = True
        elif self.turning and abs(err) < 110:
            self.turning = False
        if self.turning:
            throttle = 0.0          # stop and spin in place
        else:
            throttle = max(0, min(1, (desired_speed - fwd_speed) * 9))

        # ---- propulsion ----
        thrust = 0.0
        if throttle > 0.001 and fwd_speed < MAX_SPEED:
            reserve = max(0, min(1, (MAX_SPEED - fwd_speed) / MAX_SPEED))
            scale = 0.25 + 0.75 * reserve
            thrust = throttle * MAX_THRUST * scale * math.cos(math.radians(rudder))
        elif throttle < -0.001 and fwd_speed > -MAX_SPEED * 0.5:
            thrust = throttle * MAX_THRUST * 0.6
        self.vx += fwd[0] * thrust / MASS * DT
        self.vz += fwd[1] * thrust / MASS * DT

        # ---- rudder yaw torque ----
        # authority floor so the boat can pivot even at very low speed
        speed_factor = max(0.25, min(1.0, abs(fwd_speed) / 0.03))
        sign = 1.0 if fwd_speed >= 0 else -1.0
        tau = rudder * RUDDER_TORQUE_SCALE * speed_factor * sign
        self.w_yaw += tau / I_YAW * DT
        self.w_yaw *= (1 - ANGULAR_DAMPING * DT)

        # ---- resistance ----
        lat_x = self.vx - fwd[0] * fwd_speed
        lat_z = self.vz - fwd[1] * fwd_speed
        self.vx -= lat_x * LATERAL_DRAG * DT
        self.vz -= lat_z * LATERAL_DRAG * DT
        self.vx -= fwd[0] * fwd_speed * FORWARD_DRAG * DT
        self.vz -= fwd[1] * fwd_speed * FORWARD_DRAG * DT

        # ---- buoyancy + heave damping ----
        submerged = max(0.0, min(0.0 - self.y, HULL_SIDE_DEPTH))
        self.vy += (BUOY_STIFFNESS_PER_POINT * 4 * submerged / MASS - G) * DT
        self.vy -= self.vy * HEAVE_DAMPING / MASS * DT

        # ---- integrate ----
        self.yaw += self.w_yaw * DT
        self.x += self.vx * DT
        self.z += self.vz * DT
        self.y += self.vy * DT
        return False


def run_case(name, start, yaw_deg, target, seconds=30):
    b = Boat(start[0], start[1], math.radians(yaw_deg))
    reached = False
    t_reach = None
    for i in range(int(seconds / DT)):
        if b.step(target):
            reached = True
            t_reach = i * DT
            break
    d = math.hypot(target[0] - b.x, target[1] - b.z)
    print(f"{name}: reached={reached} t={t_reach if t_reach is not None else '-'}s "
          f"final_dist={d:.4f} speed={math.hypot(b.vx, b.vz):.4f} yaw={math.degrees(b.yaw):.1f}")
    return reached


if __name__ == "__main__":
    print(f"buoyancy stiffness/point = {BUOY_STIFFNESS_PER_POINT:.2f} N/m")
    print(f"yaw inertia = {I_YAW:.3e} kg*m2, rudder torque full = {40*RUDDER_TORQUE_SCALE:.3e} N*m, alpha = {40*RUDDER_TORQUE_SCALE/I_YAW:.2f} rad/s2")
    print()
    ok = True
    ok &= run_case("45deg turn, 28cm away   ", (0, 0), 0, (0.2, 0.2))
    ok &= run_case("135deg turn-around       ", (0, 0), 0, (-0.2, 0.2))
    ok &= run_case("180deg turn-around       ", (0, 0), 0, (-0.25, 0))
    ok &= run_case("straight, 20cm           ", (0, 0), 45, (0.141, 0.141))
    print()
    print("ALL PASS" if ok else "FAILURES PRESENT")
