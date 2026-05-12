from typing import Type

from pydantic import BaseModel
from sqlalchemy import TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class PydanticList(TypeDecorator):
    """Allows storing a list of Pydantic models in a JSONB column.

       Example:
            class Product(Base):
                __tablename__ = "products"
                id: Mapped[int] = mapped_column(primary_key=True)
                # Define the column using our custom decorator
                tags: Mapped[list[Tag]] = mapped_column(PydanticList(Tag), server_default="[]")
    """
    impl = JSONB
    cache_ok = True

    def __init__(self, model: Type[BaseModel], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def process_bind_param(self, value, dialect):
        # Convert List[Model] -> List[Dict] for Postgres
        if value is not None:
            return [m.model_dump() if isinstance(m, BaseModel) else m for m in value]
        return value

    def process_result_value(self, value, dialect):
        # Convert List[Dict] -> List[Model] for Python
        if value is not None:
            return [self.model.model_validate(item) for item in value]
        return value
