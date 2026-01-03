"""Configs router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from packages.core.models import ConfigVersion
from packages.core.schemas import ConfigVersionCreate, ConfigVersionResponse

router = APIRouter()


@router.get("/latest", response_model=ConfigVersionResponse)
async def get_latest_config(db: Session = Depends(get_db)):
    """Get latest config."""
    config = db.query(ConfigVersion).order_by(ConfigVersion.created_at.desc()).first()
    if not config:
        raise HTTPException(status_code=404, detail="No config found")
    return ConfigVersionResponse(
        id=config.id,
        mode=config.mode,
        strategy_name=config.strategy_name,
        strategy_params=config.strategy_params,
        constraints=config.constraints,
        created_at=config.created_at,
        created_by=config.created_by,
    )


@router.post("", response_model=ConfigVersionResponse)
async def create_config(
    request: ConfigVersionCreate,
    db: Session = Depends(get_db),
):
    """Create config."""
    config = ConfigVersion(
        mode=request.mode,
        strategy_name=request.strategy_name,
        strategy_params=request.strategy_params,
        constraints=request.constraints,
        created_by=request.created_by,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return ConfigVersionResponse(
        id=config.id,
        mode=config.mode,
        strategy_name=config.strategy_name,
        strategy_params=config.strategy_params,
        constraints=config.constraints,
        created_at=config.created_at,
        created_by=config.created_by,
    )
