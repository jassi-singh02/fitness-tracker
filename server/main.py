from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

testing = []

class Exercise(BaseModel):
    # by defining this, this handles all the incorect data type errors - 422
    name: str

@app.get("/")
async def root():
    return {"message": "hello world"}


## This is to create an exercise
@app.post("/exercise")
def add_item(exercise: Exercise):
    testing.append(exercise.name)
    return {"exercise": testing}

# This is to get back a list of all exercises
@app.get("/exercise")
def list_exercise():
    return testing

# To get back a certain exercise from the list
@app.get("/exercise/{exercise_id}")
def get_exercise(exercise_id: int):
    # error handling for wrong index - 404
    if exercise_id < 0 or exercise_id >= len(testing):
        raise HTTPException(status_code=404, detail = "invalid index: exercise not found")
    return {"exercise": testing[exercise_id]}

@app.patch("/exercise/{exercise_id}")
def edit_exercise(exercise_id: int, exercise: Exercise):
    if exercise_id < 0 or exercise_id >= len(testing):
        raise HTTPException(status_code=404, detail = "invalid index: exercise not found")
    # editing the exercise here and we return to the client to make it easy for us to debug later
    testing[exercise_id] = exercise.name
    return {"exercise": testing[exercise_id]}