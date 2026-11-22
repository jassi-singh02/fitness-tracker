
# Sample data to test all the routes with
WORKOUT = {"performed_on": "2026-10-19", "notes": "hump day"}

# helper function that creates a real workout in the test SQL lite database and gives back the result
def create(client, **overrides):
    response = client.post("/workouts", json={**WORKOUT, **overrides})
    assert response.status_code == 200, response.text
    return response.json()

# ----------- TESTS YAY -----------

def test_patch_only_notes_not_date(client):
    # create a workout, keep its id
    created = create(client)

    # PATCH /workouts/{id} with ONLY new notes in the body
    response = client.patch(f"/workouts/{created['id']}", json={"notes": "rest day"})
    
    # Check: status code is 200
    assert response.status_code == 200, response.text

    # Check: notes changed to the new value and performed_on is the same
    data = response.json()
    assert data["notes"] == "rest day"
    assert data["performed_on"] == created["performed_on"]

def test_patch_null_date_rejected(client):
    created = create(client)
    response = client.patch(f"/workouts/{created['id']}", json={"performed_on": None})

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "Invalid Input, workout needs performed_on date"

    # a check to make sure that the NULL performed_on PATCH request didn't change our data
    get_response = client.get(f"/workouts/{created['id']}") 
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["performed_on"] == "2026-10-19", get_response.text

