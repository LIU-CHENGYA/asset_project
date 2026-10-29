from fastapi import FastAPI
from .database import create_db_and_tables
app = FastAPI(
    title="Asset Management System",
    version="1.0.0"
)
