# Hubstaff Backend API

FastAPI backend service for Hubstaff clone application with JWT authentication and role-based access control.

## Features

- **FastAPI** framework with automatic API documentation
- **PostgreSQL** database with SQLAlchemy ORM
- **Alembic** for database migrations
- **JWT** authentication with access and refresh tokens
- **Role-based access control** (Admin, Manager, Employee)
- **Password hashing** with bcrypt
- **Comprehensive testing** with pytest
- **Code quality** tools (Black, isort, flake8, mypy)

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens with role-based access control (RBAC)
- **Password Hashing**: bcrypt
- **Database Migrations**: Alembic
- **Testing**: pytest with httpx
- **API Documentation**: Swagger/OpenAPI
- **Code Quality**: Black, isort, flake8, mypy

## Development Setup

### Prerequisites

- Python 3.11+
- uv (for dependency management)
- PostgreSQL

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd hubstaff-backend-api
```

2. Install dependencies:
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database configuration
```

4. Set up the database:
```bash
# Create database
createdb hubstaff

# Run migrations
uv run alembic upgrade head
```

5. Start the development server:
```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`
API documentation will be available at `http://localhost:8000/docs`

### Running Tests

```bash
uv run pytest
```

### Code Quality

Run code formatting and linting:

```bash
uv run black .
uv run isort .
uv run flake8
uv run mypy .
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - User logout

### Users (RBAC Protected)
- `GET /api/v1/users/` - Get all users (Manager/Admin only)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `POST /api/v1/users/` - Create new user (Admin only)
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user (Admin only)

### Health
- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

## User Roles

### Employee
- View own profile
- Update own profile (except role)

### Manager
- All Employee permissions
- View all users
- View any user profile

### Admin
- All Manager permissions
- Create new users
- Update any user (including roles)
- Delete users

## Environment Variables

- `POSTGRES_SERVER`: PostgreSQL server host
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `POSTGRES_PORT`: PostgreSQL port
- `SECRET_KEY`: JWT secret key
- `ENVIRONMENT`: Environment (development/production)

## Project Structure

```
hubstaff-backend-api/
├── app/
│   ├── api/          # API routes
│   │   ├── main.py   # Main API router
│   │   └── v1/       # API version 1
│   │       ├── auth.py   # Authentication endpoints
│   │       └── users.py  # User management endpoints
│   ├── core/         # Core configuration
│   │   ├── config.py    # Settings
│   │   ├── database.py  # Database config
│   │   ├── deps.py      # Dependencies
│   │   └── security.py  # Security utilities
│   ├── models/       # SQLAlchemy models
│   │   └── user.py      # User model
│   ├── schemas/      # Pydantic schemas
│   │   ├── auth.py      # Auth schemas
│   │   └── user.py      # User schemas
│   └── services/     # Business logic
│       └── user.py      # User service
├── alembic/          # Database migrations
├── tests/            # Test files
├── main.py           # FastAPI application
└── pyproject.toml    # Project configuration
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
