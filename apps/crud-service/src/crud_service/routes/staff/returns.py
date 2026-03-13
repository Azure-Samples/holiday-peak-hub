"""Staff return lifecycle management routes."""

from crud_service.auth import User, get_current_user
from crud_service.integrations import get_event_publisher
from crud_service.repositories import RefundRepository, ReturnRequestRepository
from crud_service.returns_lifecycle import (
    RETURN_TRANSITION_EVENTS,
    ReturnStatus,
    ReturnResponse,
    ReturnTransitionRequest,
    RefundResponse,
    create_refund_record,
    event_data,
    transition_return_record,
)
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
return_repo = ReturnRequestRepository()
refund_repo = RefundRepository()
event_publisher = get_event_publisher()


async def require_staff_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require either staff or admin role for staff return endpoints."""
    if not {"staff", "admin"}.intersection(set(current_user.roles or [])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role 'staff' or 'admin' required",
        )
    return current_user


async def _hydrate_return(record: dict, *, idempotent: bool = False) -> ReturnResponse:
    refund = await refund_repo.get_by_return_id(record["id"])
    if refund:
        record["refund"] = refund
    record["idempotent"] = idempotent
    return ReturnResponse(**record)


@router.get("/", response_model=list[ReturnResponse])
async def list_returns(_current_user: User = Depends(require_staff_or_admin)):
    """List all return requests for staff operations."""
    records = await return_repo.query(
        query="SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT 200",
    )
    records = sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)

    response: list[ReturnResponse] = []
    for record in records:
        response.append(await _hydrate_return(record))
    return response


@router.get("/{return_id}", response_model=ReturnResponse)
async def get_return(return_id: str, _current_user: User = Depends(require_staff_or_admin)):
    """Get a return request with refund progression for staff view."""
    record = await return_repo.get_by_id(return_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )
    return await _hydrate_return(record)


async def _transition_return(
    return_id: str,
    *,
    target_status: ReturnStatus,
    request: ReturnTransitionRequest,
    current_user: User,
) -> ReturnResponse:
    record = await return_repo.get_by_id(return_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    idempotent = transition_return_record(
        record,
        target_status=target_status,
        actor_id=current_user.user_id,
        actor_roles=list(current_user.roles or []),
        reason=request.reason,
    )

    if idempotent and target_status == "refunded":
        existing_refund = await refund_repo.get_by_return_id(return_id)
        if existing_refund is None:
            refund = create_refund_record(
                return_payload=record,
                actor_id=current_user.user_id,
                actor_roles=list(current_user.roles or []),
            )
            await refund_repo.create(refund)

    if not idempotent:
        await return_repo.update(record)
        occurred_at = record["last_transition_at"]

        if target_status == "refunded":
            existing_refund = await refund_repo.get_by_return_id(return_id)
            if existing_refund is None:
                refund = create_refund_record(
                    return_payload=record,
                    actor_id=current_user.user_id,
                    actor_roles=list(current_user.roles or []),
                )
                await refund_repo.create(refund)

            return_event = event_data(
                payload=record,
                actor_id=current_user.user_id,
                actor_roles=list(current_user.roles or []),
                occurred_at=occurred_at,
            )

            await event_publisher.publish_refund_issued(
                {
                    "return_id": record["id"],
                    "order_id": record["order_id"],
                    "user_id": record["user_id"],
                    "status": "issued",
                    "occurred_at": occurred_at,
                    "actor_id": current_user.user_id,
                    "actor_roles": list(current_user.roles or []),
                    "sla": return_event["sla"],
                    "timestamp": occurred_at,
                }
            )
            await event_publisher.publish_return_lifecycle_event(
                event_type=RETURN_TRANSITION_EVENTS["refunded"],
                data=return_event,
            )
        else:
            await event_publisher.publish_return_lifecycle_event(
                event_type=RETURN_TRANSITION_EVENTS[target_status],
                data=event_data(
                    payload=record,
                    actor_id=current_user.user_id,
                    actor_roles=list(current_user.roles or []),
                    occurred_at=occurred_at,
                ),
            )

    return await _hydrate_return(record, idempotent=idempotent)


@router.post("/{return_id}/approve", response_model=ReturnResponse)
async def approve_return(
    return_id: str,
    request: ReturnTransitionRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Approve a requested return."""
    return await _transition_return(
        return_id,
        target_status="approved",
        request=request,
        current_user=current_user,
    )


@router.patch("/{return_id}/approve", response_model=ReturnResponse)
async def approve_return_patch(
    return_id: str,
    request: ReturnTransitionRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Legacy compatibility endpoint for approving a return."""
    return await _transition_return(
        return_id,
        target_status="approved",
        request=request,
        current_user=current_user,
    )


@router.post("/{return_id}/reject", response_model=ReturnResponse)
async def reject_return(
    return_id: str,
    request: ReturnTransitionRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Reject a requested return."""
    return await _transition_return(
        return_id,
        target_status="rejected",
        request=request,
        current_user=current_user,
    )


@router.post("/{return_id}/receive", response_model=ReturnResponse)
async def receive_return(
    return_id: str,
    request: ReturnTransitionRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Mark approved return as received."""
    return await _transition_return(
        return_id,
        target_status="received",
        request=request,
        current_user=current_user,
    )


@router.post("/{return_id}/restock", response_model=ReturnResponse)
async def restock_return(
    return_id: str,
    request: ReturnTransitionRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Mark received return as restocked."""
    return await _transition_return(
        return_id,
        target_status="restocked",
        request=request,
        current_user=current_user,
    )


@router.post("/{return_id}/refund", response_model=ReturnResponse)
async def refund_return(
    return_id: str,
    request: ReturnTransitionRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Issue refund for a restocked return."""
    return await _transition_return(
        return_id,
        target_status="refunded",
        request=request,
        current_user=current_user,
    )


@router.get("/{return_id}/refund", response_model=RefundResponse)
async def get_refund(return_id: str, _current_user: User = Depends(require_staff_or_admin)):
    """Get refund progression details for staff operations."""
    record = await return_repo.get_by_id(return_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    refund = await refund_repo.get_by_return_id(return_id)
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found",
        )

    return RefundResponse(**refund)
