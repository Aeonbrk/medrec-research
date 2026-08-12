from __future__ import annotations

import pytest

from medrec_research import (
    ExceptionDisposition,
    ExceptionKind,
    ExceptionRecord,
    LaneSpec,
    LaneStatus,
    RepairBudget,
    ResourceCeiling,
    ScheduleDecision,
    deterministic_schedule,
    route_exception,
)
from medrec_research.errors import ProtocolValidationError


def _lanes() -> tuple[LaneSpec, ...]:
    return tuple(
        LaneSpec(
            lane_id=f"lane-{model}",
            model_id=model,
            ordinal=index,
            cpu_hours=2,
            gpu_count=1,
            memory_gb=4,
        )
        for index, model in enumerate(("gamenet", "safedrug", "retain", "leap"))
    )


def test_scheduler_is_stable_and_admits_only_within_the_resource_ceiling() -> None:
    ceiling = ResourceCeiling(cpu_hours=4, gpu_count=1, memory_gb=8)
    first = deterministic_schedule(_lanes(), resource_ceiling=ceiling)
    second = deterministic_schedule(tuple(reversed(_lanes())), resource_ceiling=ceiling)

    assert first == second
    assert first.logical_lane_ids == ("lane-gamenet", "lane-safedrug", "lane-retain", "lane-leap")
    assert first.next_lane_id == "lane-gamenet"
    assert first.admitted_resources.gpu_count <= ceiling.gpu_count
    assert first.admitted_resources.cpu_hours <= ceiling.cpu_hours
    assert first.admitted_resources.memory_gb <= ceiling.memory_gb
    assert ScheduleDecision.from_json(first.to_json()) == first
    assert "/" not in first.to_json()


def test_one_failed_lane_does_not_cancel_independent_lanes() -> None:
    lanes = _lanes()
    failed = LaneSpec(
        lane_id=lanes[0].lane_id,
        model_id=lanes[0].model_id,
        ordinal=lanes[0].ordinal,
        cpu_hours=lanes[0].cpu_hours,
        gpu_count=lanes[0].gpu_count,
        memory_gb=lanes[0].memory_gb,
        status=LaneStatus.FAILED,
    )
    decision = deterministic_schedule(
        (failed, *lanes[1:]),
        resource_ceiling=ResourceCeiling(cpu_hours=4, gpu_count=1, memory_gb=8),
    )
    assert "lane-safedrug" in decision.ready_lane_ids
    assert "lane-gamenet" not in decision.ready_lane_ids


def test_non_waivable_exceptions_block_and_repairs_are_budgeted() -> None:
    authority = ExceptionRecord(
        exception_id="authority-block",
        kind=ExceptionKind.AUTHORITY,
        description="remote preflight is not current",
    )
    disposition, budget = route_exception(authority, RepairBudget(max_units=2))
    assert disposition is ExceptionDisposition.BLOCK
    assert budget.remaining_units == 2

    repair = ExceptionRecord(
        exception_id="dependency-repair",
        kind=ExceptionKind.DEPENDENCY,
        description="bounded compatibility repair",
        repair_units=1,
        artifact_changed=True,
    )
    disposition, budget = route_exception(repair, RepairBudget(max_units=1))
    assert disposition is ExceptionDisposition.REPAIR
    assert budget.remaining_units == 0
    disposition, _ = route_exception(repair, budget)
    assert disposition is ExceptionDisposition.BLOCK

    endpoint = ExceptionRecord(
        exception_id="mirror-endpoint",
        kind=ExceptionKind.ENDPOINT,
        description="auditable mirror selected",
    )
    assert route_exception(endpoint, budget)[0] is ExceptionDisposition.CONTINUE


def test_unscoped_non_waivable_exception_blocks_the_schedule() -> None:
    decision = deterministic_schedule(
        _lanes(),
        resource_ceiling=ResourceCeiling(cpu_hours=4, gpu_count=1, memory_gb=8),
        exceptions=(
            ExceptionRecord(
                exception_id="authority-block",
                kind=ExceptionKind.AUTHORITY,
                description="remote preflight is not current",
            ),
        ),
    )

    assert decision.ready_lane_ids == ()
    assert decision.blocked_lane_ids == decision.logical_lane_ids
    assert decision.next_lane_id is None


def test_scheduler_rejects_a_lane_that_cannot_fit_the_ceiling() -> None:
    oversized = LaneSpec(
        lane_id="lane-oversized",
        model_id="gamenet",
        ordinal=0,
        cpu_hours=100,
        gpu_count=2,
        memory_gb=100,
    )
    decision = deterministic_schedule(
        (oversized,),
        resource_ceiling=ResourceCeiling(cpu_hours=4, gpu_count=1, memory_gb=8),
    )
    assert decision.next_lane_id is None
    assert decision.blocked_lane_ids == ("lane-oversized",)


def test_scheduler_deduplicates_resource_and_exception_blockers() -> None:
    lane = LaneSpec(
        lane_id="lane-gamenet",
        model_id="gamenet",
        ordinal=0,
        cpu_hours=10,
        gpu_count=1,
        memory_gb=10,
    )
    decision = deterministic_schedule(
        (lane,),
        resource_ceiling=ResourceCeiling(cpu_hours=1, gpu_count=0, memory_gb=1),
        exceptions=(
            ExceptionRecord(
                exception_id="lane-gamenet",
                kind=ExceptionKind.AUTHORITY,
                description="lane authority is not current",
            ),
        ),
    )

    assert decision.blocked_lane_ids == ("lane-gamenet",)


def test_repair_budget_rejects_invalid_values() -> None:
    with pytest.raises(ProtocolValidationError, match="exhausted"):
        RepairBudget(max_units=1, used_units=2)
