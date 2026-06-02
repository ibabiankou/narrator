from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from api.metadata.domain import Title, Identifier, AssetRef
from api.utils.db import PydanticList, PydanticType


class MetadataBase(DeclarativeBase):
    __table_args__ = {"schema": "metadata"}


class Edition(MetadataBase):
    __tablename__ = "editions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    identifiers: Mapped[list[Identifier]] = mapped_column(type_=PydanticList(Identifier))

    title: Mapped[Title] = mapped_column(type_=PydanticType(Title), nullable=False)
    description: Mapped[str] = mapped_column()
    language: Mapped[str] = mapped_column()

    cover: Mapped[Optional[AssetRef]] = mapped_column(type_=PydanticType(AssetRef), default=None)
    epub: Mapped[Optional[AssetRef]] = mapped_column(type_=PydanticType(AssetRef), default=None)


class Asset(MetadataBase):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(nullable=False)
