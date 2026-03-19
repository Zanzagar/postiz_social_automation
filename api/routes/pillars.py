"""Content pillar CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.dependencies import get_db
from api.models import Pillar
from api.schemas import PillarCreateRequest, PillarResponse, PillarUpdateRequest

router = APIRouter(prefix="/api", tags=["pillars"], dependencies=[Depends(get_current_user)])


@router.get("/pillars", response_model=list[PillarResponse])
async def list_pillars(
    active_only: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """Return all pillars, optionally filtered to active only."""
    stmt = select(Pillar).order_by(Pillar.sort_order, Pillar.name)
    if active_only:
        stmt = stmt.where(Pillar.is_active == True)  # noqa: E712
    result = await session.execute(stmt)
    return [
        PillarResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            color=p.color,
            is_active=p.is_active,
            sort_order=p.sort_order,
        )
        for p in result.scalars().all()
    ]


@router.post("/pillars", response_model=PillarResponse, status_code=201)
async def create_pillar(
    req: PillarCreateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Create a new content pillar."""
    existing = await session.execute(select(Pillar).where(Pillar.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Pillar '{req.name}' already exists")

    pillar = Pillar(
        name=req.name,
        description=req.description,
        color=req.color,
        sort_order=req.sort_order,
    )
    session.add(pillar)
    await session.commit()
    await session.refresh(pillar)
    return PillarResponse(
        id=pillar.id,
        name=pillar.name,
        description=pillar.description,
        color=pillar.color,
        is_active=pillar.is_active,
        sort_order=pillar.sort_order,
    )


@router.put("/pillars/{pillar_id}", response_model=PillarResponse)
async def update_pillar(
    pillar_id: int,
    req: PillarUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Update a content pillar."""
    result = await session.execute(select(Pillar).where(Pillar.id == pillar_id))
    pillar = result.scalar_one_or_none()
    if not pillar:
        raise HTTPException(status_code=404, detail="Pillar not found")

    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    await session.execute(update(Pillar).where(Pillar.id == pillar_id).values(**updates))
    await session.commit()

    result = await session.execute(select(Pillar).where(Pillar.id == pillar_id))
    pillar = result.scalar_one()
    return PillarResponse(
        id=pillar.id,
        name=pillar.name,
        description=pillar.description,
        color=pillar.color,
        is_active=pillar.is_active,
        sort_order=pillar.sort_order,
    )


@router.delete("/pillars/{pillar_id}")
async def delete_pillar(
    pillar_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Deactivate a pillar (soft delete). Existing content keeps the pillar name."""
    result = await session.execute(select(Pillar).where(Pillar.id == pillar_id))
    pillar = result.scalar_one_or_none()
    if not pillar:
        raise HTTPException(status_code=404, detail="Pillar not found")

    await session.execute(update(Pillar).where(Pillar.id == pillar_id).values(is_active=False))
    await session.commit()
    return {"detail": f"Pillar '{pillar.name}' deactivated"}
