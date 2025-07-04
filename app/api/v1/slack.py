"""Slack API endpoints."""

import json
import logging
from typing import Any, Dict, Union
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from slack_sdk.oauth import OAuthStateUtils
from slack_sdk.web import WebClient
from slack_sdk.errors import SlackApiError

from app.core.config import settings
from app.schemas.slack import (
    SlackCommand,
    SlackCommandResponse,
    SlackEventChallenge,
    SlackEventWrapper,
    SlackMessageRequest,
    SlackMessageResponse,
    SlackOAuthRequest,
    SlackOAuthResponse,
    SlackWebhookPayload,
    SlackTimeEntryNotification,
    SlackProjectNotification,
    SlackTaskNotification,
    SlackError,
)
from app.services.slack import slack_service

logger = logging.getLogger(__name__)
router = APIRouter()


# Slack OAuth endpoints
@router.get("/auth", response_model=Dict[str, str])
async def slack_auth_redirect() -> Dict[str, str]:
    """Redirect to Slack OAuth authorization."""
    if not settings.SLACK_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Slack OAuth not configured"
        )
    
    state = OAuthStateUtils.generate_state()
    oauth_url = (
        f"https://slack.com/oauth/v2/authorize?"
        f"client_id={settings.SLACK_CLIENT_ID}&"
        f"scope=chat:write,channels:read,users:read,commands&"
        f"redirect_uri={settings.SLACK_REDIRECT_URI}&"
        f"state={state}"
    )
    
    return {
        "auth_url": oauth_url,
        "state": state
    }


@router.get("/auth/callback")
async def slack_auth_callback(code: str, state: str = None) -> RedirectResponse:
    """Handle Slack OAuth callback."""
    if not settings.SLACK_CLIENT_ID or not settings.SLACK_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Slack OAuth not configured"
        )
    
    try:
        client = WebClient()
        response = client.oauth_v2_access(
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=settings.SLACK_REDIRECT_URI
        )
        
        if not response["ok"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth failed: {response.get('error', 'Unknown error')}"
            )
        
        # Store the access token securely (implement your storage logic)
        # For now, we'll just log it (don't do this in production)
        logger.info(f"Slack OAuth successful for team: {response['team']['name']}")
        
        # Redirect to success page
        return RedirectResponse(url="/slack/auth/success")
        
    except SlackApiError as e:
        logger.error(f"Slack OAuth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth failed: {e.response['error']}"
        )


@router.get("/auth/success")
async def slack_auth_success() -> Dict[str, str]:
    """OAuth success page."""
    return {"message": "Slack integration configured successfully!"}


# Slack webhook endpoint
@router.post("/webhook")
async def slack_webhook(request: Request) -> Union[Dict[str, str], Response]:
    """Handle Slack webhook events."""
    body = await request.body()
    
    # Get headers for signature verification
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    # Verify signature
    if not slack_service.verify_slack_signature(body, timestamp, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    
    # Handle events
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type")
        
        logger.info(f"Received Slack event: {event_type}")
        
        # Handle different event types
        if event_type == "message":
            await handle_message_event(event)
        elif event_type == "app_mention":
            await handle_mention_event(event)
        
        return Response(status_code=200)
    
    # Handle interactive components
    if payload.get("type") == "interactive_message":
        await handle_interactive_message(payload)
        return Response(status_code=200)
    
    return Response(status_code=200)


async def handle_message_event(event: Dict[str, Any]) -> None:
    """Handle incoming message events."""
    if event.get("subtype") == "bot_message":
        return  # Ignore bot messages
    
    text = event.get("text", "")
    channel = event.get("channel")
    user = event.get("user")
    
    # Simple keyword detection for time tracking
    if "time" in text.lower() and "log" in text.lower():
        try:
            slack_service.send_ephemeral_message(
                channel=channel,
                user=user,
                text="To log time, use the `/logtime` command. Example: `/logtime 2.5 hours on Project A - Task 1`"
            )
        except Exception as e:
            logger.error(f"Error sending ephemeral message: {e}")


async def handle_mention_event(event: Dict[str, Any]) -> None:
    """Handle app mention events."""
    text = event.get("text", "")
    channel = event.get("channel")
    
    # Simple help response
    if "help" in text.lower():
        help_text = """
        🤖 *Hubstaff Bot Commands*
        
        • `/logtime <hours> <project> <task>` - Log time entry
        • `/status` - Check your current status
        • `/projects` - List your projects
        • `/tasks` - List your tasks
        
        Mention me with "help" to see this message again!
        """
        
        try:
            slack_service.send_message(
                channel=channel,
                text=help_text
            )
        except Exception as e:
            logger.error(f"Error sending help message: {e}")


async def handle_interactive_message(payload: Dict[str, Any]) -> None:
    """Handle interactive message components."""
    actions = payload.get("actions", [])
    
    for action in actions:
        if action.get("name") == "time_entry_approve":
            # Handle time entry approval
            logger.info(f"Time entry approved: {action.get('value')}")
        elif action.get("name") == "time_entry_reject":
            # Handle time entry rejection
            logger.info(f"Time entry rejected: {action.get('value')}")


# Slack slash commands endpoint
@router.post("/commands", response_model=SlackCommandResponse)
async def slack_commands(request: Request) -> SlackCommandResponse:
    """Handle Slack slash commands."""
    form_data = await request.form()
    
    # Get headers for signature verification
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    body = await request.body()
    
    # Verify signature
    if not slack_service.verify_slack_signature(body, timestamp, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    try:
        command_data = SlackCommand(**dict(form_data))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid command data: {e}"
        )
    
    command = command_data.command
    text = command_data.text
    user_name = command_data.user_name
    
    # Handle different commands
    if command == "/logtime":
        return await handle_logtime_command(text, user_name)
    elif command == "/status":
        return await handle_status_command(user_name)
    elif command == "/projects":
        return await handle_projects_command(user_name)
    elif command == "/tasks":
        return await handle_tasks_command(user_name)
    else:
        return SlackCommandResponse(
            text=f"Unknown command: {command}",
            response_type="ephemeral"
        )


async def handle_logtime_command(text: str, user_name: str) -> SlackCommandResponse:
    """Handle /logtime command."""
    if not text.strip():
        return SlackCommandResponse(
            text="Please provide time details. Example: `/logtime 2.5 hours on Project A - Task 1`",
            response_type="ephemeral"
        )
    
    # Simple parsing (in real implementation, you'd want more robust parsing)
    try:
        parts = text.lower().split(" on ")
        if len(parts) != 2:
            raise ValueError("Invalid format")
        
        hours_part = parts[0].replace("hours", "").replace("hour", "").strip()
        hours = float(hours_part)
        
        project_task = parts[1].strip()
        
        # Create blocks for rich formatting
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⏱️ *Time Entry Submitted*\n\n*Hours:* {hours}\n*Details:* {project_task}\n*User:* {user_name}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve"
                        },
                        "style": "primary",
                        "action_id": "approve_time_entry"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reject"
                        },
                        "style": "danger",
                        "action_id": "reject_time_entry"
                    }
                ]
            }
        ]
        
        return SlackCommandResponse(
            text=f"Time entry logged: {hours} hours on {project_task}",
            blocks=blocks,
            response_type="ephemeral"
        )
        
    except (ValueError, IndexError):
        return SlackCommandResponse(
            text="Invalid format. Please use: `/logtime <hours> on <project> - <task>`",
            response_type="ephemeral"
        )


async def handle_status_command(user_name: str) -> SlackCommandResponse:
    """Handle /status command."""
    # In real implementation, fetch user's current status from database
    status_text = f"📊 *Status for {user_name}*\n\n• Currently tracking: Project Alpha - Backend Development\n• Today's hours: 6.5\n• This week: 32.5 hours"
    
    return SlackCommandResponse(
        text=status_text,
        response_type="ephemeral"
    )


async def handle_projects_command(user_name: str) -> SlackCommandResponse:
    """Handle /projects command."""
    # In real implementation, fetch user's projects from database
    projects_text = f"📋 *Projects for {user_name}*\n\n• Project Alpha (Active)\n• Project Beta (Paused)\n• Project Gamma (Completed)"
    
    return SlackCommandResponse(
        text=projects_text,
        response_type="ephemeral"
    )


async def handle_tasks_command(user_name: str) -> SlackCommandResponse:
    """Handle /tasks command."""
    # In real implementation, fetch user's tasks from database
    tasks_text = f"✅ *Tasks for {user_name}*\n\n• Backend API development (In Progress)\n• Database optimization (Todo)\n• Code review (Completed)"
    
    return SlackCommandResponse(
        text=tasks_text,
        response_type="ephemeral"
    )


# Notification endpoints
@router.post("/notify/time-entry", response_model=SlackMessageResponse)
async def notify_time_entry(notification: SlackTimeEntryNotification) -> SlackMessageResponse:
    """Send time entry notification to Slack."""
    try:
        blocks = slack_service.create_time_entry_blocks(
            project_name=notification.project_name,
            task_name=notification.task_name,
            hours=notification.hours,
            user_name=notification.user_name
        )
        
        response = slack_service.send_blocks_message(
            channel=notification.channel,
            blocks=blocks,
            text=f"Time entry logged: {notification.hours} hours by {notification.user_name}"
        )
        
        return SlackMessageResponse(**response)
        
    except Exception as e:
        logger.error(f"Error sending time entry notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )


@router.post("/notify/project", response_model=SlackMessageResponse)
async def notify_project(notification: SlackProjectNotification) -> SlackMessageResponse:
    """Send project notification to Slack."""
    try:
        blocks = slack_service.create_project_blocks(
            project_name=notification.project_name,
            description=notification.description,
            action=notification.action
        )
        
        response = slack_service.send_blocks_message(
            channel=notification.channel,
            blocks=blocks,
            text=f"Project {notification.action}: {notification.project_name}"
        )
        
        return SlackMessageResponse(**response)
        
    except Exception as e:
        logger.error(f"Error sending project notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )


@router.post("/notify/task", response_model=SlackMessageResponse)
async def notify_task(notification: SlackTaskNotification) -> SlackMessageResponse:
    """Send task notification to Slack."""
    try:
        blocks = slack_service.create_task_blocks(
            task_name=notification.task_name,
            project_name=notification.project_name,
            action=notification.action,
            assignee=notification.assignee
        )
        
        response = slack_service.send_blocks_message(
            channel=notification.channel,
            blocks=blocks,
            text=f"Task {notification.action}: {notification.task_name}"
        )
        
        return SlackMessageResponse(**response)
        
    except Exception as e:
        logger.error(f"Error sending task notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )


# Utility endpoints
@router.post("/send-message", response_model=SlackMessageResponse)
async def send_message(message: SlackMessageRequest) -> SlackMessageResponse:
    """Send a message to Slack."""
    try:
        if message.blocks:
            response = slack_service.send_blocks_message(
                channel=message.channel,
                blocks=message.blocks,
                text=message.text
            )
        else:
            response = slack_service.send_message(
                channel=message.channel,
                text=message.text
            )
        
        return SlackMessageResponse(**response)
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/health")
async def slack_health() -> Dict[str, Any]:
    """Check Slack integration health."""
    if not settings.SLACK_BOT_TOKEN:
        return {
            "status": "not_configured",
            "message": "Slack bot token not configured"
        }
    
    try:
        # Test API connection
        response = slack_service.client.auth_test()
        return {
            "status": "healthy",
            "team": response.data.get("team"),
            "user": response.data.get("user"),
            "bot_id": response.data.get("bot_id")
        }
    except Exception as e:
        logger.error(f"Slack health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
