from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date

app = FastAPI()

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

@app.get("/")
async def root():
    return {"message": "hello world"}


## This is to create an exercise
@app.post("/exercises", response_model=ExerciseResponse)
def add_exercise(exercise: CreateExercise):
    global next_id
    newExercise = ExerciseResponse(name = exercise.name, group = exercise.group, id = next_id)
    testing.append(newExercise)
    next_id += 1
    return newExercise

# This is to get back a list of all exercises
@app.get("/exercises", response_model=ExerciseResponse)
def list_exercise():
    return testing

# To get back a certain exercise from the list
@app.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(exercise_id: int):
    # have to search through database list for the correct exercise
    for exercises in testing:
        if exercises.id == exercise_id:
            return exercises
    # otherwise raise a 404 error
    raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

@app.patch("/exercises/{exercise_id}", response_model=ExerciseResponse)
def edit_exercise(exercise_id: int, exercise: CreateExercise):
    for stored_exercise in testing:
        if stored_exercise.id == exercise_id:
            # editing the exercise here and we return to the client for them to save a GET trip
            stored_exercise.name = exercise.name
            stored_exercise.group = exercise.group
            return stored_exercise
    raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

#  To delete an exercise
@app.delete("/exercises/{exercise_id}")
def delete_exercise(exercise_id: int):
    if exercise_id < 0 or exercise_id >= len(testing):
        raise HTTPException(status_code=404, detail = "invalid index: exercise not found")
    # again good to return to the client to make it easy for us to debug later
    return {"exercise": testing.pop(exercise_id)}