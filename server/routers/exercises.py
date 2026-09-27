from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/exercises")

testing = []
next_id = 0

class CreateExercise(BaseModel):
    # by defining this, this handles all the incorect data type errors - 422
    name: str
    group: str

class ExerciseResponse(BaseModel):
    id: int
    name: str
    group: str

class LogExercise(BaseModel):
    exercise_id: int
    weight: float
    reps: int
    performed_on: date

## This is to create an exercise
@router.post("", response_model=ExerciseResponse)
def add_exercise(exercise: CreateExercise):
    global next_id
    newExercise = ExerciseResponse(name = exercise.name, group = exercise.group, id = next_id)
    testing.append(newExercise)
    next_id += 1
    return newExercise

# This is to get back a list of all exercises
@router.get("", response_model=list[ExerciseResponse])
def list_exercise():
    return testing

# To get back a certain exercise from the list
@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(exercise_id: int):
    # have to search through database list for the correct exercise
    for exercises in testing:
        if exercises.id == exercise_id:
            return exercises
    # otherwise raise a 404 error - check in
    raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

@router.patch("/{exercise_id}", response_model=ExerciseResponse)
def edit_exercise(exercise_id: int, exercise: CreateExercise):
    for stored_exercise in testing:
        if stored_exercise.id == exercise_id:
            # editing the exercise here and we return to the client for them to save a GET trip
            stored_exercise.name = exercise.name
            stored_exercise.group = exercise.group
            return stored_exercise
    raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

#  To delete an exercise
@router.delete("/{exercise_id}", response_model=ExerciseResponse)
def delete_exercise(exercise_id: int):
    for stored_exercise in testing:
        if stored_exercise.id == exercise_id:
            testing.remove(stored_exercise)
            return stored_exercise
    raise HTTPException(status_code=404, detail = "invalid id: exercise not found")