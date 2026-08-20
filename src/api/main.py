"""Products & Admin API router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.database import get_session
from src.models.db_models import Base_Products

router = APIRouter(prefix="/products", tags=["Products & Admin"])


@router.post("/", response_model=Base_Products)
def create_product(
    product: Base_Products,
    session: Session = Depends(get_session),
) -> Base_Products:
    session.add(product)
    session.commit()
    session.refresh(product)
    return product
