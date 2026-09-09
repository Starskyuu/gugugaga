#!/usr/bin/env python3
"""智能救援塔 v2 入口，同时支持整机运行和分模块调试。"""

from __future__ import annotations

import argparse
import json
import threading
import time

import config
from core.devices import Boat, Lift, VisionReceiver, WaterReceiver
from core.mission import MissionController
from core.planner import PathPlanner
from core.state import SystemState
from core.web import serve


def build_system():
    state = SystemState()
    stop_event, flood_event = threading.Event(), threading.Event()
    mission = MissionController(state, flood_event, stop_event)
    return state, stop_event, flood_event, mission


def run_all() -> None:
    state, stop_event, flood_event, mission = build_system()
    VisionReceiver(state, stop_event).start()
    WaterReceiver(state, flood_event, stop_event).start()
    mission.start()
    try:
        serve(state, mission)
    except KeyboardInterrupt:
        stop_event.set(); mission.abort("程序退出")


def debug_module(args) -> None:
    state, stop_event, flood_event, mission = build_system()
    if args.module == "boat":
        ok = Boat(state).send(args.command); print("成功" if ok else state.snapshot()["control"])
    elif args.module == "lift":
        ok = Lift(state).send(args.command); print("成功" if ok else state.snapshot()["lift"])
    elif args.module == "vision":
        VisionReceiver(state, stop_event).start(); print("等待 666.py UDP 数据，Ctrl+C 退出")
        try:
            while True:
                time.sleep(1); print(json.dumps(state.snapshot()["vision"], ensure_ascii=False))
        except KeyboardInterrupt:
            stop_event.set()
    elif args.module == "water":
        WaterReceiver(state, flood_event, stop_event).start(); print(f"监听 TCP {config.WATER_PORT}，Ctrl+C 退出")
        try:
            while True:
                time.sleep(1); print(json.dumps(state.snapshot()["water"], ensure_ascii=False))
        except KeyboardInterrupt:
            stop_event.set()
    elif args.module == "planner":
        route = PathPlanner().plan_first_target(
            {"id": 0, "x": 50, "y": 50},
            [{"id": 1, "x": 500, "y": 500}, {"id": 2, "x": 180, "y": 120}],
        )
        print(json.dumps(route.__dict__, ensure_ascii=False, indent=2))
    elif args.module == "web":
        VisionReceiver(state, stop_event).start(); serve(state, mission)


def main() -> None:
    parser = argparse.ArgumentParser(description="智能救援塔 v2")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("run", help="运行整套自动系统")
    debug = sub.add_parser("debug", help="单独调试模块")
    debug.add_argument("module", choices=["boat", "lift", "water", "vision", "planner", "web"])
    debug.add_argument("command", nargs="?", help="boat: F/B/L/R/S；lift: U/D")
    args = parser.parse_args()
    if args.action in (None, "run"):
        run_all()
    else:
        if args.module == "boat" and args.command not in Boat.VALID:
            parser.error("boat 模块必须指定 F/B/L/R/S")
        if args.module == "lift" and args.command not in {"U", "D"}:
            parser.error("lift 模块必须指定 U/D")
        debug_module(args)


if __name__ == "__main__":
    main()
