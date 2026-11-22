from fastapi import APIRouter, HTTPException, Depends
from pydantic import model_validator
from datetime import date
from sqlmodel import SQLModel, Field, Session, select, col
from sqlalchemy import delete
from db import get_session
from enum import Enum

router = APIRouter()

class SetEntryBase(SQLModel):
    exercise_id:
    workout_id:
    weight:
    reps:
    duration_seconds:
    notes:

class SetEntry(SetEntryBase, table=True)


class LogSet():


class SetEntryResponse():


class SetEntryUpdate():
