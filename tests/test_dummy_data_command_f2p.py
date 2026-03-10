import subprocess
import sys
from pathlib import Path


def test_dummy_data_command_runs_without_error_f2p():
    """
    This test just calls the dummy data loader command.
    It checks that the process exits with code 0.
    This is a very small safety check around the script.
    """

    project_root = Path(__file__).resolve().parent.parent
    manage_py = project_root / "manage.py"

    result = subprocess.run(
        [sys.executable, str(manage_py), "load_dummy_data", "--users", "1", "--courses", "1"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

