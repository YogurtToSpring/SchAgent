from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv

app = FastAPI()

router = APIRouter(prefix="/api")

DATABASE = os.getenv("DATABASE_URL", "class.db")

def init_db():
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS class(
            name TEXT         
        )
    """)