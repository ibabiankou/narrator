import datetime
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


load_dotenv()
engine = create_engine(os.getenv("PG_URL"))

def get_session():
    with Session(engine) as session:
        yield session

class Base(DeclarativeBase):
    pass


class TempFile(Base):
    __tablename__ = "temp_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    file_name: Mapped[str]
    file_path: Mapped[str]
    upload_time: Mapped[datetime.datetime]
