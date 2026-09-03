from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.escrow import (
    AdminResolution,
    DisputeSubmission,
    EscrowCreate,
    EscrowRead,
    ReceiptConfirmation,
    ShippingSubmission,
)
from app.services.escrows import EscrowService, InvalidTransition

router = APIRouter()


@router.get("/{escrow_id}", response_model=EscrowRead)
async def get_escrow(
    escrow_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    escrow = await EscrowService(session).get(escrow_id)
    if escrow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found")
    return EscrowRead.model_validate(escrow)


@router.get("", response_model=list[EscrowRead])
async def list_escrows(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 50,
) -> list[EscrowRead]:
    escrows = await EscrowService(session).list_for_user(user_id=user_id, limit=limit)
    return [EscrowRead.model_validate(escrow) for escrow in escrows]


@router.post("", response_model=EscrowRead, status_code=status.HTTP_201_CREATED)
async def create_escrow(
    payload: EscrowCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    service = EscrowService(session)
    escrow = await service.create(payload)
    return EscrowRead.model_validate(escrow)


@router.post("/{escrow_id}/dispute", response_model=EscrowRead)
async def file_dispute(
    escrow_id: UUID,
    payload: DisputeSubmission,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    service = EscrowService(session)
    try:
        escrow = await service.file_dispute(escrow_id=escrow_id, payload=payload)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EscrowRead.model_validate(escrow)


@router.post("/{escrow_id}/resolve/release", response_model=EscrowRead)
async def resolve_to_seller(
    escrow_id: UUID,
    payload: AdminResolution,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    service = EscrowService(session)
    try:
        escrow = await service.resolve_to_seller(escrow_id=escrow_id, payload=payload)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EscrowRead.model_validate(escrow)


@router.post("/{escrow_id}/resolve/refund", response_model=EscrowRead)
async def refund_buyer(
    escrow_id: UUID,
    payload: AdminResolution,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    service = EscrowService(session)
    try:
        escrow = await service.refund_buyer(escrow_id=escrow_id, payload=payload)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EscrowRead.model_validate(escrow)


@router.post("/{escrow_id}/confirm-terms", response_model=EscrowRead)
async def confirm_terms(
    escrow_id: UUID,
    changed_by: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    service = EscrowService(session)
    try:
        escrow = await service.confirm_terms(escrow_id=escrow_id, changed_by=changed_by)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EscrowRead.model_validate(escrow)


@router.post("/{escrow_id}/ship", response_model=EscrowRead)
async def submit_shipping(
    escrow_id: UUID,
    payload: ShippingSubmission,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    service = EscrowService(session)
    try:
        escrow = await service.mark_shipped(escrow_id=escrow_id, payload=payload)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EscrowRead.model_validate(escrow)


@router.post("/{escrow_id}/confirm-receipt", response_model=EscrowRead)
async def confirm_receipt(
    escrow_id: UUID,
    payload: ReceiptConfirmation,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EscrowRead:
    service = EscrowService(session)
    try:
        escrow = await service.confirm_receipt(escrow_id=escrow_id, changed_by=payload.buyer_id)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return EscrowRead.model_validate(escrow)
