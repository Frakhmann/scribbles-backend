from typing import List, Optional
from fastapi import WebSocket
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        try:
            self.loop = asyncio.get_running_loop()
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(dead)

ws_manager = ConnectionManager()

def broadcast_sync(message: dict):
    try:
        if ws_manager.loop and ws_manager.loop.is_running():
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(message), ws_manager.loop)
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(ws_manager.broadcast(message))
                else:
                    loop.run_until_complete(ws_manager.broadcast(message))
            except Exception:
                pass
    except Exception as e:
        print(f'[WS] broadcast_sync error: {e}')
