# Student Management Backend System
# Requirements: pip install fastapi uvicorn sqlalchemy python-multipart python-jose[cryptography] passlib[bcrypt] python-decouple

import os
import shutil
from datetime import datetime, timedelta
from typing import Optional, List , Any
from pathlib import Path

import os
from urllib.parse import quote_plus
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship , joinedload
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
import json
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-key")

# Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
UPLOAD_DIR = "student_upload_files"

# Ensure upload directory exists
Path(UPLOAD_DIR).mkdir(exist_ok=True)


#------------------------------------------------------------------------------------------------------#


# Database Configuration
def get_database_url():
    # Use NeonDB DATABASE_URL
    NEON_DB_URL = os.getenv("NEON_DATABASE_URL")
    if NEON_DB_URL:
        return NEON_DB_URL  

    # Fallback to local PostgreSQL config
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "admin123")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "student_management")

    encoded_password = quote_plus(DB_PASSWORD)
    return f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Final database URL
SQLALCHEMY_DATABASE_URL = get_database_url()

# Create SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"sslmode": "require"}, pool_pre_ping=True,)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()
#------------------------------------------------------------------------------------------------------#

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# Database Models
class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(15), nullable=False)
    gender = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    academic_details = relationship("AcademicDetails", back_populates="student", cascade="all, delete-orphan")
    documents = relationship("Documents", back_populates="student", cascade="all, delete-orphan")

class AcademicDetails(Base):
    __tablename__ = "academic_details"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    college_name = Column(String(200), nullable=False)
    department = Column(String(100), nullable=False)
    graduation_year = Column(Integer, nullable=False, index=True)
    cgpa = Column(Float, nullable=False)
    backlogs = Column(Integer, default=0)
    
    # Relationships
    student = relationship("Student", back_populates="academic_details")

class Documents(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # resume, id_proof, etc.
    file_path = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=func.now())
    
    # Relationships
    student = relationship("Student", back_populates="documents")

#------------------------------------------------------------------------------------------------------#

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class AcademicDetailsBase(BaseModel):
    college_name: str
    department: str
    graduation_year: int
    cgpa: float
    backlogs: int = 0

class AcademicDetailsResponse(AcademicDetailsBase):
    id: int
    student_id: int
    
    class Config:
        orm_mode = True

class DocumentResponse(BaseModel):
    id: int
    student_id: int
    doc_type: str
    file_path: str
    uploaded_at: datetime
    
    class Config:
        orm_mode = True  

class StudentBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    gender: str

class StudentCreate(StudentBase):
    academic_details: AcademicDetailsBase

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    academic_details: Optional[AcademicDetailsBase] = None

class StudentResponse(StudentBase):
    id: int
    created_at: datetime
    academic_details: List[AcademicDetailsResponse] = []
    documents: List[DocumentResponse] = []
    
    class Config:
        orm_mode = True 

class Token(BaseModel):
    access_token: str
    token_type: str
    
#------------------------------------------------------------------------------------------------------# 
    
# FastAPI App
app = FastAPI(
    title="Student Management API",
    description="Backend of student onboarding and tracking system",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#------------------------------------------------------------------------------------------------------#

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication Functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Authentication Endpoints

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
        <head>
            <title>Student Management System</title>
        </head>
        <body>
            <h1>Welcome to the Student Management System API</h1>
            <p>Visit <a href="/docs">/docs</a> to explore the API.</p>
        </body>
    </html>
    """
    
    
@app.post("/auth/login", response_model=Token)
async def login():
    """
    Simple login endpoint - in production, implement proper user authentication
    For demo purposes, returns a token for admin access
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "admin"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

#------------------------------------------------------------------------------------------------------#

# Student CRUD Operations
@app.post("/students", response_model=StudentResponse)
async def create_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Create a new student with academic details"""
    # Check if email already exists
    existing_student = db.query(Student).filter(Student.email == student.email).first()
    if existing_student:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create student
    db_student = Student(
        name=student.name,
        email=student.email,
        phone=student.phone,
        gender=student.gender
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    
    # Create academic details
    db_academic = AcademicDetails(
        student_id=db_student.id,
        college_name=student.academic_details.college_name,
        department=student.academic_details.department,
        graduation_year=student.academic_details.graduation_year,
        cgpa=student.academic_details.cgpa,
        backlogs=student.academic_details.backlogs
    )
    db.add(db_academic)
    db.commit()
    db.refresh(db_academic)
    
    return db_student


@app.get("/students", response_model=List[StudentResponse])
async def get_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Get all students with pagination"""
    students = db.query(Student)\
        .options(joinedload(Student.academic_details))\
        .options(joinedload(Student.documents))\
        .offset(skip)\
        .limit(limit)\
        .all()
    return students

#------------------------------------------------------------------------------------------------------#

# Search and Filter Endpoints

@app.get("/students/search", response_model=List[StudentResponse])
async def search_students(
    college: Optional[str] = Query(None, description="Filter by college name"),
    year: Optional[int] = Query(None, description="Filter by graduation year"),
    department: Optional[str] = Query(None, description="Filter by department"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Search and filter students by college, graduation year, and department"""
    
    # Start with base query, join AcademicDetails, and add eager loading
    query = db.query(Student).join(AcademicDetails).options(
        joinedload(Student.academic_details),
        joinedload(Student.documents)
    )
    
    # Apply filters
    if college:
        query = query.filter(AcademicDetails.college_name.ilike(f"%{college}%"))
    if year:
        query = query.filter(AcademicDetails.graduation_year == year)
    if department:
        query = query.filter(AcademicDetails.department.ilike(f"%{department}%"))
    
    # Apply pagination
    students = query.offset(skip).limit(limit).all()
    return students
#-----------------------------------------#


@app.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Get a specific student's full record"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@app.put("/students/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    student_update: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Update student or academic details"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Update student fields
    update_data = student_update.dict(exclude_unset=True, exclude={"academic_details"})
    for field, value in update_data.items():
        setattr(student, field, value)
    
    # Update academic details
    if student_update.academic_details:
        academic = db.query(AcademicDetails).filter(AcademicDetails.student_id == student_id).first()
        if academic:
            academic_data = student_update.academic_details.dict()
            for field, value in academic_data.items():
                setattr(academic, field, value)
    
    db.commit()
    db.refresh(student)
    return student

@app.delete("/students/{student_id}")
async def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Delete student and cascade delete related data"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Delete associated files
    for doc in student.documents:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    
    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}

#------------------------------------------------------------------------------------------------------#

#file  upload endpoints
@app.post("/students/{student_id}/upload")
async def upload_documents(
    student_id: int,
    resume: UploadFile = File(...),  # Required
    id_proof: Optional[UploadFile] = File(None),  # Optional
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Upload student documents (resume required, ID proof optional)"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    uploaded_files = []

    # Upload resume
    if resume:
        resume_filename = f"student_{student_id}_resume_{resume.filename}"
        resume_path = os.path.join(UPLOAD_DIR, resume_filename)
        with open(resume_path, "wb") as buffer:
            shutil.copyfileobj(resume.file, buffer)

        db_doc = Documents(
            student_id=student_id,
            doc_type="resume",
            file_path=resume_path
        )
        db.add(db_doc)
        uploaded_files.append({"type": "resume", "filename": resume.filename})

    # Upload ID proof
    if id_proof:
        id_filename = f"student_{student_id}_id_{id_proof.filename}"
        id_path = os.path.join(UPLOAD_DIR, id_filename)
        with open(id_path, "wb") as buffer:
            shutil.copyfileobj(id_proof.file, buffer)

        db_doc = Documents(
            student_id=student_id,
            doc_type="id_proof",
            file_path=id_path
        )
        db.add(db_doc)
        uploaded_files.append({"type": "id_proof", "filename": id_proof.filename})

    db.commit()
    return {"message": "Files uploaded successfully", "files": uploaded_files}


@app.get("/students/{student_id}/documents/{doc_id}/download")
async def download_document(
    student_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """Download a specific document"""
    document = db.query(Documents).filter(
        Documents.id == doc_id,
        Documents.student_id == student_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        document.file_path,
        filename=f"{document.doc_type}_{student_id}.pdf"
    )


#-------------------------------------------------------------------------------------------------------------------------------------------#
# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Initialize with dummy data
@app.on_event("startup")
async def create_dummy_data():
    """Create dummy data on startup"""
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(Student).count() > 0:
        db.close()
        return
    
#-------------------------------------------------------------------------------------------------------------------------------------------# 
    # Dummy data
    dummy_students = [
        {
            "student": {
                "name": "Rahul Sharma",
                "email": "rahul.sharma@email.com",
                "phone": "+91-9876543210",
                "gender": "Male"
            },
            "academic": {
                "college_name": "Indian Institute of Technology Delhi",
                "department": "Computer Science",
                "graduation_year": 2024,
                "cgpa": 8.5,
                "backlogs": 0
            }
        },
        {
            "student": {
                "name": "Priya Patel",
                "email": "priya.patel@email.com",
                "phone": "+91-9876543211",
                "gender": "Female"
            },
            "academic": {
                "college_name": "Delhi University",
                "department": "Information Technology",
                "graduation_year": 2025,
                "cgpa": 9.1,
                "backlogs": 0
            }
        },
        {
            "student": {
                "name": "Amit Kumar",
                "email": "amit.kumar@email.com",
                "phone": "+91-9876543212",
                "gender": "Male"
            },
            "academic": {
                "college_name": "Jawaharlal Nehru University",
                "department": "Electronics",
                "graduation_year": 2024,
                "cgpa": 7.8,
                "backlogs": 1
            }
        },
        {
            "student": {
                "name": "Sneha Gupta",
                "email": "sneha.gupta@email.com",
                "phone": "+91-9876543213",
                "gender": "Female"
            },
            "academic": {
                "college_name": "Indian Institute of Technology Mumbai",
                "department": "Mechanical Engineering",
                "graduation_year": 2025,
                "cgpa": 8.9,
                "backlogs": 0
            }
        },
        {
            "student": {
                "name": "Vikram Singh",
                "email": "vikram.singh@email.com",
                "phone": "+91-9876543214",
                "gender": "Male"
            },
            "academic": {
                "college_name": "Bangalore University",
                "department": "Computer Science",
                "graduation_year": 2024,
                "cgpa": 8.2,
                "backlogs": 0
            }
        }
    ]
    
    additional_students = []
    colleges = ["BITS Pilani", "VIT University", "SRM University", "Manipal University", "Anna University"]
    departments = ["Computer Science", "Information Technology", "Electronics", "Mechanical Engineering", "Civil Engineering"]
    names = ["Rajesh", "Kavya", "Arjun", "Deepika", "Manoj", "Pooja", "Sanjay", "Ritu", "Ashish", "Meera"]
    
    for i in range(20):
        additional_students.append({
            "student": {
                "name": f"{names[i % len(names)]} {['Sharma', 'Patel', 'Kumar', 'Singh', 'Gupta'][i % 5]}",
                "email": f"student{i+6}@email.com",
                "phone": f"+91-987654{3215 + i}",
                "gender": "Male" if i % 2 == 0 else "Female"
            },
            "academic": {
                "college_name": colleges[i % len(colleges)],
                "department": departments[i % len(departments)],
                "graduation_year": 2024 + (i % 3),
                "cgpa": round(7.0 + (i % 20) * 0.15, 1),
                "backlogs": i % 3
            }
        })
    
    all_students = dummy_students + additional_students
    
    try:
        for student_data in all_students:
            # Create student
            db_student = Student(**student_data["student"])
            db.add(db_student)
            db.commit()
            db.refresh(db_student)
            
            # Create academic details
            db_academic = AcademicDetails(
                student_id=db_student.id,
                **student_data["academic"]
            )
            db.add(db_academic)
        
        db.commit()
        print("Dummy data created successfully!")
        
    except Exception as e:
        print(f"Error creating dummy data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)