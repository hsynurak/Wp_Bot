from __future__ import annotations

import numpy as np
from sqlmodel import Session, select

from src.models.db_models import (
    Base_Products,
    Customer_Interactions,
    Customers,
)

EMBEDDING_DIM = 512


def _get_recent_favorite_codes(session: Session, phone_number: str) -> list[str]:
    interactions = session.exec(
        select(Customer_Interactions)
        .where(Customer_Interactions.phone == phone_number)
        .where(Customer_Interactions.interaction_type == "favorite")
        .order_by(Customer_Interactions.created_at.desc())
        .limit(10)
    ).all()

    if not interactions:
        return []

    return list(dict.fromkeys(i.product_code for i in interactions))


def _compute_mean_embedding(session: Session, favorite_codes: list[str]) -> list[float] | None:
    favorite_products = session.exec(
        select(Base_Products).where(Base_Products.model_code.in_(favorite_codes))
    ).all()

    if not favorite_products:
        return None

    embeddings: list[np.ndarray] = []
    for product in favorite_products:
        if product.embedding is not None:
            embeddings.append(np.asarray(product.embedding, dtype=np.float32))

    if not embeddings:
        return None

    return np.mean(np.stack(embeddings), axis=0).tolist()


async def update_customer_taste_vector(session: Session, phone_number: str) -> bool:
    favorite_codes = _get_recent_favorite_codes(session, phone_number)
    if not favorite_codes:
        return False

    mean_vector = _compute_mean_embedding(session, favorite_codes)
    if mean_vector is None:
        return False

    customer = session.exec(
        select(Customers).where(Customers.phone == phone_number)
    ).first()

    if customer is None:
        customer = Customers(phone=phone_number, taste_vector=mean_vector)
        session.add(customer)
    else:
        customer.taste_vector = mean_vector
        session.add(customer)

    return True


async def get_personalized_recommendations(
    session: Session,
    phone_number: str,
    limit: int = 3,
) -> list[Base_Products]:
    await update_customer_taste_vector(session, phone_number)
    session.commit()

    customer = session.exec(
        select(Customers).where(Customers.phone == phone_number)
    ).first()

    if customer is None or customer.taste_vector is None:
        return []

    favorite_codes = _get_recent_favorite_codes(session, phone_number)
    if not favorite_codes:
        return []

    statement = (
        select(Base_Products)
        .where(Base_Products.model_code.not_in(favorite_codes))
        .order_by(Base_Products.embedding.cosine_distance(customer.taste_vector))
        .limit(limit)
    )

    return list(session.exec(statement).all())
