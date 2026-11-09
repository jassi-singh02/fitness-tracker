from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import delete
from db import get_session
from enum import Enum

router = APIRouter(prefix="/exercises")

class MuscleGroup(str, Enum):
    chest = "Chest"
    back = "Back"
    shoulders = "Shoulders"
    biceps = "Biceps"
    triceps = "Triceps"
    legs = "Legs"
    core = "Core"

class MeasuredBy(str, Enum):
    time = "time"
    reps = "reps"

class LoadType(str, Enum):
    external = "external"
    bodyweight = "bodyweight"
    assisted = "assisted"

class ExerciseSecondaryMuscle(SQLModel, table=True):
    exercise_id: int = Field(foreign_key="exercise.id", primary_key=True)
    muscle_group: MuscleGroup = Field(primary_key=True)

class ExerciseBase(SQLModel):
    name: str
    muscle_group: MuscleGroup
    load_type: LoadType
    measured_by: MeasuredBy = MeasuredBy.reps
    # reps being default value ^^
    archived_at: date | None = None

class Exercise(ExerciseBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

class ExerciseCreate(ExerciseBase):
    # The model that the client sends in w/o ID
    secondary_muscle_group: list[MuscleGroup] = []

class ExerciseResponse(ExerciseBase):
    # This is the model that is sent to the client on each route
    id: int
    secondary_muscle_group: list[MuscleGroup]

# Packages up an exercise to send back to the client, including its secondary muscles.
# All the routes share this one function, so we only write it once (DRY).
def to_response(exercise: Exercise, session: Session) -> ExerciseResponse:
    # Look up the secondary muscles for this exercise
    rows = session.exec(
        select(ExerciseSecondaryMuscle.muscle_group)
        .where(ExerciseSecondaryMuscle.exercise_id == exercise.id)
    ).all()
    groups = [MuscleGroup(g) for g in rows]
    # Put the exercise and its muscles together
    return ExerciseResponse(**exercise.model_dump(), secondary_muscle_group=groups)

@router.post("", response_model=ExerciseResponse)
def add_exercise(exercise: ExerciseCreate, session: Session = Depends(get_session)):
    newExercise = Exercise(name = exercise.name, group = exercise.group)
    session.add(newExercise)
    session.commit()
    session.refresh(newExercise)
    return newExercise

@router.get("", response_model=list[ExerciseResponse])
def list_exercises(session: Session = Depends(get_session)):
    return session.exec(select(Exercise)).all()

@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(exercise_id: int, session: Session = Depends(get_session)):
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Invalid ID: Exercise not found")
    return exercise

@router.patch("/{exercise_id}", response_model=ExerciseResponse)
def edit_exercise(exercise_id: int, exercise: ExerciseCreate, session: Session = Depends(get_session)):
    stored_exercise = session.get(Exercise, exercise_id)
    
    if stored_exercise is None:
        raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

    stored_exercise.name = exercise.name
    stored_exercise.group = exercise.group

    session.add(stored_exercise)
    session.commit()
    session.refresh(stored_exercise)
    return stored_exercise

@router.delete("/{exercise_id}", response_model=ExerciseResponse)
def delete_exercise(exercise_id: int, session: Session = Depends(get_session)):
    deleted_exercise = session.get(Exercise, exercise_id)

    if deleted_exercise is None:
        raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

    session.delete(deleted_exercise)
    session.commit()
    return deleted_exercise