from fastapi import FastAPI, File, UploadFile, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os
import uuid

from database import get_db, Project, ProjectData, engine, Base

app = FastAPI()

# Mount static and template directories
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Ensure uploads directory exists
os.makedirs("static/uploads", exist_ok=True)


def get_single_project_details(db: Session, p: Project):
    return {
        "project_id": p.id,
        "project_name": p.project_name,
        "total_uploaded": p.get_project_data_count(db),
        "total_annotated": p.get_project_annotated_data_count(db),
    }


def get_projects(db: Session, search: str | None = None):
    query = db.query(Project)
    if search:
        query = query.filter(Project.project_name.ilike(f"%{search}%"))

    projects = query.all()

    projects = db.query(Project).all()
    result = []
    for p in projects:
        result.append(get_single_project_details(db, p))
    return result


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "index.html", {"request": request, "projects": get_projects(db)}
    )


@app.post("/create-project")
def create_project(
    request: Request,
    project_name: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db),
):
    new_project = Project(project_name=project_name, description=description)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return templates.TemplateResponse(
        "project-list.html",
        {"request": request, "projects": get_projects(db)},
    )


@app.post("/search-projects")
def search_projects(
    request: Request, project_search: str = Form(None), db: Session = Depends(get_db)
):
    if not project_search:
        projects = get_projects(db)
    else:
        projects = [
            p
            for p in get_projects(db)
            if project_search.lower() in p["project_name"].lower()
        ]

    return templates.TemplateResponse(
        "project-list.html", {"request": request, "projects": projects}
    )


@app.post("/upload-image/{project_id}")
async def upload_image(
    request: Request,
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = f"static/uploads/{unique_filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    project = db.query(Project).where(Project.id == project_id).first()
    if project is None:
        raise RuntimeError("Invalid Project ID")

    new_annotation_data = ProjectData(
        project_id=project_id, filename=file.filename, file_path=file_path
    )
    db.add(new_annotation_data)
    db.commit()
    db.refresh(new_annotation_data)

    project_details = get_single_project_details(db, project)
    project_details["filename"] = unique_filename

    return templates.TemplateResponse(
        "project-card.html",
        {"request": request, "project": project_details},
    )


@app.get("/annotate/{project_id}")
def annotate_project(request: Request, project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()

    images = (
        db.query(ProjectData)
        .filter(
            ProjectData.project_id == project_id,
            ProjectData.annotation_data == None,
        )
        .all()
    )

    return templates.TemplateResponse(
        "annotate.html", {"request": request, "project": project, "images": images}
    )


@app.post("/save-annotation/{image_id}")
def save_annotation(
    image_id: int, annotation_data: str = Form(...), db: Session = Depends(get_db)
):
    image = db.query(ProjectData).filter(ProjectData.id == image_id).first()
    if image:
        image.annotation_data = annotation_data
        db.commit()

    return {"status": "success"}


# Startup event to create tables
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
