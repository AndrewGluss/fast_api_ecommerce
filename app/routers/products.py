from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session
#from sqlalchemy.ext.asyncio import AsyncSession

#from app.db_depends import get_async_db
from app.auth import get_current_seller
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.db_depends import get_db


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


'''@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    stmt = select(ProductModel).where(ProductModel.is_active == True)
    result = await db.scalars(stmt)
    products = result.all()
    return products'''

@router.get("/sync/", response_model=list[ProductSchema])
def get_all_products_sync(db: Session = Depends(get_db)):
    """
    Возвращает список всех товаров.
    """
    stmt = select(ProductModel).where(ProductModel.is_active == True)
    products = db.scalars(stmt).all()
    return products


@router.post("/sync/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
def create_product_sync(
        product: ProductCreate,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый продукт.
    """
    # Проверка существования category_id, если указан
    if product.category_id is not None:
        stmt = select(CategoryModel).where(CategoryModel.id == product.category_id,
                                           CategoryModel.is_active == True)
        category = db.scalars(stmt).first()
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    # Создание новой категории
    db_product = ProductModel(**product.model_dump(), sellet_id=current_user.id)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

'''@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_async_db)):
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
    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    await db.commit()
    #db.refresh(db_product)
    return db_product'''


@router.get("/sync/products/category/{category_id}", response_model=list[ProductSchema])
def get_products_by_category_sync(category_id: int, db: Session = Depends(get_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    stmt = select(CategoryModel).where(CategoryModel.id == category_id, CategoryModel.is_active == True)
    category = db.scalars(stmt).first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    stmt_product = select(ProductModel).where(
        ProductModel.is_active == True, ProductModel.category_id == category_id
    )
    products = db.scalars(stmt_product).all()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Products not found")

    return products


'''@router.get("/products/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
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

    return products'''


@router.get("/sync/{product_id}", response_model=ProductSchema)
def get_product_sync(product_id: int, db: Session = Depends(get_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt_product = select(ProductModel).where(
        ProductModel.is_active == True, ProductModel.id == product_id
    )
    product = db.scalars(stmt_product).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return product


'''@router.get("/{product_id}", response_model=ProductSchema)
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

    return product'''


@router.put("/sync/{product_id}", response_model=ProductSchema)
def update_product_sync(
        product_id: int,
        product_update: ProductCreate,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар по его ID.
    """

    stmt_product = select(ProductModel).where(
        ProductModel.is_active == True, ProductModel.id == product_id
    )
    product = db.scalars(stmt_product).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can only update your own products")

    stmt = select(CategoryModel).where(
        CategoryModel.id == product_update.category_id, CategoryModel.is_active == True
    )
    category = db.scalars(stmt).first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product_update.model_dump())
    )
    db.commit()
    db.refresh(product)
    return product


'''@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(product_id: int, product_update: ProductCreate, db: AsyncSession = Depends(get_async_db())):
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
    return product'''


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
        product_id: int,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Удаляет товар по его ID.
    """
    # Проверка существования активной категории
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    product = db.scalars(stmt).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can only delete your own products")

    # Логическое удаление категории (установка is_active=False)
    db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False))
    db.commit()

    return {"status": "success", "message": "Product marked as inactive"}


'''@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db())):
    """
    Удаляет товар по его ID.
    """
    # Проверка существования активной категории
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)

    result = await db.scalars(stmt)
    product = result.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Логическое удаление категории (установка is_active=False)
    await db.execute(update(ProductModel).where(ProductModel.id == product_id).values(is_active=False))
    await db.commit()

    return {"status": "success", "message": "Product marked as inactive"}'''