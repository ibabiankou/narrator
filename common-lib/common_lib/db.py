from _contextvars import ContextVar
from functools import wraps

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class DBFactory:
    def __init__(self, db_url: str):
        self._db_url = db_url
        self._engine = create_engine(db_url, pool_recycle=600)
        self._session_maker = sessionmaker(self._engine)

        self._session_ctx: ContextVar = ContextVar("current_session", default=None)

    @property
    def context(self) -> ContextVar:
        return self._session_ctx

    def new_session(self):
        return self._session_maker()

    def current_session(self) -> Session:
        session = self._session_ctx.get()
        if session is None:
            raise RuntimeError("No current session. Did you forget to use '@transactional' decorator on a method?")
        return session


def transactional(func):
    """Starts a new or nested transaction. The transaction is committed at the end of the function."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):

        db_factory = self.db_factory
        context_var = db_factory.context
        session = context_var.get()

        if session is None:
            with db_factory.new_session() as new_session:
                token = context_var.set(new_session)
                try:
                    with new_session.begin():
                        return func(self, *args, **kwargs)
                finally:
                    context_var.reset(token)
        else:
            with session.begin_nested():
                return func(self, *args, **kwargs)
    return wrapper
