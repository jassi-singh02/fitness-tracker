from fastapi import APIRouter, HTTPException, Depends
from pydantic import model_validator
from datetime import date
from sqlmodel import SQLModel, Field, Session, select, col
from sqlalchemy import delete
from db import get_session
from enum import Enum

router = APIRouter(prefix="/workout")

class Workout(SQLModel):
    performed_on: datetime
    notes: str

