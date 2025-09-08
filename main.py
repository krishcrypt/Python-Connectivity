import os
import uuid
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./registration_pipeline.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

UPLOAD_DIRECTORY = "uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


class Registration(Base):
    __tablename__ = "registrations"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

class RegistrationForm(BaseModel):
    name: str
    email: EmailStr
    student_id: str
    branch: str
    year: int
    division: str
    roll_no: int
    transaction_id: str

class RegistrationResponse(RegistrationForm):
    id: int
    screenshot_filename: str
    class Config:
        from_attributes = True

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register/", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def create_registration_pipeline(
    db: Session = Depends(get_db),
  
    name: str = Form(...),
    email: EmailStr = Form(...),
    student_id: str = Form(...),
    branch: str = Form(...),
    year: int = Form(...),
    division: str = Form(...),
    roll_no: int = Form(...),
    transaction_id: str = Form(...),
    screenshot: UploadFile = File(...)
):
 
    print(f"Pipeline received registration request for email: {email}")

 
    existing_registration = db.query(Registration).filter(
        (Registration.email == email) | (Registration.student_id == student_id)
    ).first()

    if existing_registration:
        print("Processing failed: Email or Student ID already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A registration with this Email or Student ID already exists."
        )

  
    if not screenshot.filename:
        raise HTTPException(status_code=400, detail="No screenshot file was uploaded.")

   
    unique_id = uuid.uuid4()
    file_extension = os.path.splitext(screenshot.filename)[1]
    unique_filename = f"{unique_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)

    try:
        
        contents = await screenshot.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        print(f"Processing: Screenshot saved as '{unique_filename}'")
    except Exception as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="There was an error uploading the file.")
    finally:
        await screenshot.close()


   
    new_registration = Registration(
        name=name,
        email=email,
        student_id=student_id,
        branch=branch,
        year=year,
        division=division,
        roll_no=roll_no,
        transaction_id=transaction_id,
        screenshot_filename=unique_filename 
    )

    
    db.add(new_registration)
    db.commit()
    db.refresh(new_registration)
    print(f"Pipeline finished: Registration saved with ID {new_registration.id}.")

    return new_registration