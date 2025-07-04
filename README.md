# Hubstaff Backend API

## Purpose

This is the backend API service for the Hubstaff clone application. It provides RESTful endpoints for time tracking, project management, team collaboration, and user authentication.

## Features

- User authentication and authorization
- Time tracking and timesheets
- Project and task management
- Team and organization management
- Screenshot and activity monitoring
- Reporting and analytics
- Integration APIs

## Technology Stack

- **Framework**: FastAPI/Django/Flask (to be determined)
- **Database**: PostgreSQL
- **Authentication**: JWT tokens
- **File Storage**: AWS S3 or local storage
- **Task Queue**: Celery with Redis
- **API Documentation**: Swagger/OpenAPI

## Local Setup Instructions

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis (for task queue)
- Virtual environment tool (venv/virtualenv)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/hubstaff-backend-api.git
   cd hubstaff-backend-api
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Set up the database:
   ```bash
   # Create database
   createdb hubstaff_dev
   
   # Run migrations
   python manage.py migrate
   ```

6. Start Redis (for task queue):
   ```bash
   redis-server
   ```

7. Start the development server:
   ```bash
   python manage.py runserver
   # Or for FastAPI: uvicorn main:app --reload
   ```

8. (Optional) Start Celery worker:
   ```bash
   celery -A hubstaff_backend worker --loglevel=info
   ```

### API Documentation

Once the server is running, visit:
- Development: `http://localhost:8000/docs`
- API endpoints: `http://localhost:8000/api/v1/`

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
