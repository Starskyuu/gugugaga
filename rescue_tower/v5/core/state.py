"""线程间共享状态。所有模块只通过这个对象交换数据。"""

from __future__ import annotations

import copy
import threading
import time


class SystemState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = {
            "started_at": time.time(),
            "mission": {
                "stage": "idle",
                "stage_cn": "等待水位触发",
                "message": "系统已就绪",
                "automatic": True,
                "target_id": None,
                "path": [],
                "waypoint_index": 0,
            },
            "water": {"value": None, "baseline": None, "rise": None, "triggered": False, "online": False},
            "vision": {"received_at": None, "age_ms": None, "coordinate_ready": False, "boats": [], "persons": [], "performance": {}, "references": {"visible": 0, "inliers": 0, "ids": []}},
            "lift": {"command": "S", "ok": None, "message": "未动作"},
            "control": {"command": "S", "ok": None, "latency_ms": None, "error": None, "mode": "auto"},
            "events": [],
        }

    def update(self, section: str, **values) -> None:
        with self._lock:
            self._data[section].update(values)

    def mission(self, stage: str, stage_cn: str, message: str, **extra) -> None:
        self.update("mission", stage=stage, stage_cn=stage_cn, message=message, **extra)
        self.event(f"{stage_cn}：{message}")

    def event(self, text: str) -> None:
        with self._lock:
            self._data["events"].insert(0, {"time": time.strftime("%H:%M:%S"), "text": text})
            del self._data["events"][30:]

    def snapshot(self) -> dict:
        with self._lock:
            result = copy.deepcopy(self._data)
        received_at = result["vision"].pop("received_at", None)
        result["vision"]["age_ms"] = None if received_at is None else round((time.monotonic() - received_at) * 1000)
        # 兼容原前端所使用的顶层字段。
        result.update({key: result["vision"][key] for key in ("age_ms", "coordinate_ready", "boats", "persons", "performance", "references")})
        result["control"]["esp32_configured"] = True
        return result

