# --------------------------------------------------------------------------
# --- IMPORTS: All necessary libraries for the pipeline ---
# --------------------------------------------------------------------------
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# --------------------------------------------------------------------------
# --- Part 1: DATABASE CONNECTION (The "Output" End of the Pipeline) ---
# This section defines how your pipeline connects to a database.
# The "Database Person" on your team would typically provide this.
# --------------------------------------------------------------------------

# The connection string for a simple SQLite database file.
SQLALCHEMY_DATABASE_URL = "sqlite:///./registration_pipeline.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# A factory for creating database sessions (conversations).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# A base class for database models.
Base = declarative_base()

# A placeholder database model. The "Database Person" would define the final version.
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# Create the actual database tables from the model definition above.
Base.metadata.create_all(bind=engine)

# --------------------------------------------------------------------------
# --- Part 2: DATA CONTRACT (The "Input" End of the Pipeline) ---
# These models define the data structure you expect from the frontend.
# This is your "agreement" with the "Frontend Person".
# --------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Data you EXPECT to receive from the frontend."""
    username: str
    email: EmailStr  # Pydantic automatically validates the email format.
    password: str

class UserResponse(BaseModel):
    """Data you PROMISE to send back to the frontend on success."""
    id: int
    username: str
    email: EmailStr
    class Config:
        from_attributes = True

# --------------------------------------------------------------------------
# --- Part 3: THE PIPELINE LOGIC (Your Core Responsibility) ---
# This is the main application that receives, processes, and saves the data.
# --------------------------------------------------------------------------

app = FastAPI()

# Password hashing setup (a crucial security step in your pipeline).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependency to get a database session for a single request.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user_pipeline(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    This is the main connectivity pipeline. It takes data from the frontend,
    processes it, and sends it to the database.
    """
    print(f"Pipeline received data for email: {user_data.email}")

    # --- PROCESSING STEP 1: Check for duplicates ---
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        print("Processing failed: Email already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    # --- PROCESSING STEP 2: Secure the password ---
    hashed_password = pwd_context.hash(user_data.password)
    print("Processing: Password has been securely hashed.")

    # --- PROCESSING STEP 3: Format data for the database ---
    new_user_record = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )

    # --- FINAL STEP: Send data to the database ---
    db.add(new_user_record)
    db.commit()
    db.refresh(new_user_record) # Get the new ID from the database.
    print(f"Pipeline finished: User {new_user_record.username} saved with ID {new_user_record.id}.")

    return new_user_record