from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("", response_model=schemas.InteractionOut)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Used by the structured form's Submit button."""
    hcp = None
    if payload.hcp_id:
        hcp = db.query(models.HCP).filter_by(id=payload.hcp_id).first()
    if not hcp and payload.hcp_name:
        hcp = db.query(models.HCP).filter(models.HCP.name.ilike(payload.hcp_name)).first()
        if not hcp:
            hcp = models.HCP(name=payload.hcp_name)
            db.add(hcp)
            db.commit()
            db.refresh(hcp)
    if not hcp:
        raise HTTPException(400, "hcp_id or hcp_name is required")

    interaction = models.Interaction(
        hcp_id=hcp.id,
        interaction_type=payload.interaction_type,
        date=payload.date,
        time=payload.time,
        attendees=payload.attendees,
        topics_discussed=payload.topics_discussed,
        materials_shared=[m.model_dump() for m in payload.materials_shared],
        samples_distributed=[s.model_dump() for s in payload.samples_distributed],
        sentiment=payload.sentiment,
        outcomes=payload.outcomes,
        follow_up_actions=payload.follow_up_actions,
        source="form",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    interaction.hcp_name = hcp.name
    return interaction


@router.get("/{interaction_id}", response_model=schemas.InteractionOut)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
    if not interaction:
        raise HTTPException(404, "Not found")
    interaction.hcp_name = interaction.hcp.name
    return interaction


@router.patch("/{interaction_id}", response_model=schemas.InteractionOut)
def update_interaction(interaction_id: str, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
    if not interaction:
        raise HTTPException(404, "Not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in ("materials_shared", "samples_distributed") and value is not None:
            value = [v if isinstance(v, dict) else v.model_dump() for v in value]
        setattr(interaction, field, value)
    interaction.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interaction)
    interaction.hcp_name = interaction.hcp.name
    return interaction


@router.get("", response_model=list[schemas.InteractionOut])
def list_interactions(hcp_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interaction)
    if hcp_id:
        q = q.filter_by(hcp_id=hcp_id)
    results = q.order_by(models.Interaction.created_at.desc()).limit(50).all()
    for r in results:
        r.hcp_name = r.hcp.name
    return results


@router.get("/hcps/search")
def search_hcps(q: str, db: Session = Depends(get_db)):
    matches = db.query(models.HCP).filter(models.HCP.name.ilike(f"%{q}%")).limit(10).all()
    return [{"id": h.id, "name": h.name, "specialty": h.specialty} for h in matches]
