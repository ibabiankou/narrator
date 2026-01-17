import logging


LOG = logging.getLogger(__name__)

class EndpointFilter(logging.Filter):
    def __init__(self, path: str, status_code: int):
        super().__init__()
        self._path = path
        self._status_code = status_code

    @staticmethod
    def add_filter(path: str, status_code: int = 200):
        logger = logging.getLogger("uvicorn.access")
        logger.addFilter(EndpointFilter(path, status_code))

    def filter(self, record: logging.LogRecord) -> bool:
        # record.args contains (IP, Method, Path, HTTP version, Status Code)

        if not record.args:
            LOG.warning("No args in log record. Skipping filtering.")
            return True

        if len(record.args) < 5:
            # This is a nice to have verification, so not a big deal if missing.
            LOG.debug("Log record does not have status code argument. Skipping that check.")
        else:
            if record.args[4] != self._status_code:
                return False

        if len(record.args) < 3:
            LOG.warning("Log record does not have path argument. Skipping filtering.")
            return True
        elif record.args[2] == self._path:
            return False

        return True
