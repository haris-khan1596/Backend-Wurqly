import json
from typing import Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from app.models.user import User


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections grouped by user_id
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store user info for each connection
        self.connection_users: Dict[WebSocket, User] = {}
        # Project-specific connections for project updates
        self.project_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user: User):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Add to user connections
        if user.id not in self.active_connections:
            self.active_connections[user.id] = set()
        self.active_connections[user.id].add(websocket)
        
        # Store user info
        self.connection_users[websocket] = user
        
        # Send initial connection message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected successfully",
            "user_id": user.id
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.connection_users:
            user = self.connection_users[websocket]
            
            # Remove from user connections
            if user.id in self.active_connections:
                self.active_connections[user.id].discard(websocket)
                if not self.active_connections[user.id]:
                    del self.active_connections[user.id]
            
            # Remove from project connections
            for project_id, connections in self.project_connections.items():
                connections.discard(websocket)
            
            # Remove user info
            del self.connection_users[websocket]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except:
            # Connection might be closed
            self.disconnect(websocket)
    
    async def send_message_to_user(self, message: dict, user_id: int):
        """Send a message to all connections of a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id].copy():
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)
    
    async def send_message_to_project(self, message: dict, project_id: int):
        """Send a message to all users connected to a specific project"""
        if project_id in self.project_connections:
            disconnected = set()
            for connection in self.project_connections[project_id].copy():
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users"""
        disconnected = set()
        for user_id, connections in self.active_connections.items():
            for connection in connections.copy():
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    def subscribe_to_project(self, websocket: WebSocket, project_id: int):
        """Subscribe a connection to project updates"""
        if project_id not in self.project_connections:
            self.project_connections[project_id] = set()
        self.project_connections[project_id].add(websocket)
    
    def unsubscribe_from_project(self, websocket: WebSocket, project_id: int):
        """Unsubscribe a connection from project updates"""
        if project_id in self.project_connections:
            self.project_connections[project_id].discard(websocket)
            if not self.project_connections[project_id]:
                del self.project_connections[project_id]
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get the number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Get the total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_connected_users(self) -> List[int]:
        """Get list of all connected user IDs"""
        return list(self.active_connections.keys())


class WebSocketEventService:
    """Service for sending different types of real-time events"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
    
    async def notify_time_entry_started(self, user_id: int, time_entry_data: dict):
        """Notify when a user starts a time entry"""
        message = {
            "type": "time_entry_started",
            "data": time_entry_data,
            "timestamp": time_entry_data.get("start_time")
        }
        await self.manager.send_message_to_user(message, user_id)
    
    async def notify_time_entry_stopped(self, user_id: int, time_entry_data: dict):
        """Notify when a user stops a time entry"""
        message = {
            "type": "time_entry_stopped",
            "data": time_entry_data,
            "timestamp": time_entry_data.get("end_time")
        }
        await self.manager.send_message_to_user(message, user_id)
    
    async def notify_activity_update(self, user_id: int, activity_data: dict):
        """Notify about activity updates"""
        message = {
            "type": "activity_update",
            "data": activity_data,
            "timestamp": activity_data.get("timestamp")
        }
        await self.manager.send_message_to_user(message, user_id)
    
    async def notify_screenshot_taken(self, user_id: int, screenshot_data: dict):
        """Notify when a screenshot is taken"""
        message = {
            "type": "screenshot_taken",
            "data": screenshot_data,
            "timestamp": screenshot_data.get("captured_at")
        }
        await self.manager.send_message_to_user(message, user_id)
    
    async def notify_project_update(self, project_id: int, update_data: dict):
        """Notify project members about project updates"""
        message = {
            "type": "project_update",
            "project_id": project_id,
            "data": update_data,
            "timestamp": update_data.get("updated_at")
        }
        await self.manager.send_message_to_project(message, project_id)
    
    async def notify_task_update(self, project_id: int, task_data: dict):
        """Notify project members about task updates"""
        message = {
            "type": "task_update",
            "project_id": project_id,
            "data": task_data,
            "timestamp": task_data.get("updated_at")
        }
        await self.manager.send_message_to_project(message, project_id)
    
    async def notify_user_status_change(self, user_id: int, status: str):
        """Notify about user online/offline status changes"""
        message = {
            "type": "user_status_change",
            "user_id": user_id,
            "status": status,
            "timestamp": None  # Could add timestamp here
        }
        # Broadcast to all users or just to project members
        await self.manager.broadcast_to_all(message)
    
    async def send_system_notification(self, user_id: int, notification: dict):
        """Send system notifications to specific users"""
        message = {
            "type": "system_notification",
            "data": notification,
            "timestamp": notification.get("created_at")
        }
        await self.manager.send_message_to_user(message, user_id)
    
    async def send_productivity_alert(self, user_id: int, alert_data: dict):
        """Send productivity alerts"""
        message = {
            "type": "productivity_alert",
            "data": alert_data,
            "timestamp": alert_data.get("timestamp")
        }
        await self.manager.send_message_to_user(message, user_id)


# Global instances
manager = ConnectionManager()
websocket_service = WebSocketEventService(manager)
