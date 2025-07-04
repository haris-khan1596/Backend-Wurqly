"""Slack schemas for request/response models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SlackEvent(BaseModel):
    """Slack event schema."""
    type: str
    user: Optional[str] = None
    text: Optional[str] = None
    ts: Optional[str] = None
    channel: Optional[str] = None
    event_ts: Optional[str] = None


class SlackEventChallenge(BaseModel):
    """Slack event challenge schema."""
    token: str
    challenge: str
    type: str


class SlackEventWrapper(BaseModel):
    """Slack event wrapper schema."""
    token: str
    team_id: str
    api_app_id: str
    event: SlackEvent
    type: str
    event_id: str
    event_time: int
    authorizations: Optional[List[Dict[str, Any]]] = None
    is_ext_shared_channel: Optional[bool] = None
    event_context: Optional[str] = None


class SlackCommand(BaseModel):
    """Slack slash command schema."""
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: str
    trigger_id: str
    api_app_id: str


class SlackCommandResponse(BaseModel):
    """Slack command response schema."""
    response_type: str = "ephemeral"  # ephemeral or in_channel
    text: str
    blocks: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    thread_ts: Optional[str] = None
    replace_original: Optional[bool] = None
    delete_original: Optional[bool] = None


class SlackInteraction(BaseModel):
    """Slack interaction schema."""
    type: str
    user: Dict[str, Any]
    api_app_id: str
    token: str
    container: Optional[Dict[str, Any]] = None
    trigger_id: str
    team: Dict[str, Any]
    enterprise: Optional[Dict[str, Any]] = None
    is_enterprise_install: Optional[bool] = None
    channel: Optional[Dict[str, Any]] = None
    message: Optional[Dict[str, Any]] = None
    view: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    response_url: Optional[str] = None


class SlackMessageRequest(BaseModel):
    """Request schema for sending Slack messages."""
    channel: str
    text: str
    blocks: Optional[List[Dict[str, Any]]] = None
    thread_ts: Optional[str] = None
    reply_broadcast: Optional[bool] = None
    unfurl_links: Optional[bool] = None
    unfurl_media: Optional[bool] = None


class SlackMessageResponse(BaseModel):
    """Response schema for Slack messages."""
    ok: bool
    channel: str
    ts: str
    message: Dict[str, Any]
    warning: Optional[str] = None
    error: Optional[str] = None


class SlackOAuthRequest(BaseModel):
    """Slack OAuth request schema."""
    code: str
    state: Optional[str] = None


class SlackOAuthResponse(BaseModel):
    """Slack OAuth response schema."""
    ok: bool
    access_token: str
    token_type: str
    scope: str
    bot_user_id: str
    app_id: str
    team: Dict[str, Any]
    enterprise: Optional[Dict[str, Any]] = None
    authed_user: Dict[str, Any]
    incoming_webhook: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SlackWebhookPayload(BaseModel):
    """Generic Slack webhook payload."""
    token: Optional[str] = None
    team_id: Optional[str] = None
    api_app_id: Optional[str] = None
    type: Optional[str] = None
    event: Optional[Dict[str, Any]] = None
    challenge: Optional[str] = None


class SlackTimeEntryNotification(BaseModel):
    """Schema for time entry notification."""
    project_name: str
    task_name: str
    hours: float
    user_name: str
    channel: str


class SlackProjectNotification(BaseModel):
    """Schema for project notification."""
    project_name: str
    description: str
    action: str  # created, updated, deleted
    channel: str


class SlackTaskNotification(BaseModel):
    """Schema for task notification."""
    task_name: str
    project_name: str
    action: str  # created, updated, completed
    assignee: Optional[str] = None
    channel: str


class SlackUserInfo(BaseModel):
    """Slack user information schema."""
    id: str
    name: str
    real_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    is_bot: bool = False
    is_admin: bool = False
    is_owner: bool = False


class SlackChannelInfo(BaseModel):
    """Slack channel information schema."""
    id: str
    name: str
    is_channel: bool = True
    is_private: bool = False
    is_im: bool = False
    is_mpim: bool = False
    is_group: bool = False
    topic: Optional[str] = None
    purpose: Optional[str] = None
    num_members: Optional[int] = None


class SlackError(BaseModel):
    """Slack error response schema."""
    ok: bool = False
    error: str
    details: Optional[str] = None
