"""B1/B2 endpoints: /profile, /goals, /plan, /whatif."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from api.deps import get_store, get_today
from api.errors import ApiError
from engine.planner import service
from engine.planner.models import GoalIn, GoalPatch, ProfileIn, WhatIfRequest

router = APIRouter(tags=["planner"])


@router.get("/profile")
def read_profile(store=Depends(get_store)) -> dict:
    return service.load_profile(store)


@router.put("/profile")
def replace_profile(body: ProfileIn, store=Depends(get_store)) -> dict:
    return service.save_profile(store, body.model_dump())


@router.get("/plan")
def read_plan(store=Depends(get_store), today: date = Depends(get_today)) -> dict:
    """Usual variable spend per category, surplus and goal projections (feeds the what-if sliders)."""
    return service.overview(store, today)


@router.get("/goals")
def list_goals(store=Depends(get_store), today: date = Depends(get_today)) -> dict:
    return service.goals_view(store, today)


@router.post("/goals", status_code=201)
def create_goal(body: GoalIn, store=Depends(get_store)) -> dict:
    return service.add_goal(store, body.model_dump())


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: int, body: GoalPatch, store=Depends(get_store)) -> dict:
    patch = body.model_dump(exclude_unset=True)
    goal = store.update_goal(goal_id, patch)
    if goal is None:
        raise ApiError(404, "goal_not_found", f"No goal with id {goal_id}.")
    return goal


@router.post("/whatif")
def what_if(body: WhatIfRequest, store=Depends(get_store), today: date = Depends(get_today)) -> dict:
    try:
        return service.run_what_if(store, body.change(), today)
    except ValueError as e:
        raise ApiError(422, "unknown_category", str(e)) from e
