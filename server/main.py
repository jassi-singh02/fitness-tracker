from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

testing = []

class Fruit(BaseModel):
    name: str

@app.get("/")
async def root():
    return {"message": "hello world"}

@app.post("/fruits")
def add_item(fruit: Fruit):
    testing.append(fruit.name)
    return {"fruits": testing}

@app.get("/fruits")
def list_fruits():
    return testing