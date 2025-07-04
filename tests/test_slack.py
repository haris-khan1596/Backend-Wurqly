"""Tests for Slack integration endpoints."""

import hashlib
import hmac
import json
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from slack_sdk.errors import SlackApiError

from app.core.config import settings
from app.services.slack import SlackService, slack_service
from main import app


class MockSlackWebClient:
    """Mock Slack WebClient for testing."""
    
    def __init__(self, token: str = None):
        self.token = token
    
    def chat_postMessage(self, **kwargs):
        """Mock chat.postMessage."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "channel": kwargs.get("channel", "C1234567890"),
            "ts": "1234567890.123456",
            "message": {
                "text": kwargs.get("text", ""),
                "user": "U1234567890",
                "ts": "1234567890.123456"
            }
        }
        return mock_response
    
    def chat_postEphemeral(self, **kwargs):
        """Mock chat.postEphemeral."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "message_ts": "1234567890.123456"
        }
        return mock_response
    
    def chat_update(self, **kwargs):
        """Mock chat.update."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "channel": kwargs.get("channel", "C1234567890"),
            "ts": kwargs.get("ts", "1234567890.123456"),
            "text": kwargs.get("text", ""),
            "message": {}
        }
        return mock_response
    
    def chat_delete(self, **kwargs):
        """Mock chat.delete."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "channel": kwargs.get("channel", "C1234567890"),
            "ts": kwargs.get("ts", "1234567890.123456")
        }
        return mock_response
    
    def users_info(self, **kwargs):
        """Mock users.info."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "user": {
                "id": kwargs.get("user", "U1234567890"),
                "name": "testuser",
                "real_name": "Test User",
                "profile": {
                    "email": "test@example.com",
                    "image_72": "https://example.com/avatar.jpg"
                }
            }
        }
        return mock_response
    
    def conversations_info(self, **kwargs):
        """Mock conversations.info."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "channel": {
                "id": kwargs.get("channel", "C1234567890"),
                "name": "general",
                "is_channel": True,
                "topic": {"value": "General discussion"},
                "purpose": {"value": "General channel"},
                "num_members": 10
            }
        }
        return mock_response
    
    def auth_test(self):
        """Mock auth.test."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "url": "https://testteam.slack.com/",
            "team": "Test Team",
            "user": "testbot",
            "team_id": "T1234567890",
            "user_id": "U0987654321",
            "bot_id": "B1234567890"
        }
        return mock_response
    
    def oauth_v2_access(self, **kwargs):
        """Mock oauth.v2.access."""
        mock_response = Mock()
        mock_response.data = {
            "ok": True,
            "access_token": "xoxb-test-token",
            "token_type": "bot",
            "scope": "chat:write,channels:read,users:read,commands",
            "bot_user_id": "U0987654321",
            "app_id": "A1234567890",
            "team": {
                "id": "T1234567890",
                "name": "Test Team"
            },
            "authed_user": {
                "id": "U1234567890"
            }
        }
        return mock_response


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_slack_client():
    """Mock Slack client fixture."""
    return MockSlackWebClient()


@pytest.fixture
def slack_signature():
    """Generate valid Slack signature for testing."""
    def _generate_signature(body: str, timestamp: str = None) -> tuple:
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        signing_secret = "test_signing_secret"
        sig_basestring = f"v0={timestamp}:{body}".encode()
        signature = "v0=" + hmac.new(
            signing_secret.encode(),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    return _generate_signature


class TestSlackService:
    """Test SlackService class."""
    
    def test_slack_service_initialization(self):
        """Test SlackService initialization."""
        service = SlackService()
        assert service.signing_secret == settings.SLACK_SIGNING_SECRET
    
    def test_verify_slack_signature_valid(self):
        """Test valid Slack signature verification."""
        service = SlackService()
        service.signing_secret = "test_signing_secret"
        
        body = b"test_body"
        timestamp = str(int(time.time()))
        
        sig_basestring = f"v0={timestamp}:".encode() + body
        signature = "v0=" + hmac.new(
            service.signing_secret.encode(),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        assert service.verify_slack_signature(body, timestamp, signature) is True
    
    def test_verify_slack_signature_invalid(self):
        """Test invalid Slack signature verification."""
        service = SlackService()
        service.signing_secret = "test_signing_secret"
        
        body = b"test_body"
        timestamp = str(int(time.time()))
        signature = "v0=invalid_signature"
        
        assert service.verify_slack_signature(body, timestamp, signature) is False
    
    def test_verify_slack_signature_old_timestamp(self):
        """Test signature verification with old timestamp."""
        service = SlackService()
        service.signing_secret = "test_signing_secret"
        
        body = b"test_body"
        timestamp = str(int(time.time()) - 400)  # 400 seconds ago (> 300 limit)
        
        sig_basestring = f"v0={timestamp}:".encode() + body
        signature = "v0=" + hmac.new(
            service.signing_secret.encode(),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        assert service.verify_slack_signature(body, timestamp, signature) is False
    
    @patch('app.services.slack.WebClient')
    def test_send_message(self, mock_web_client):
        """Test sending Slack message."""
        mock_client = MockSlackWebClient()
        mock_web_client.return_value = mock_client
        
        service = SlackService()
        service.client = mock_client
        
        response = service.send_message(
            channel="C1234567890",
            text="Test message"
        )
        
        assert response["ok"] is True
        assert response["channel"] == "C1234567890"
    
    def test_create_time_entry_blocks(self):
        """Test creating time entry blocks."""
        service = SlackService()
        
        blocks = service.create_time_entry_blocks(
            project_name="Test Project",
            task_name="Test Task",
            hours=2.5,
            user_name="testuser"
        )
        
        assert len(blocks) == 2
        assert blocks[0]["type"] == "section"
        assert "New Time Entry Logged" in blocks[0]["text"]["text"]
        assert blocks[1]["type"] == "section"
        assert "fields" in blocks[1]


class TestSlackWebhooks:
    """Test Slack webhook endpoints."""
    
    @patch.object(slack_service, 'verify_slack_signature')
    def test_webhook_url_verification(self, mock_verify, client, slack_signature):
        """Test webhook URL verification challenge."""
        mock_verify.return_value = True
        
        payload = {
            "token": "test_token",
            "challenge": "test_challenge",
            "type": "url_verification"
        }
        
        signature, timestamp = slack_signature(json.dumps(payload))
        
        response = client.post(
            "/api/v1/slack/webhook",
            json=payload,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {"challenge": "test_challenge"}
    
    @patch.object(slack_service, 'verify_slack_signature')
    @patch.object(slack_service, 'send_ephemeral_message')
    def test_webhook_message_event(self, mock_send, mock_verify, client, slack_signature):
        """Test webhook message event handling."""
        mock_verify.return_value = True
        mock_send.return_value = {"ok": True}
        
        payload = {
            "token": "test_token",
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "I need to log time",
                "channel": "C1234567890",
                "user": "U1234567890",
                "ts": "1234567890.123456"
            }
        }
        
        signature, timestamp = slack_signature(json.dumps(payload))
        
        response = client.post(
            "/api/v1/slack/webhook",
            json=payload,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature
            }
        )
        
        assert response.status_code == 200
        mock_send.assert_called_once()
    
    @patch.object(slack_service, 'verify_slack_signature')
    @patch.object(slack_service, 'send_message')
    def test_webhook_mention_event(self, mock_send, mock_verify, client, slack_signature):
        """Test webhook app mention event handling."""
        mock_verify.return_value = True
        mock_send.return_value = {"ok": True}
        
        payload = {
            "token": "test_token",
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "<@U0987654321> help",
                "channel": "C1234567890",
                "user": "U1234567890",
                "ts": "1234567890.123456"
            }
        }
        
        signature, timestamp = slack_signature(json.dumps(payload))
        
        response = client.post(
            "/api/v1/slack/webhook",
            json=payload,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature
            }
        )
        
        assert response.status_code == 200
        mock_send.assert_called_once()
    
    def test_webhook_invalid_signature(self, client):
        """Test webhook with invalid signature."""
        payload = {
            "token": "test_token",
            "type": "url_verification",
            "challenge": "test_challenge"
        }
        
        response = client.post(
            "/api/v1/slack/webhook",
            json=payload,
            headers={
                "X-Slack-Request-Timestamp": str(int(time.time())),
                "X-Slack-Signature": "v0=invalid_signature"
            }
        )
        
        assert response.status_code == 401


class TestSlackCommands:
    """Test Slack slash commands."""
    
    @patch.object(slack_service, 'verify_slack_signature')
    def test_logtime_command_valid(self, mock_verify, client, slack_signature):
        """Test valid /logtime command."""
        mock_verify.return_value = True
        
        form_data = {
            "token": "test_token",
            "team_id": "T1234567890",
            "team_domain": "testteam",
            "channel_id": "C1234567890",
            "channel_name": "general",
            "user_id": "U1234567890",
            "user_name": "testuser",
            "command": "/logtime",
            "text": "2.5 hours on Project Alpha - Backend Development",
            "response_url": "https://hooks.slack.com/commands/1234567890",
            "trigger_id": "123456789.987654321.abcd1234567890",
            "api_app_id": "A1234567890"
        }
        
        # Convert form data to URL-encoded format
        body = "&".join([f"{k}={v}" for k, v in form_data.items()])
        signature, timestamp = slack_signature(body)
        
        response = client.post(
            "/api/v1/slack/commands",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "Time entry logged" in response_data["text"]
        assert response_data["response_type"] == "ephemeral"
        assert "blocks" in response_data
    
    @patch.object(slack_service, 'verify_slack_signature')
    def test_logtime_command_invalid_format(self, mock_verify, client, slack_signature):
        """Test /logtime command with invalid format."""
        mock_verify.return_value = True
        
        form_data = {
            "token": "test_token",
            "team_id": "T1234567890",
            "team_domain": "testteam",
            "channel_id": "C1234567890",
            "channel_name": "general",
            "user_id": "U1234567890",
            "user_name": "testuser",
            "command": "/logtime",
            "text": "invalid format",
            "response_url": "https://hooks.slack.com/commands/1234567890",
            "trigger_id": "123456789.987654321.abcd1234567890",
            "api_app_id": "A1234567890"
        }
        
        body = "&".join([f"{k}={v}" for k, v in form_data.items()])
        signature, timestamp = slack_signature(body)
        
        response = client.post(
            "/api/v1/slack/commands",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "Invalid format" in response_data["text"]
    
    @patch.object(slack_service, 'verify_slack_signature')
    def test_status_command(self, mock_verify, client, slack_signature):
        """Test /status command."""
        mock_verify.return_value = True
        
        form_data = {
            "token": "test_token",
            "team_id": "T1234567890",
            "team_domain": "testteam",
            "channel_id": "C1234567890",
            "channel_name": "general",
            "user_id": "U1234567890",
            "user_name": "testuser",
            "command": "/status",
            "text": "",
            "response_url": "https://hooks.slack.com/commands/1234567890",
            "trigger_id": "123456789.987654321.abcd1234567890",
            "api_app_id": "A1234567890"
        }
        
        body = "&".join([f"{k}={v}" for k, v in form_data.items()])
        signature, timestamp = slack_signature(body)
        
        response = client.post(
            "/api/v1/slack/commands",
            data=form_data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "Status for testuser" in response_data["text"]


class TestSlackAuth:
    """Test Slack OAuth endpoints."""
    
    @patch.object(settings, 'SLACK_CLIENT_ID', 'test_client_id')
    def test_auth_redirect(self, client):
        """Test Slack auth redirect."""
        response = client.get("/api/v1/slack/auth")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "auth_url" in response_data
        assert "state" in response_data
        assert "slack.com/oauth/v2/authorize" in response_data["auth_url"]
    
    def test_auth_redirect_not_configured(self, client):
        """Test auth redirect when not configured."""
        with patch.object(settings, 'SLACK_CLIENT_ID', None):
            response = client.get("/api/v1/slack/auth")
            
            assert response.status_code == 501
            assert "not configured" in response.json()["detail"]
    
    @patch('app.api.v1.slack.WebClient')
    @patch.object(settings, 'SLACK_CLIENT_ID', 'test_client_id')
    @patch.object(settings, 'SLACK_CLIENT_SECRET', 'test_client_secret')
    def test_auth_callback_success(self, mock_web_client, client):
        """Test successful OAuth callback."""
        mock_client = MockSlackWebClient()
        mock_web_client.return_value = mock_client
        
        response = client.get(
            "/api/v1/slack/auth/callback?code=test_code&state=test_state"
        )
        
        assert response.status_code == 200  # Redirect response
    
    def test_auth_success(self, client):
        """Test auth success page."""
        response = client.get("/api/v1/slack/auth/success")
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]


class TestSlackNotifications:
    """Test Slack notification endpoints."""
    
    @patch.object(slack_service, 'send_blocks_message')
    def test_notify_time_entry(self, mock_send, client):
        """Test time entry notification."""
        mock_send.return_value = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {}
        }
        
        notification_data = {
            "project_name": "Test Project",
            "task_name": "Test Task",
            "hours": 2.5,
            "user_name": "testuser",
            "channel": "C1234567890"
        }
        
        response = client.post(
            "/api/v1/slack/notify/time-entry",
            json=notification_data
        )
        
        assert response.status_code == 200
        assert response.json()["ok"] is True
        mock_send.assert_called_once()
    
    @patch.object(slack_service, 'send_blocks_message')
    def test_notify_project(self, mock_send, client):
        """Test project notification."""
        mock_send.return_value = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {}
        }
        
        notification_data = {
            "project_name": "Test Project",
            "description": "Test project description",
            "action": "created",
            "channel": "C1234567890"
        }
        
        response = client.post(
            "/api/v1/slack/notify/project",
            json=notification_data
        )
        
        assert response.status_code == 200
        assert response.json()["ok"] is True
        mock_send.assert_called_once()


class TestSlackUtilities:
    """Test Slack utility endpoints."""
    
    @patch.object(slack_service, 'send_message')
    def test_send_message(self, mock_send, client):
        """Test send message endpoint."""
        mock_send.return_value = {
            "ok": True,
            "channel": "C1234567890",
            "ts": "1234567890.123456",
            "message": {}
        }
        
        message_data = {
            "channel": "C1234567890",
            "text": "Test message"
        }
        
        response = client.post(
            "/api/v1/slack/send-message",
            json=message_data
        )
        
        assert response.status_code == 200
        assert response.json()["ok"] is True
        mock_send.assert_called_once()
    
    @patch.object(slack_service, 'client')
    def test_health_check_healthy(self, mock_client, client):
        """Test Slack health check when healthy."""
        mock_client.auth_test.return_value = MockSlackWebClient().auth_test()
        
        with patch.object(settings, 'SLACK_BOT_TOKEN', 'test_token'):
            response = client.get("/api/v1/slack/health")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "healthy"
    
    def test_health_check_not_configured(self, client):
        """Test health check when not configured."""
        with patch.object(settings, 'SLACK_BOT_TOKEN', None):
            response = client.get("/api/v1/slack/health")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "not_configured"
