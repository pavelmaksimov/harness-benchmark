"""Desired-state planning and supervision for unattended benchmark fleets."""

from benchmark.fleet.config import DesiredConfig, ExperimentTarget, HarnessTarget, load_desired

__all__ = [
    "DesiredConfig",
    "ExperimentTarget",
    "FleetAction",
    "FleetCell",
    "FleetPlan",
    "HarnessTarget",
    "build_plan",
    "load_desired",
]


def __getattr__(name: str):
    if name in {"FleetAction", "FleetCell", "FleetPlan", "build_plan"}:
        from benchmark.fleet.planner import FleetAction, FleetCell, FleetPlan, build_plan

        return {
            "FleetAction": FleetAction,
            "FleetCell": FleetCell,
            "FleetPlan": FleetPlan,
            "build_plan": build_plan,
        }[name]
    raise AttributeError(name)
