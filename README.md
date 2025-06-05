![image](https://github.com/user-attachments/assets/c40a02fe-b01f-479e-95ad-e9b9465b197e)🎓 Student Management System Backend
A comprehensive FastAPI-based student management system with JWT authentication, CRUD operations, file upload functionality, and interactive API documentation.
✨ Features

🔐 JWT Authentication - Secure user registration and login
👥 Student Management - Complete CRUD operations for student records
📚 Academic Details - Manage college, department, graduation year, CGPA
📄 Document Upload - Upload and manage student documents
🔍 Advanced Search - Filter students by college, year, department
📖 Interactive Documentation - Swagger UI for easy API testing
⚡ Fast & Efficient - Built with FastAPI for high performance

🛠️ Tech Stack

Backend: FastAPI, Python 3.8+
Database: PostgreSQL with SQLAlchemy ORM
Authentication: JWT (JSON Web Tokens)
Documentation: Swagger UI (Auto-generated)
File Handling: Python Multipart

## Prerequisites

- Python 3.8+
- PostgreSQL
- Git

## Setup & Run

### 1. Clone & Install
```bash
git clone <your-repository-url>
cd student-management-system
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```


### 2. Environment Configuration
Create `.env` file:
```env
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/student_management
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Run Application
```bash
uvicorn main:app --reload
```

## Access Points

- **API:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **API Documentation:** http://localhost:8000/redoc

## Quick Test

1. Go to http://localhost:8000/docs
2. Register user via **POST /auth/register**
3. Login via **POST /auth/login** (copy the token)
4. Click **"Authorize"** → Enter `Bearer your_token`
5. Test **POST /students** to create a student

## API Endpoints

### Authentication
- `POST /auth/register` - Register user
- `POST /auth/login` - Get JWT token

### Students
- `GET /students` - List all students
- `POST /students` - Create student
- `GET /students/{id}` - Get student by ID
- `PUT /students/{id}` - Update student
- `DELETE /students/{id}` - Delete student
- `GET /students/search` - Search students

### Documents
- `POST /students/{id}/documents` - Upload documents
- `GET /students/{id}/documents` - Get documents

## Sample Student Data
```json
{
  "name": "Uday ",
  "email": "Uday@example.com",
  "phone": "9876543210",
  "gender": "Male",
  "academic_details": {
    "college_name": "GGSIPU Delhi",
    "department": "Computer Science",
    "graduation_year": 2025,
    "cgpa": 8.5,
    "backlogs": 0
  }
}
```

## Troubleshooting

- **Database Error:** Check PostgreSQL is running and credentials in `.env`
- **Module Error:** Ensure virtual environment is activated and dependencies installed
- **422 Error:** Check request format in Swagger UI


