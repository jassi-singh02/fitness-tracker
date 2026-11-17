from fastapi import APIRouter, HTTPException, Depends
from pydantic import model_validator
from datetime import date
from sqlmodel import SQLModel, Field, Session, select, col
from sqlalchemy import delete
from db import get_session
from enum import Enum

router = APIRouter(prefix="/workouts")

# base model top inherit from
class WorkoutBase(SQLModel):
    performed_on: date = Field(default_factory=date.today)
    notes: str | None = None

# SQL table model for workouts
class Workout(WorkoutBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

# the request body that the client sends to create a workout
class WorkoutCreate(WorkoutBase):
    pass

# the json response that we give to the client
class WorkoutResponse(WorkoutBase):
    id: int

# the request body for PATCH to edit workouts
class WorkoutUpdate(SQLModel):
    performed_on: date | None = None
    notes: str | None = None

@router.post("", response_model = WorkoutResponse)
def create_workout(workout: WorkoutCreate, session: Session = Depends(get_session)):
    newWorkout = Workout.model_validate(workout)
    session.add(newWorkout)
    session.commit()
    session.refresh(newWorkout)
    return newWorkout

@router.get("/{workout_id}", response_model=WorkoutResponse)
def get_workout(workout_id: int, session: Session = Depends(get_session)):
    workout = session.get(Workout, workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail="Invalid ID, workout not found")
    return workout

# this query can give you all workouts in a list or a filter for the performed_on date
@router.get("", response_model=list[WorkoutResponse])
def list_workouts(start: date | None = None, end: date | None = None, session: Session = Depends(get_session)):
    query = select(Workout) # translates to SELECT * FROM workout
    if start is not None:
        query = query.where(Workout.performed_on >= start) # WHERE performed_on >= start
    if end is not None:
        query = query.where(Workout.performed_on <= end) # AND performed_on <= end
    query = query.order_by(col(Workout.performed_on).desc(), col(Workout.id).desc()) # ORDER BY performed_on DESC, id DESC
    return session.exec(query).all() # runs that SQL query

@router.patch("/{workout_id}", response_model=WorkoutResponse)
def edit_workout(workout_id: int, workout: WorkoutUpdate, session: Session = Depends(get_session)):
    stored_workout = session.get(Workout, workout_id)

    if stored_workout is None:
        raise HTTPException(status_code=404, detail="Invalid ID, workout not found")

    updates = workout.model_dump(exclude_unset=True)

    if "performed_on" in updates and updates.get("performed_on") is None:
        raise HTTPException(status_code=422, detail="Invalid Input, workout needs performed_on date")
 
    # iterate through what the client sent us and set each attr in stored_workout accordingly
    for key, value in updates.items():
        setattr(stored_workout, key, value)
    
    session.add(stored_workout)
    session.commit()
    session.refresh(stored_workout)
    return stored_workout

@router.delete("/{workout_id}", response_model=WorkoutResponse)
def delete_workout(workout_id: int, session: Session = Depends(get_session)):
    deleted_workout = session.get(Workout, workout_id)

    if deleted_workout is None:
        raise HTTPException(status_code=404, detail="Invalid ID, workout doesn't exist")
    
    session.delete(deleted_workout)
    session.commit()
    return deleted_workout