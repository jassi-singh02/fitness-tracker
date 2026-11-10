from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from sqlmodel import SQLModel, Field, Session, select, col
from sqlalchemy import delete
from db import get_session
from enum import Enum

router = APIRouter(prefix="/exercises")

# Is a design tradeoff for now, we have a specific list of muscles that is chosen for primary and secondary. Might switch to a lookup table
class MuscleGroup(str, Enum):
    chest = "Chest"                          # broad: any chest work, flat pressing
    upper_chest = "Upper Chest"              # incline press, low-to-high flyes
    lower_chest = "Lower Chest"              # decline press, dips
    serratus = "Serratus"                    # ab rollouts, scap push-ups

    # Back
    back = "Back"                            # broad: general back work
    lats = "Lats"                            # pulldowns, pull-ups
    teres_major = "Teres Major"              # pulldowns, rows
    rhomboids = "Rhomboids"                  # rows with a shoulder-blade squeeze
    traps = "Traps"                          # broad traps
    upper_traps = "Upper Traps"              # shrugs
    mid_traps = "Mid Traps"                  # wide-grip rows, face pulls
    lower_traps = "Lower Traps"              # Y-raises
    lower_back = "Lower Back"                # deadlifts, back extensions

    # Shoulders
    shoulders = "Shoulders"                  # broad: general shoulder work
    front_delts = "Front Delts"              # overhead press, front raises
    side_delts = "Side Delts"                # lateral raises
    rear_delts = "Rear Delts"                # reverse flyes, face pulls
    rotator_cuff = "Rotator Cuff"            # external rotations

    # Biceps
    biceps = "Biceps"                        # broad: curls
    brachialis = "Brachialis"                # hammer curls, reverse curls
    brachioradialis = "Brachioradialis"      # hammer and reverse curls

    # Triceps
    triceps = "Triceps"                      # broad: pushdowns, close-grip press
    triceps_long_head = "Triceps Long Head"  # overhead extensions
    triceps_lateral_head = "Triceps Lateral Head"  # pushdowns
    triceps_medial_head = "Triceps Medial Head"    # reverse-grip pushdowns

    # Forearms
    forearms = "Forearms"                    # broad: grip and wrist work
    forearm_flexors = "Forearm Flexors"      # wrist curls
    forearm_extensors = "Forearm Extensors"  # reverse wrist curls

    # Legs
    legs = "Legs"                            # broad: general leg work
    quads = "Quads"                          # squats, leg press, leg extensions
    hamstrings = "Hamstrings"                # leg curls, RDLs
    glutes = "Glutes"                        # hip thrusts, squats
    glute_medius = "Glute Medius"            # side-lying raises
    adductors = "Adductors"                  # adduction machine
    abductors = "Abductors"                  # abduction machine
    hip_flexors = "Hip Flexors"              # hanging leg raises, knee drives
    calves = "Calves"                        # standing calf raises
    soleus = "Soleus"                        # seated calf raises
    tibialis = "Tibialis"                    # tib raises

    # Core
    core = "Core"                            # broad: general core work
    abs = "Abs"                              # crunches, leg raises
    obliques = "Obliques"                    # side bends, woodchops
    deep_core = "Deep Core"                  # planks, dead bugs

    # Neck
    neck = "Neck"                            # neck curls and extensions

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
    secondary_muscle_groups: list[MuscleGroup] = []

class ExerciseResponse(ExerciseBase):
    # This is the model that is sent to the client on each route
    id: int
    secondary_muscle_groups: list[MuscleGroup]

# This is for the patch route, everything is optional for the client to edit
class ExerciseUpdate(SQLModel):
    name: str | None = None
    muscle_group: MuscleGroup | None = None
    load_type: LoadType | None = None
    measured_by: MeasuredBy | None = None
    archived_at: date | None = None
    secondary_muscle_groups: list[MuscleGroup] | None = None

# Packages up an exercise to send back to the client, including its secondary muscles.
def to_response(exercise: Exercise, session: Session) -> ExerciseResponse:
    # Look up the secondary muscles for this exercise
    rows = session.exec(
        select(ExerciseSecondaryMuscle.muscle_group)
        .where(ExerciseSecondaryMuscle.exercise_id == exercise.id)
    ).all()
    groups = [MuscleGroup(g) for g in rows]
    # Put the exercise and its muscles together
    return ExerciseResponse(**exercise.model_dump(), secondary_muscle_groups=groups)

@router.post("", response_model=ExerciseResponse)
def add_exercise(exercise: ExerciseCreate, session: Session = Depends(get_session)):
    newExercise = Exercise.model_validate(
        exercise.model_dump(exclude={"secondary_muscle_groups"})
    )
    session.add(newExercise)
    # to recieve an int ID for newExercise
    session.flush()
    assert newExercise.id is not None

    for group in exercise.secondary_muscle_groups:
        session.add(ExerciseSecondaryMuscle(exercise_id=newExercise.id, muscle_group=group))

    session.commit()
    session.refresh(newExercise)
    return to_response(newExercise, session)

@router.get("", response_model=list[ExerciseResponse])
def list_exercises(muscle_group: MuscleGroup | None = None, include_archived: bool = False, session: Session = Depends(get_session)):
    # query parameter to filter for muscle groups or archived exercises
    query = select(Exercise)
    if muscle_group is not None:
        query = query.where(Exercise.muscle_group == muscle_group)
    if not include_archived:
        query = query.where(Exercise.archived_at == None)

    exercises = session.exec(query).all()
    return [to_response(e, session) for e in exercises]

@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(exercise_id: int, session: Session = Depends(get_session)):
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Invalid ID: Exercise not found")
    return to_response(exercise, session)

@router.patch("/{exercise_id}", response_model=ExerciseResponse)
def edit_exercise(exercise_id: int, exercise: ExerciseUpdate, session: Session = Depends(get_session)):
    stored_exercise = session.get(Exercise, exercise_id)
    
    if stored_exercise is None:
        raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

    # we only update the fields that the client sends us
    updates = exercise.model_dump(exclude_unset=True)
    new_groups = updates.pop("secondary_muscle_groups", None)

    for key, value in updates.items():
        setattr(stored_exercise, key, value)

    if new_groups is not None:
        session.exec(
            delete(ExerciseSecondaryMuscle).where(col(ExerciseSecondaryMuscle.exercise_id) == exercise_id)
        )
        for group in new_groups:
            session.add(ExerciseSecondaryMuscle(exercise_id=exercise_id, muscle_group=group))

    session.add(stored_exercise)
    session.commit()
    session.refresh(stored_exercise)
    return to_response(stored_exercise, session)

@router.delete("/{exercise_id}", response_model=ExerciseResponse)
def delete_exercise(exercise_id: int, session: Session = Depends(get_session)):
    deleted_exercise = session.get(Exercise, exercise_id)

    if deleted_exercise is None:
        raise HTTPException(status_code=404, detail = "invalid id: exercise not found")

    response = to_response(deleted_exercise, session)

    session.exec(
        delete(ExerciseSecondaryMuscle).where(col(ExerciseSecondaryMuscle.exercise_id) == exercise_id)
    )

    session.delete(deleted_exercise)
    session.commit()
    return response