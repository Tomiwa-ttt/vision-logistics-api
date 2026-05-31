from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import contact

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contact.router, prefix="/api")
