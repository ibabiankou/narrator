from pathlib import Path

import logging
import logging.config
import os
import pytest
import yaml

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


def pytest_configure(config):
    """
    Hook that runs before any tests are executed.
    Loads the logging configuration from the YAML file.
    """
    dir_path = os.path.dirname(__file__)
    yaml_path = os.path.join(dir_path, "../log_conf.yaml")

    if os.path.exists(yaml_path):
        with open(yaml_path, "r") as f:
            log_config = yaml.safe_load(f.read())
            logging.config.dictConfig(log_config)
    else:
        print(f"Warning: Logging config file not found at {yaml_path}")

@pytest.fixture(scope="session")
def project_dist_path(pytestconfig) -> Path:
    """
    Returns the absolute path to the project's 'dist' directory,
    resolved relative to the project root directory.
    """
    # pytestconfig.rootpath is the directory where pyproject.toml lives
    dist_dir = pytestconfig.rootpath / "out"

    # Optional: Automatically create it if your tests expect it to exist
    dist_dir.mkdir(parents=True, exist_ok=True)

    return dist_dir
