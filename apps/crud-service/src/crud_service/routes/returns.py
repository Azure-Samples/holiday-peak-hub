"""Customer return and refund progression routes."""

from crud_service.auth import User, require_customer
from crud_service.integrations import get_event_publisher
from crud_service.repositories import OrderRepository, RefundRepository, ReturnRequestRepository
from crud_service.returns_lifecycle import (
    RETURN_TRANSITION_EVENTS,
    ReturnCreateRequest,
    ReturnResponse,
    RefundResponse,
    create_return_record,
    event_data,
    utc_now_iso,
)
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
return_repo = ReturnRequestRepository()
refund_repo = RefundRepository()
order_repo = OrderRepository()
event_publisher = get_event_publisher()


async def _attach_refund(payload: dict) -> dict:
    refund = await refund_repo.get_by_return_id(payload["id"])
    if refund:
        payload["refund"] = refund
    return payload


@router.post("", response_model=ReturnResponse, status_code=201)
async def create_return(
    request: ReturnCreateRequest,
    current_user: User = Depends(require_customer),
):
    """Create a customer return request in requested state."""
    order = await order_repo.get_by_id(request.order_id, partition_key=current_user.user_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.get("user_id") != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    payload = create_return_record(
        order_id=request.order_id,
        user_id=current_user.user_id,
        reason=request.reason,
        items=request.items,
        actor_id=current_user.user_id,
        actor_roles=list(current_user.roles or []),
    )
    await return_repo.create(payload)

    occurred_at = payload["requested_at"]
    await event_publisher.publish_return_lifecycle_event(
        event_type=RETURN_TRANSITION_EVENTS["requested"],
        data=event_data(
            payload=payload,
            actor_id=current_user.user_id,
            actor_roles=list(current_user.roles or []),
            occurred_at=occurred_at,
        ),
    )

    return ReturnResponse(**payload)


@router.get("", response_model=list[ReturnResponse])
async def list_returns(current_user: User = Depends(require_customer)):
    """List returns owned by authenticated customer."""
    records = await return_repo.get_by_user(current_user.user_id, limit=100)
    records = sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)

    response: list[ReturnResponse] = []
    for record in records:
        hydrated = await _attach_refund(record)
        response.append(ReturnResponse(**hydrated))
    return response


@router.get("/{return_id}", response_model=ReturnResponse)
async def get_return(return_id: str, current_user: User = Depends(require_customer)):
    """Get return details and lifecycle/refund progression for the current customer."""
    record = await return_repo.get_by_id(return_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )
    if record.get("user_id") != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    hydrated = await _attach_refund(record)
    return ReturnResponse(**hydrated)


@router.get("/{return_id}/refund", response_model=RefundResponse)
async def get_refund_progress(return_id: str, current_user: User = Depends(require_customer)):
    """Get refund progression details for a customer return."""
    record = await return_repo.get_by_id(return_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )
    if record.get("user_id") != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    refund = await refund_repo.get_by_return_id(return_id)
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found",
        )

    refund.setdefault("updated_at", refund.get("issued_at") or utc_now_iso())
    refund.setdefault("last_transition_at", refund.get("issued_at") or refund["updated_at"])
    return RefundResponse(**refund)
