import sys
from pathlib import Path

import pytest

# Add scripts to path so tests can import modules
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def temp_db(tmp_path):
    """Create a HealthStorage instance with a temporary database."""
    from health_storage import HealthStorage

    db_path = tmp_path / "test_health.sqlite"
    return HealthStorage(db_path)
