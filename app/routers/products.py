from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.db_depends import get_async_db
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate, Review as ReviewSchema, ProductList



# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=ProductList)
async def get_all_products(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        category_id: int | None = Query(
            None, description="ID категории для фильтрации"),
        min_price: float | None = Query(
            None, ge=0, description="Минимальная цена товара"),
        max_price: float | None = Query(
            None, ge=0, description="Максимальная цена товара"),
        in_stock: bool | None = Query(
            None, description="true — только товары в наличии, false — только без остатка"),
        seller_id: int | None = Query(
            None, description="ID продавца для фильтрации"),
        db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает список всех активных товаров.
    """
    # Проверка логики min_price <= max_price
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )

    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)

    # Получаем количество активных товаров
    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)
    total = await db.scalar(total_stmt) or 0

    # Получаем список активных продуктов
    products_stmt = (
        select(ProductModel)
        .where(ProductModel.is_active == True)
        .order_by(ProductModel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.scalars(products_stmt)).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый продукт.
    """
    # Проверка существования category_id, если указан
    if product.category_id is not None:
        stmt = select(CategoryModel).where(CategoryModel.id == product.category_id,
                                           CategoryModel.is_active == True)
        result = await db.scalars(stmt)
        category = result.first()
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    # Создание новой категории
    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    #db.refresh(db_product)
    return db_product


@router.get("/products/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(
        category_id: int,
        db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    stmt = select(CategoryModel).where(CategoryModel.id == category_id, CategoryModel.is_active == True)
    result = await db.scalars(stmt)
    category = result.first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    stmt_product = select(ProductModel).where(
        ProductModel.is_active == True, ProductModel.category_id == category_id
    )
    result2 = await db.scalars(stmt_product)
    products = result2.all()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Products not found")

    return products


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt_product = select(ProductModel).where(
        ProductModel.is_active == True, ProductModel.id == product_id
    )
    result = await db.scalars(stmt_product)
    product = result.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
        product_id: int,
        product_update: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар по его ID.
    """

    stmt_product = select(ProductModel).where(
        ProductModel.is_active == True, ProductModel.id == product_id
    )
    result = await db.scalars(stmt_product)
    product = result.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can only update your own products")

    stmt = select(CategoryModel).where(
        CategoryModel.id == product_update.category_id, CategoryModel.is_active == True
    )
    result2 = await db.scalars(stmt)
    category = result2.first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product_update.model_dump())
    )
    await db.commit()
    #db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Удаляет товар по его ID.
    """
    # Проверка существования активной категории
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)

    result = await db.scalars(stmt)
    product = result.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can only delete your own products")

    # Логическое удаление категории (установка is_active=False)
    await db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False))
    await db.commit()

    return {"status": "success", "message": "Product marked as inactive"}

@router.get("/{product_id}/reviews/", response_model=list[ReviewSchema])
async def get_all_reviews_by_product_id(
        product_id: int,
        db: AsyncSession = Depends(get_async_db)
):
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    db_product = await db.scalars(stmt)

    product = db_product.first()

    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    reviews_stmt = select(ReviewModel).where(
        ReviewModel.product_id == product_id, ReviewModel.is_active == True
    )
    reviews = await db.scalars(reviews_stmt)

    return reviews.all()


async def update_product_rating(
        db: AsyncSession,
        product_id: int
):
    """result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )"""
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    #product = db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()
    #db.commit()