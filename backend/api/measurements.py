"""Body measurement endpoints (Phase 8)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.schemas import MeasurementIn, MeasurementOut

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.put("", response_model=MeasurementOut)
def upsert_measurement(
    payload: MeasurementIn, session: SessionDep, user: CurrentUser
) -> MeasurementOut:
    fields = payload.model_dump(exclude_none=True)
    day = fields.pop("date", None) or date.today()
    row = repository.upsert_measurement(session, user.id, day, **fields)
    session.commit()
    return MeasurementOut.model_validate(row)


@router.get("", response_model=list[MeasurementOut])
def list_measurements(session: SessionDep, user: CurrentUser) -> list[MeasurementOut]:
    return [
        MeasurementOut.model_validate(m)
        for m in repository.list_measurements(session, user.id)
    ]
