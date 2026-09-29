import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.routes import router as auth_router
from app.routers.sections import router as sections_router
from app.routers import profile, posts, universities
from app.routers.likes import router as likes_router
from app.routers.comments import router as comments_router
from app.core.ws_manager import ws_manager

app = FastAPI()

app.include_router(auth_router)
app.include_router(profile.router)
app.include_router(likes_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(posts.router, prefix="/api/posts")
app.include_router(universities.router, prefix="/api/universities")

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"message": "API up and running"}

@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open, ignore any ping from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    import asyncio
    ws_manager.loop = asyncio.get_running_loop()
