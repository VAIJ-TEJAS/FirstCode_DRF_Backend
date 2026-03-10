import importlib.util
import pytest


MODULE_PATH = "utils.schedule_allocation"


def test_schedule_allocation_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("schedule allocation module not available")

    from utils.schedule_allocation import ScheduleDemand, ScheduleSupply, allocate_schedule

    assignments = allocate_schedule(
        [ScheduleDemand(cohort_id="c-1", learners=20, preferred_window="w1")],
        [ScheduleSupply(instructor_id="i-1", capacity=25, windows=["w1"])],
    )

    assert assignments
    assert assignments[0].instructor_id == "i-1"
