from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.orm import sessionmaker

sqlite_file_name = "pos.db"

connect_args={"check_same_thread": False}
engine = create_engine(f"sqlite:///{sqlite_file_name}",connect_args=connect_args,echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
