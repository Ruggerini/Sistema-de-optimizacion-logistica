from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_db
from ..models import RouteHistory, User
from ..schemas import OptimizationRequest, OptimizationResponse, RouteHistoryRead, TruckRoute
from ..services.optimizer import OptimizationEngine

router = APIRouter(prefix="/api/routes", tags=["routes"])

optimizer = OptimizationEngine()


@router.post("/optimize", response_model=OptimizationResponse)
def optimize_routes(
    payload: OptimizationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OptimizationResponse:
    try:
        result = optimizer.optimize(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    history = RouteHistory(
        user_id=user.id,
        execution_date=payload.execution_date,
        truck_assignments=[route.model_dump(mode="json") for route in result.assignments],
        google_maps_links=[route.google_maps_link for route in result.assignments],
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return result


@router.get("/history", response_model=List[RouteHistoryRead])
def list_history(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[RouteHistoryRead]:
    histories = (
        db.query(RouteHistory)
        .filter(RouteHistory.user_id == user.id)
        .order_by(RouteHistory.run_date.desc())
        .limit(20)
        .all()
    )
    results: List[RouteHistoryRead] = []
    for record in histories:
        routes = [TruckRoute(**route) for route in record.truck_assignments]
        results.append(
            RouteHistoryRead(
                id=record.id,
                run_date=record.run_date,
                execution_date=record.execution_date,
                truck_assignments=routes,
                google_maps_links=record.google_maps_links,
            )
        )
    return results
    return [RouteHistoryRead.model_validate(record) for record in histories]


@router.delete("/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(
    history_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    record = db.query(RouteHistory).filter(RouteHistory.id == history_id, RouteHistory.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")
    db.delete(record)
    db.commit()
