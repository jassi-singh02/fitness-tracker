# Tests for the /exercises routes.
# Each test gets a fresh, empty in-memory SQLite database, so tests never touch
# your real Postgres data and never affect each other.
#
# Run from the server/ folder:  pytest -v

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from db import get_session
from routers.exercises import ExerciseSecondaryMuscle


# ---------- Setup (fixtures) ----------

@pytest.fixture
def session():
    # A throwaway database that lives in memory for one test
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(session):
    # Swap the real database session for the test one
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


BENCH = {
    "name": "Bench Press",
    "muscle_group": "Chest",
    "load_type": "external",
    "measured_by": "reps",
    "archived_at": None,
    "secondary_muscle_groups": ["Front Delts", "Triceps"],
}


def create(client, **overrides):
    # Creates an exercise (Bench Press unless overridden) and returns the response JSON
    response = client.post("/exercises", json={**BENCH, **overrides})
    assert response.status_code == 200, response.text
    return response.json()


# ---------- POST ----------

def test_create_returns_exercise_with_secondaries(client):
    data = create(client)
    assert data["id"] is not None
    assert data["name"] == "Bench Press"
    # The database doesn't guarantee order, so compare as sets
    assert set(data["secondary_muscle_groups"]) == {"Front Delts", "Triceps"}


def test_create_uses_defaults_for_missing_fields(client):
    response = client.post("/exercises", json={
        "name": "Lateral Raise",
        "muscle_group": "Side Delts",
        "load_type": "external",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["measured_by"] == "reps"
    assert data["archived_at"] is None
    assert data["secondary_muscle_groups"] == []


# Step 1: checks your new 422 format from main.py
def test_create_with_invalid_muscle_group_returns_422(client):
    response = client.post("/exercises", json={**BENCH, "muscle_group": "Pecs"})
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Invalid input"
    assert body["errors"][0]["field"] == "muscle_group"


def test_create_missing_required_field_returns_422(client):
    response = client.post("/exercises", json={"name": "No Muscle", "load_type": "external"})
    assert response.status_code == 422
    fields = [e["field"] for e in response.json()["errors"]]
    assert "muscle_group" in fields


# Step 2: "assisted" is gone, so it should now be rejected
def test_assisted_load_type_is_rejected(client):
    response = client.post("/exercises", json={**BENCH, "load_type": "assisted"})
    assert response.status_code == 422


# Step 3: primary/secondary rules on POST (your model_validator)
def test_primary_cannot_also_be_secondary(client):
    response = client.post("/exercises", json={**BENCH, "secondary_muscle_groups": ["Chest"]})
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert error["field"] == "request"   # whole-model error, so no single field
    assert "primary" in error["message"]


def test_duplicate_secondaries_are_rejected(client):
    response = client.post("/exercises", json={**BENCH, "secondary_muscle_groups": ["Triceps", "Triceps"]})
    assert response.status_code == 422
    assert "duplicates" in response.json()["errors"][0]["message"]


# ---------- GET ----------

def test_get_exercise_includes_secondaries(client):
    created = create(client)
    response = client.get(f"/exercises/{created['id']}")
    assert response.status_code == 200
    assert set(response.json()["secondary_muscle_groups"]) == {"Front Delts", "Triceps"}


def test_get_missing_exercise_returns_404(client):
    response = client.get("/exercises/999")
    assert response.status_code == 404


def test_list_filters_by_muscle_group(client):
    create(client)
    # Step 2: Pull-up sample now uses bodyweight
    create(client, name="Pull-up", muscle_group="Lats", load_type="bodyweight",
           secondary_muscle_groups=["Biceps"])
    response = client.get("/exercises", params={"muscle_group": "Lats"})
    names = [e["name"] for e in response.json()]
    assert names == ["Pull-up"]


def test_archived_exercises_hidden_unless_requested(client):
    create(client, name="Old Exercise", archived_at="2026-11-09")

    default = client.get("/exercises").json()
    assert default == []

    with_archived = client.get("/exercises", params={"include_archived": True}).json()
    assert [e["name"] for e in with_archived] == ["Old Exercise"]


# ---------- PATCH ----------

def test_patch_one_field_leaves_everything_else(client):
    created = create(client)
    response = client.patch(f"/exercises/{created['id']}", json={"name": "Flat Bench Press"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Flat Bench Press"
    assert data["muscle_group"] == "Chest"
    assert set(data["secondary_muscle_groups"]) == {"Front Delts", "Triceps"}


def test_patch_secondaries_replaces_the_list(client):
    created = create(client)
    response = client.patch(f"/exercises/{created['id']}", json={"secondary_muscle_groups": ["Triceps"]})
    assert response.json()["secondary_muscle_groups"] == ["Triceps"]


# Step 3: PATCH-side checks (in the route, so 400 instead of 422)
def test_patch_primary_into_stored_secondary_returns_400(client):
    created = create(client)  # secondaries: Front Delts, Triceps
    response = client.patch(f"/exercises/{created['id']}", json={"muscle_group": "Triceps"})
    assert response.status_code == 400
    # And nothing should have changed
    assert client.get(f"/exercises/{created['id']}").json()["muscle_group"] == "Chest"


def test_patch_secondaries_to_include_primary_returns_400(client):
    created = create(client)
    response = client.patch(f"/exercises/{created['id']}", json={"secondary_muscle_groups": ["Chest"]})
    assert response.status_code == 400


def test_patch_duplicate_secondaries_returns_400(client):
    created = create(client)
    response = client.patch(f"/exercises/{created['id']}", json={"secondary_muscle_groups": ["Biceps", "Biceps"]})
    assert response.status_code == 400


def test_patch_missing_exercise_returns_404(client):
    response = client.patch("/exercises/999", json={"name": "Nope"})
    assert response.status_code == 404


# ---------- DELETE ----------

def test_delete_removes_exercise_and_its_secondaries(client, session):
    created = create(client)

    response = client.delete(f"/exercises/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Bench Press"

    assert client.get(f"/exercises/{created['id']}").status_code == 404
    # The link rows should be gone too
    assert session.exec(select(ExerciseSecondaryMuscle)).all() == []


def test_delete_missing_exercise_returns_404(client):
    response = client.delete("/exercises/999")
    assert response.status_code == 404
