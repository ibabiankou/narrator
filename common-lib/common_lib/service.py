import logging

from fastapi.params import Depends

LOG = logging.getLogger(__name__)

class Service:
    """Base class for all services. Makes the service a singleton."""

    instance = None

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
