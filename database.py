from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./labelbox.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True)  # type: ignore
    description = Column(String)  # type: ignore

    def get_project_data_count(self, db: Session):
        return db.query(ProjectData).filter(ProjectData.project_id == self.id).count()

    def get_project_annotated_data_count(self, db: Session):
        return (
            db.query(ProjectData)
            .filter(
                ProjectData.project_id == self.id, ProjectData.annotation_data != None
            )
            .count()
        )


class ProjectData(Base):
    __tablename__ = "project_data"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer)  # type: ignore
    filename = Column(String)  # type: ignore
    file_path = Column(String)  # type: ignore
    annotation_data = Column(String, nullable=True)  # type: ignore


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
