from pathlib import Path

import logging
import os
import pytest

# Get the absolute path of your project root directory
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# Store the original factory so we don't break Python's internals
old_factory = logging.getLogRecordFactory()

def custom_record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)

    # Calculate the path relative to the project root
    if record.pathname:
        try:
            record.relative_path = os.path.relpath(record.pathname, PROJECT_ROOT)
        except ValueError:
            # Fallback to absolute path if file is on a different drive (Windows edge case)
            record.relative_path = record.pathname
    else:
        record.relative_path = "unknown"

    return record

# Tell the logging framework to use our customized factory during the test run
logging.setLogRecordFactory(custom_record_factory)


@pytest.fixture
def test_data_loader(request):
    """
    Returns a function that loads a text file from the local 'test_data' directory.
    """
    test_dir = Path(request.fspath).parent
    data_dir = test_dir / "test_data"

    def _loader(filename: str) -> str:
        file_path = data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found at {file_path}")
        return file_path.read_text(encoding="utf-8")

    return _loader
