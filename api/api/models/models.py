import datetime
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

# TODO: move configuration to .env file and use dotenv
engine = create_engine("postgresql://narrator:narrator@localhost:5432/narrator")

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
