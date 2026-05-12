from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

from api.procurement.domain import IdMatch
from api.utils.db import PydanticList


class ProcurementBase(DeclarativeBase):
    __table_args__ = {"schema": "procurement"}


class EpubFile(ProcurementBase):
    __tablename__ = "epub_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    file_name: Mapped[str]
    file_hash: Mapped[str] = mapped_column(unique=True)
    file_size_bytes: Mapped[int]

    raw_metadata: Mapped[dict] = mapped_column(type_=JSONB)

    id_matches: Mapped[list[IdMatch]] = mapped_column(type_=PydanticList(IdMatch))


class MetadataId(ProcurementBase):
    __tablename__ = "metadata_ids"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_file: Mapped[int] = mapped_column(ForeignKey("procurement.epub_files.id"))
    type: Mapped[str]
    value: Mapped[str] = mapped_column(unique=True)
