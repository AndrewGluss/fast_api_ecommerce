from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_admin, get_current_user
from app.db_depends import get_async_db
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from app.models.users import User as UserModel
from app.routers.products import update_product_rating
from app.schemas import Review as ReviewSchema, ReviewCreate

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)

@router.get("/", response_model=list[ReviewSchema])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """Получить список всех отзывов"""
    stmt = select(ReviewModel).where(ReviewModel.is_active == True)
    result = await db.scalars(stmt)
    return result.all()


@router.post("/", response_model=ReviewSchema)
async def create_review(
        review: ReviewCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_user)
):
    """Создание отзыва о продукте"""
    if review.product_id is not None:
        stmt = select(ProductModel).where(ProductModel.id == review.product_id,
                                           ProductModel.is_active == True)
        db_product = await db.scalars(stmt)

        product = db_product.first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    if current_user.role != "buyer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only buyer can write review")

    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    await db.commit()
    #db.refresh(db_review)
    await update_product_rating(product_id=review.product_id, db=db)
    return db_review

@router.delete("/{review_id}")
async def delete_review(
        review_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_admin)
):
    """Удаление отзыва о продукте"""

    stmt = select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    db_review = await db.scalars(stmt)
    review = db_review.first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    await db.execute(update(ReviewModel).where(ReviewModel.id == review_id).values(is_active=False))
    await db.commit()
    await update_product_rating(product_id=review.product_id, db=db)
    return {"status": "success", "message": "Review marked as inactive"}