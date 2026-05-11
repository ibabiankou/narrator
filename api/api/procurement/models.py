from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase



class ProcurementBase(DeclarativeBase):
    __table_args__ = {"schema": "procurement"}


class EpubFile(ProcurementBase):
    __tablename__ = "epub_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    file_name: Mapped[str]
    file_hash: Mapped[str]
    file_size_bytes: Mapped[int]

    # TODO Which model to use for metadata? Simple dictionary? Something more specific?
