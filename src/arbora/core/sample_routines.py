"""Read-only starter trusted routines for first-run testers.

Trust is still earned: samples cover inspect-only journeys (list downloads,
disk diagnose). Mutate / hard-confirmation plans are never auto-trusted.
"""

from __future__ import annotations

from arbora.core.broker import PermissionBroker
from arbora.core.planner import GoalPlanner
from arbora.core.routines_store import routines_to_dicts
from arbora.core.types import Sensitivity
from arbora.memory.store import LocalMemoryStore

MEMORY_FLAG = "sample_routines_seeded"

SAMPLE_SPECS: tuple[tuple[str, str], ...] = (
    ("list-downloads", "list downloads"),
    ("disk-diagnose", "diagnose disk space"),
)


def seed_sample_routines(
    broker: PermissionBroker,
    planner: GoalPlanner,
    memory: LocalMemoryStore,
) -> int:
    """Install sample routines when this memory store has never been seeded."""
    if memory.get(MEMORY_FLAG):
        return 0
    if broker.list_routines():
        memory.set(MEMORY_FLAG, True)
        return 0

    added = 0
    for name, goal in SAMPLE_SPECS:
        plan = planner.plan(goal)
        if not plan.steps:
            continue
        if plan.has_hard_confirmation_steps:
            continue
        if any(step.sensitivity != Sensitivity.READ for step in plan.steps):
            continue
        broker.promote_plan(plan, name)
        added += 1

    memory.set(MEMORY_FLAG, True)
    if added:
        memory.set("trusted_routines", routines_to_dicts(broker.list_routines()))
    return added
