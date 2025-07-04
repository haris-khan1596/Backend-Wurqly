import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from main import app

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpassword"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_manager(db):
    manager = User(
        email="manager@example.com",
        username="manager",
        hashed_password=get_password_hash("managerpassword"),
        full_name="Manager User",
        role=UserRole.MANAGER,
        is_active=True,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


class TestAuthentication:
    def test_login_success(self, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_username(self, test_user):
        """Test login with invalid username"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "wronguser", "password": "testpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_invalid_password(self, test_user):
        """Test login with invalid password"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_with_email(self, test_user):
        """Test login using email instead of username"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test@example.com", "password": "testpassword"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_inactive_user(self, test_user, db):
        """Test login with inactive user"""
        test_user.is_active = False
        db.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]

    def test_register_success(self, db):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "newpassword",
                "full_name": "New User",
                "role": "employee"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["role"] == "employee"
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, test_user):
        """Test registration with duplicate email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "newuser",
                "password": "newpassword",
                "full_name": "New User"
            }
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_duplicate_username(self, test_user):
        """Test registration with duplicate username"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "testuser",
                "password": "newpassword",
                "full_name": "New User"
            }
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_refresh_token_success(self, test_user):
        """Test successful token refresh"""
        # First login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword"}
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_invalid(self):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    def test_get_current_user(self, test_user):
        """Test getting current user info"""
        token = create_access_token(subject=str(test_user.id))
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_logout(self):
        """Test logout endpoint"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]


class TestRoleBasedAccess:
    def test_admin_can_access_all_users(self, test_admin, test_user):
        """Test that admin can access all users"""
        token = create_access_token(subject=str(test_admin.id))
        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 2  # At least admin and test_user

    def test_manager_can_access_all_users(self, test_manager, test_user):
        """Test that manager can access all users"""
        token = create_access_token(subject=str(test_manager.id))
        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_employee_cannot_access_all_users(self, test_user):
        """Test that employee cannot access all users"""
        token = create_access_token(subject=str(test_user.id))
        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_user_can_view_own_profile(self, test_user):
        """Test that user can view their own profile"""
        token = create_access_token(subject=str(test_user.id))
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id

    def test_user_cannot_view_other_profile(self, test_user, test_admin):
        """Test that employee cannot view other user's profile"""
        token = create_access_token(subject=str(test_user.id))
        response = client.get(
            f"/api/v1/users/{test_admin.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_manager_can_view_any_profile(self, test_manager, test_user):
        """Test that manager can view any user's profile"""
        token = create_access_token(subject=str(test_manager.id))
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_admin_can_create_user(self, test_admin):
        """Test that admin can create new user"""
        token = create_access_token(subject=str(test_admin.id))
        response = client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "newpassword",
                "full_name": "New User",
                "role": "employee"
            }
        )
        assert response.status_code == 200

    def test_non_admin_cannot_create_user(self, test_user):
        """Test that non-admin cannot create user"""
        token = create_access_token(subject=str(test_user.id))
        response = client.post(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "newpassword",
                "full_name": "New User"
            }
        )
        assert response.status_code == 403

    def test_user_can_update_own_profile(self, test_user):
        """Test that user can update their own profile"""
        token = create_access_token(subject=str(test_user.id))
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"full_name": "Updated Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    def test_user_cannot_update_own_role(self, test_user):
        """Test that user cannot update their own role"""
        token = create_access_token(subject=str(test_user.id))
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "admin"}
        )
        assert response.status_code == 200
        data = response.json()
        # Role should remain unchanged
        assert data["role"] == "employee"

    def test_admin_can_update_any_user(self, test_admin, test_user):
        """Test that admin can update any user"""
        token = create_access_token(subject=str(test_admin.id))
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "manager"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "manager"

    def test_admin_can_delete_user(self, test_admin, test_user):
        """Test that admin can delete user"""
        token = create_access_token(subject=str(test_admin.id))
        response = client.delete(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    def test_admin_cannot_delete_self(self, test_admin):
        """Test that admin cannot delete their own account"""
        token = create_access_token(subject=str(test_admin.id))
        response = client.delete(
            f"/api/v1/users/{test_admin.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]

    def test_non_admin_cannot_delete_user(self, test_user, test_manager):
        """Test that non-admin cannot delete user"""
        token = create_access_token(subject=str(test_user.id))
        response = client.delete(
            f"/api/v1/users/{test_manager.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
