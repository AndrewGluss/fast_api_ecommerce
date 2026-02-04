from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session
#from sqlalchemy.ext.asyncio import AsyncSession

#from app.db_depends import get_async_db
from app.auth import get_current_admin, get_current_user
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.models.reviews import Review as ReviewModel
from app.schemas import Product as ProductSchema, ProductCreate, Review as ReviewSchema, ReviewCreate
from app.db_depends import get_db
from app.routers.products import update_product_rating


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)

@router.get("/", response_model=list[ReviewSchema])
def get_all_reviews(db: Session = Depends(get_db)):
    """Получить список всех отзывов"""
    stmt = select(ReviewModel).where(ReviewModel.is_active == True)

    return db.scalars(stmt).all()


@router.post("/", response_model=ReviewSchema)
def create_review(
        review: ReviewCreate,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    """Создание отзыва о продукте"""
    if review.product_id is not None:
        stmt = select(ProductModel).where(ProductModel.id == review.product_id,
                                           ProductModel.is_active == True)
        product = db.scalars(stmt).first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    if current_user.role != "buyer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only buyer can write review")

    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    update_product_rating(product_id=review.product_id, db=db)
    return db_review

@router.delete("/{review_id}")
def delete_review(
        review_id: int,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
):
    """Удаление отзыва о продукте"""

    stmt = select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    review = db.scalars(stmt).first()
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    db.execute(update(ReviewModel).where(ReviewModel.id == review_id).values(is_active=False))
    db.commit()
    update_product_rating(product_id=review.product_id, db=db)
    return {"status": "success", "message": "Review marked as inactive"}