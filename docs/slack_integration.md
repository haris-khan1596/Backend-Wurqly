# Slack Integration

This document describes the Slack integration features implemented in the Hubstaff Backend API.

## Overview

The Slack integration provides comprehensive support for:
- Webhook events handling
- Slash commands for time tracking
- OAuth authentication flow  
- Rich message notifications
- Interactive components

## Configuration

Add the following environment variables to your `.env` file:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CLIENT_ID=your-client-id
SLACK_CLIENT_SECRET=your-client-secret
SLACK_REDIRECT_URI=http://localhost:8000/api/v1/slack/auth/callback
```

## API Endpoints

### Authentication

- `GET /api/v1/slack/auth` - Initiate OAuth flow
- `GET /api/v1/slack/auth/callback` - Handle OAuth callback
- `GET /api/v1/slack/auth/success` - OAuth success page

### Webhooks

- `POST /api/v1/slack/webhook` - Handle Slack events
  - URL verification challenges
  - Message events with keyword detection
  - App mention events with help responses
  - Interactive message components

### Slash Commands

- `POST /api/v1/slack/commands` - Handle slash commands
  - `/logtime <hours> on <project> - <task>` - Log time entries
  - `/status` - View current status and hours
  - `/projects` - List user projects
  - `/tasks` - List user tasks

### Notifications

- `POST /api/v1/slack/notify/time-entry` - Send time entry notifications
- `POST /api/v1/slack/notify/project` - Send project notifications  
- `POST /api/v1/slack/notify/task` - Send task notifications

### Utilities

- `POST /api/v1/slack/send-message` - Send arbitrary messages
- `GET /api/v1/slack/health` - Check integration health

## Features

### Security
- Request signature verification using HMAC-SHA256
- Timestamp validation to prevent replay attacks
- Proper error handling and logging

### Message Formatting
- Rich Block Kit formatting for enhanced visual appeal
- Interactive buttons for approval workflows
- Ephemeral messages for private responses
- Fallback text for accessibility

### Event Handling
- Automatic keyword detection in messages
- Help responses for app mentions
- Support for various Slack event types
- Proper bot message filtering

### Slash Commands
- Natural language parsing for time entries
- Real-time command response with rich formatting
- Error handling with helpful feedback
- Support for multiple command types

## Usage Examples

### Log Time Entry
```
/logtime 2.5 hours on Project Alpha - Backend Development
```

### Check Status
```
/status
```

### List Projects
```
/projects
```

### Send Notification (API)
```json
POST /api/v1/slack/notify/time-entry
{
  "project_name": "Project Alpha",
  "task_name": "Backend Development", 
  "hours": 2.5,
  "user_name": "john.doe",
  "channel": "#general"
}
```

## Testing

The integration includes comprehensive tests with a mock Slack server:

```bash
# Run Slack integration tests
pytest tests/test_slack.py -v

# Run specific test class
pytest tests/test_slack.py::TestSlackWebhooks -v
```

## Block Kit Templates

The service includes pre-built Block Kit templates for:
- Time entry notifications with approval buttons
- Project status updates
- Task assignment notifications
- Interactive command responses

## Error Handling

- Graceful degradation when Slack is unavailable
- Proper HTTP status codes and error messages
- Comprehensive logging for debugging
- Fallback to simple text messages when blocks fail

## Security Considerations

- All webhook requests are signature-verified
- Timestamps prevent replay attacks  
- OAuth tokens should be stored securely
- Rate limiting should be implemented for production use

## Future Enhancements

- User mapping between Slack and internal users
- Custom Block Kit templates
- Advanced command parsing with natural language
- Integration with Slack workflows and shortcuts
- Support for Slack Connect and Enterprise Grid
