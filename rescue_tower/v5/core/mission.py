"""自动任务状态机：水位 -> 升台 -> 发现目标 -> 规划 -> 靠近并停车。"""

from __future__ import annotations

import threading
import time

import config
from core.devices import Boat, Lift
from core.navigation import PidPilot, desired_heading, distance, normalize_angle
from core.planner import PathPlanner, PlannedRoute
from core.state import SystemState


class MissionController:
    def __init__(self, state: SystemState, flood_event: threading.Event, stop_event: threading.Event) -> None:
        self.state, self.flood_event, self.stop_event = state, flood_event, stop_event
        self.boat, self.lift, self.planner = Boat(state), Lift(state), PathPlanner()
        self.pilot = PidPilot()
        self._abort = threading.Event()
        self._mission_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self, skip_water: bool = False) -> bool:
        if self._thread and self._thread.is_alive():
            # 整机启动后任务通常正在等水位，测试按钮可以直接放行这一步。
            if skip_water:
                self.flood_event.set()
                return True
            return False
        self._abort.clear()
        if skip_water:
            self.flood_event.set()
        self._thread = threading.Thread(target=self._run, name="mission", daemon=True)
        self._thread.start()
        return True

    def abort(self, reason: str = "任务已停止") -> None:
        self._abort.set()
        self.boat.stop()
        self.state.mission("stopped", "任务停止", reason)

    def reset(self) -> None:
        self.abort("系统复位")
        self.flood_event.clear()
        self.state.update("water", triggered=False)
        self.state.mission("idle", "等待水位触发", "系统已复位")

    def manual(self, command: str) -> bool:
        self._abort.set()
        self.state.update("control", mode="manual")
        # 网页按住按钮时每 200ms 续发一次，只有命令变化才记日志。
        if command != self.boat.last_command:
            self.state.mission("manual", "手动控制", f"执行 {command} 指令")
        return self.boat.send(command)

    def _cancelled(self) -> bool:
        return self._abort.is_set() or self.stop_event.is_set()

    def _sleep(self, seconds: float) -> bool:
        return self._abort.wait(seconds) or self.stop_event.is_set()

    def _fresh_vision(self) -> dict | None:
        snapshot = self.state.snapshot()
        vision = snapshot["vision"]
        if vision["age_ms"] is None or vision["age_ms"] > config.VISION_TIMEOUT_S * 1000:
            return None
        return vision if vision["coordinate_ready"] else None

    def _find_boat(self, vision: dict) -> dict | None:
        return next((b for b in vision["boats"] if int(b.get("id", -1)) == config.BOAT_ID), None)

    def _wait_for_scene(self) -> tuple[dict, list[dict]] | None:
        deadline = time.monotonic() + config.MISSION_TIMEOUT_S
        while not self._cancelled() and time.monotonic() < deadline:
            vision = self._fresh_vision()
            if vision:
                boat = self._find_boat(vision)
                if boat and boat.get("angle") is not None and vision["persons"]:
                    return boat, vision["persons"]
            self._sleep(0.2)
        return None

    def _navigate(self, route: PlannedRoute) -> bool:
        path = route.waypoints_mm
        waypoint_index = 1 if len(path) > 1 else 0
        last_target_seen = time.monotonic()
        last_plan = time.monotonic()
        last_pid_update = time.monotonic()
        throttle_failures = 0
        self.pilot.reset()  # 每次起航都从零开始，清掉上次的积分与微分
        deadline = time.monotonic() + config.MISSION_TIMEOUT_S
        while not self._cancelled() and time.monotonic() < deadline:
            vision = self._fresh_vision()
            if not vision:
                self.boat.stop()  # 坐标一过期立即停车
                self.pilot.reset()  # 清掉 PID 历史，重新有视觉后从零开始
                self._sleep(config.CONTROL_PERIOD_S)
                continue
            boat = self._find_boat(vision)
            if not boat or boat.get("angle") is None:
                self.boat.stop()
                self.pilot.reset()
                self._sleep(config.CONTROL_PERIOD_S)
                continue
            target = next((p for p in vision["persons"] if str(p.get("id")) == route.target_id), None)
            if target:
                route.target_x_mm, route.target_y_mm = float(target["x"]), float(target["y"])
                last_target_seen = time.monotonic()
                path[-1] = (route.target_x_mm, route.target_y_mm)
            elif time.monotonic() - last_target_seen > config.TARGET_LOST_TIMEOUT_S:
                self.boat.stop()
                self.pilot.reset()
                raise RuntimeError("目标丢失，已停车")

            position = (float(boat["x"]), float(boat["y"]))
            final = (route.target_x_mm, route.target_y_mm)
            if distance(position, final) <= config.ARRIVAL_RADIUS_MM:
                self.boat.stop()
                return True
            if target and time.monotonic() - last_plan >= config.REPLAN_PERIOD_S:
                # 根据最新船位和目标位置重新规划，避免一直追旧路径。
                updated = self.planner.plan_first_target(boat, [target])
                path = updated.waypoints_mm
                waypoint_index = 1 if len(path) > 1 else 0
                last_plan = time.monotonic()
                self.state.update("mission", path=[{"x": x, "y": y} for x, y in path])
            while waypoint_index < len(path) - 1 and distance(position, path[waypoint_index]) <= config.WAYPOINT_RADIUS_MM:
                waypoint_index += 1
            waypoint = path[min(waypoint_index, len(path) - 1)]

            # v4：双环 PID 连续油门替代 v3 的开关式 F/L/R/S。
            now = time.monotonic()
            dt = min(1.0, max(0.05, now - last_pid_update))
            last_pid_update = now
            a, b, status = self.pilot.update(
                position[0], position[1], float(boat["angle"]),
                waypoint[0], waypoint[1], dt,
            )
            ok = self.boat.throttle(round(a), round(b))
            if ok:
                throttle_failures = 0
            else:
                throttle_failures += 1
                if throttle_failures >= config.THROTTLE_MAX_FAILS:
                    self.boat.stop()
                    raise RuntimeError(f"连续 {config.THROTTLE_MAX_FAILS} 次油门下发失败，已停车")
            error = normalize_angle(desired_heading(position, waypoint) - float(boat["angle"]))
            self.state.update(
                "mission",
                waypoint_index=waypoint_index,
                heading_error=round(error, 1),
                throttle=(round(a), round(b)),
                pid_status=status,
            )
            self._sleep(config.CONTROL_PERIOD_S)
        self.boat.stop()
        return False

    def _run(self) -> None:
        if not self._mission_lock.acquire(blocking=False):
            return
        try:
            self.state.update("control", mode="auto")
            self.state.mission("waiting_water", "等待水位触发", "正在监听水位传感器")
            while not self._cancelled() and not self.flood_event.wait(0.2):
                pass
            if self._cancelled():
                return
            self.state.mission("raising_lift", "升降台上升", "洪水信号已确认")
            if not self.lift.send("U"):
                raise RuntimeError("升降台没有响应")
            if self._sleep(config.LIFT_RAISE_WAIT_S):
                return
            self.state.mission("searching", "寻找小船和人员", "请保证小船已下水且位于摄像头视野内")
            scene = self._wait_for_scene()
            if not scene:
                raise RuntimeError("规定时间内没有同时检测到小船和人员")
            boat_data, persons = scene
            route = self.planner.plan_first_target(boat_data, persons)
            self.state.mission(
                "navigating", "自动航行", f"目标 {route.target_id}，规划距离 {route.distance_mm:.0f} mm",
                target_id=route.target_id,
                path=[{"x": x, "y": y} for x, y in route.waypoints_mm], waypoint_index=0,
            )
            if not self._navigate(route):
                if not self._cancelled():
                    raise RuntimeError("自动航行超时")
                return
            self.state.mission("arrived", "已到达目标", "小船已靠近目标并停车")
        except Exception as exc:
            self.boat.stop()
            self.state.mission("error", "任务异常", str(exc))
        finally:
            self._mission_lock.release()
