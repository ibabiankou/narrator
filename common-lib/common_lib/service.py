import logging

from fastapi.params import Depends
from sqlalchemy.orm import Session

from common_lib.db import DBFactory

LOG = logging.getLogger(__name__)

class Service:
    """Base class for all services. Makes the service a singleton."""

    instance = None

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)

        self._db_factory = kwargs.pop('db_factory', None)
        if self._db_factory is None:
            LOG.warning("Service %s initialized without DB factory.", cls.__name__)

        return self

    def __init_subclass__(cls, **kwargs):
        """Ensure instance is initialized. Fail creation of the new instances."""
        super().__init_subclass__(**kwargs)
        original_init = cls.__init__

        def wrapped_init(self, *args, **kwargs):
            LOG.debug("Initializing service %s", cls.__name__)
            if cls.instance is not None:
                raise RuntimeError("Class is already initialized.")
            cls.instance = self
            original_init(self, *args, **kwargs)

        cls.__init__ = wrapped_init

    @classmethod
    def _instance(cls):
        if cls.instance is None:
            raise RuntimeError("Class is not initialized.")
        return cls.instance

    @classmethod
    def dep(cls):
        """Returns a dependency for the service."""
        return Depends(cls._instance)

    @property
    def db_factory(self) -> DBFactory:
        if self._db_factory is None:
            raise RuntimeError("DB Factory is not available.")
        return self._db_factory

    @property
    def db(self) -> Session:
        """Returns a current session that can be used to access the database.
        Should only be used within a '@transactional' method."""
        return self.db_factory.current_session()
