from typing import List

from sqlalchemy import ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, BIT, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, validates

from api.procurement.domain import IdMatch, ImageMatch, ContentMatch
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
    cover_matches: Mapped[list[ImageMatch]] = mapped_column(type_=PydanticList(ImageMatch))
    content_matches: Mapped[list[ContentMatch]] = mapped_column(type_=PydanticList(ContentMatch))


class MetadataId(ProcurementBase):
    __tablename__ = "metadata_ids"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_file: Mapped[int] = mapped_column(ForeignKey("procurement.epub_files.id"))
    type: Mapped[str]
    value: Mapped[str] = mapped_column(unique=True)


class ImagePhash(ProcurementBase):
    __tablename__ = "image_phashes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_file: Mapped[int] = mapped_column(ForeignKey("procurement.epub_files.id"))
    image_name: Mapped[str]
    phash: Mapped[str] = mapped_column(BIT(64))


class ContentSignature(ProcurementBase):
    __tablename__ = "content_signatures"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_file: Mapped[int] = mapped_column(ForeignKey("procurement.epub_files.id"))
    # The full 128-integer signature (for Jaccard calculation)
    full_signature: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger))

    # 8 Bands of 16 integers each (for LSH search)
    band1: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)
    band2: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)
    band3: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)
    band4: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)
    band5: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)
    band6: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)
    band7: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)
    band8: Mapped[List[int]] = mapped_column(type_=ARRAY(BigInteger), index=True)

    @validates("full_signature")
    def _split_signature(self, key, value):
        if value is None or len(value) != 128:
            raise ValueError("full_signature must be a list of exactly 128 integers.")

        # Automatically populate the bands
        self.band1 = value[0:16]
        self.band2 = value[16:32]
        self.band3 = value[32:48]
        self.band4 = value[48:64]
        self.band5 = value[64:80]
        self.band6 = value[80:96]
        self.band7 = value[96:112]
        self.band8 = value[112:128]

        return value
