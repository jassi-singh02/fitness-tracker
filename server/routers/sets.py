from fastapi import APIRouter, HTTPException, Depends
from pydantic import model_validator
from datetime import date
from sqlmodel import SQLModel, Field, Session, select, col
from sqlalchemy import delete
from db import get_session
from enum import Enum
from routers.exercises import Exercise, LoadType, MeasuredBy
from routers.workouts import Workout

router = APIRouter()

class SetEntryBase(SQLModel):
    weight: float | None = None
    reps: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, gt=0)
    note: str | None = None

class SetEntry(SetEntryBase, table=True):
    __tablename__ = "set_entry"
    id: int | None = Field(default=None, primary_key=True)
    exercise_id: int = Field(foreign_key="exercise.id", ondelete="RESTRICT")
    workout_id: int = Field(foreign_key="workout.id", ondelete="CASCADE")

class SetEntryCreate(SetEntryBase):
    exercise_id: int

class SetEntryResponse(SetEntryBase):
    id: int
    exercise_id: int
    workout_id: int

class SetEntryUpdate(SQLModel):
    weight: float | None = None
    reps: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, gt=0)
    note: str | None = None

# helper function to check if the set matches input for the exercise
def check_exercise_fields(exercise: Exercise, weight: float | None, reps: int | None, duration_seconds: float | None):

    # Check if exercised is archived, no sets added to archived exercises
    if exercise.archived_at is not None:
        raise HTTPException(status_code=422, detail="Exercise is archived, can't add new set")
    
    # check exercise measuredBy - elegant isn't it
    if exercise.measured_by == MeasuredBy.reps:
        needed, extra = "reps", "duration_seconds"
    else:
        needed, extra = "duration_seconds", "reps"

    values = {"reps": reps, "duration_seconds": duration_seconds}

    if values[needed] is None or values[extra] is not None:
        raise HTTPException(
            status_code=422,
            detail=f"This exercise is measured by {needed}, so send {needed} only (not {extra})",
        )

    # check exercise load_type - i decided that weight needs to have a value for external
    if (exercise.load_type == LoadType.external) and (weight is None):
        raise HTTPException(status_code=422, detail="Weight needs to have a value")

    if (exercise.load_type == LoadType.external) and (weight <= 0):
        raise HTTPException(status_code=422, detail="External load_type needs weight greater than 0")

# helper function to convert bodyweight sets with no weight to 0
def default_bodyweight(exercise: Exercise, weight: float | None) -> float | None:
    if exercise.load_type == LoadType.bodyweight and weight is None:
        return 0.0
    return weight
    

@router.post("/workouts/{workout_id}/sets", response_model=SetEntryResponse)
def create_set(entry: SetEntryCreate, workout_id: int, session: Session = Depends(get_session)):

    setExercise = session.get(Exercise, entry.exercise_id)

    if session.get(Workout, workout_id) is None:
        raise HTTPException(status_code=404, detail="Invalid ID, workout not found")

    if setExercise is None:
        raise HTTPException(status_code=422, detail="Invalid input, exercise not found")

    # set validation checks for isArchived, loadType, and measuredBy
    weight = default_bodyweight(setExercise, entry.weight)
    check_exercise_fields(setExercise, weight, entry.reps, entry.duration_seconds)

    # add it to the database after validating it as an entry
    newEntry = SetEntry.model_validate(entry, update={"workout_id": workout_id, "weight": weight})
    session.add(newEntry)
    session.commit()
    session.refresh(newEntry)
    return newEntry

#@router.get("/sets/{set_id}", response_model=SetEntryResponse)
# check in ...

#@router.get("/exercises/{exercise_id}/sets", response_model=SetEntryResponse)

#@router.patch("/sets/{set_id}", response_model=SetEntryResponse)

#@router.delete("/sets/{set_id}", response_model=SetEntryResponse)