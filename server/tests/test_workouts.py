
# Sample data to test all the routes with
WORKOUT = {"performed_on": "2026-10-19", "notes": "hump day"}

def create(client, **overrides):
    response = client.post("/workouts", json={**WORKOUT, **overrides})
    assert response.status_code == 200, response.text
    return response.json()

# ----------- TESTS YAY -----------

def test_patch_only_notes_not_date(client):
    