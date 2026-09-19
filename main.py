from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes import query

app = FastAPI(
    title="EMR Natural Language Query Interface",
    description="Query patient data in plain English — no SQL required.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(query.router, prefix="/api", tags=["Query"])


@app.get("/")
def root():
    return FileResponse("static/index.html")
