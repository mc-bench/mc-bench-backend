import pytest

from mc_bench.apps.server_worker.tasks.run import get_frames_per_command


@pytest.mark.parametrize(
    "num_commands, expected",
    [(4500, 1), (4501, 2), (9000, 2), (9001, 3)],
)
def test_get_frames_per_command(num_commands, expected):
    assert get_frames_per_command(num_commands) == expected
