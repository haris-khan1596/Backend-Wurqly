"""Slack service for handling Slack integrations."""

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.core.config import settings

logger = logging.getLogger(__name__)


class SlackService:
    """Service for handling Slack integrations."""
    
    def __init__(self) -> None:
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN) if settings.SLACK_BOT_TOKEN else None
        self.signing_secret = settings.SLACK_SIGNING_SECRET
    
    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Verify Slack request signature for security."""
        if not self.signing_secret:
            logger.warning("Slack signing secret not configured")
            return False
        
        # Check if the request is not too old (5 minutes)
        if abs(time.time() - float(timestamp)) > 300:
            logger.warning("Request timestamp is too old")
            return False
        
        # Create signature
        sig_basestring = f"v0={timestamp}".encode() + b":" + body
        my_signature = "v0=" + hmac.new(
            self.signing_secret.encode(),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(my_signature, signature)
    
    def send_message(self, channel: str, text: str, **kwargs) -> Dict[str, Any]:
        """Send a message to a Slack channel."""
        if not self.client:
            raise ValueError("Slack client not initialized")
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                **kwargs
            )
            return response.data
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
            raise
    
    def send_ephemeral_message(self, channel: str, user: str, text: str, **kwargs) -> Dict[str, Any]:
        """Send an ephemeral message to a specific user in a channel."""
        if not self.client:
            raise ValueError("Slack client not initialized")
        
        try:
            response = self.client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=text,
                **kwargs
            )
            return response.data
        except SlackApiError as e:
            logger.error(f"Error sending ephemeral Slack message: {e}")
            raise
    
    def send_blocks_message(self, channel: str, blocks: list, text: str = "", **kwargs) -> Dict[str, Any]:
        """Send a message with blocks to a Slack channel."""
        if not self.client:
            raise ValueError("Slack client not initialized")
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=text,
                **kwargs
            )
            return response.data
        except SlackApiError as e:
            logger.error(f"Error sending blocks message: {e}")
            raise
    
    def update_message(self, channel: str, ts: str, text: str = "", blocks: Optional[list] = None, **kwargs) -> Dict[str, Any]:
        """Update an existing message."""
        if not self.client:
            raise ValueError("Slack client not initialized")
        
        try:
            response = self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks,
                **kwargs
            )
            return response.data
        except SlackApiError as e:
            logger.error(f"Error updating Slack message: {e}")
            raise
    
    def delete_message(self, channel: str, ts: str) -> Dict[str, Any]:
        """Delete a message."""
        if not self.client:
            raise ValueError("Slack client not initialized")
        
        try:
            response = self.client.chat_delete(
                channel=channel,
                ts=ts
            )
            return response.data
        except SlackApiError as e:
            logger.error(f"Error deleting Slack message: {e}")
            raise
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information."""
        if not self.client:
            raise ValueError("Slack client not initialized")
        
        try:
            response = self.client.users_info(user=user_id)
            return response.data
        except SlackApiError as e:
            logger.error(f"Error getting user info: {e}")
            raise
    
    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information."""
        if not self.client:
            raise ValueError("Slack client not initialized")
        
        try:
            response = self.client.conversations_info(channel=channel_id)
            return response.data
        except SlackApiError as e:
            logger.error(f"Error getting channel info: {e}")
            raise
    
    def create_time_entry_blocks(self, project_name: str, task_name: str, hours: float, user_name: str) -> list:
        """Create Slack blocks for time entry notification."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⏱️ *New Time Entry Logged*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*User:*\n{user_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*\n{project_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Task:*\n{task_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Hours:*\n{hours:.2f}"
                    }
                ]
            }
        ]
    
    def create_project_blocks(self, project_name: str, description: str, action: str) -> list:
        """Create Slack blocks for project notifications."""
        action_emoji = "🆕" if action == "created" else "✏️" if action == "updated" else "🗑️"
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{action_emoji} *Project {action.title()}*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*\n{project_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{description}"
                    }
                ]
            }
        ]
    
    def create_task_blocks(self, task_name: str, project_name: str, action: str, assignee: Optional[str] = None) -> list:
        """Create Slack blocks for task notifications."""
        action_emoji = "📋" if action == "created" else "✅" if action == "completed" else "🔄"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{action_emoji} *Task {action.title()}*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Task:*\n{task_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Project:*\n{project_name}"
                    }
                ]
            }
        ]
        
        if assignee:
            blocks[1]["fields"].append({
                "type": "mrkdwn",
                "text": f"*Assignee:*\n{assignee}"
            })
        
        return blocks


# Global instance
slack_service = SlackService()
