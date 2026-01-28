from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

#from sqlalchemy.ext.asyncio import AsyncSession

#from db_depends import get_async_db

from app.auth import get_current_admin
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.schemas import Category as CategorySchema, CategoryCreate
from app.db_depends import get_db


# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


'''@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: AsyncSession = Depends(get_db)):
#async def get_all_categories(db: Session = Depends(get_db)):
    """
    Возвращает список всех активных категорий.
    """
    result = await db.scalars(select(CategoryModel).where(CategoryModel.is_active==True))
    categories = result.all()
    return categories'''


@router.get("/sync/", response_model=list[CategorySchema])
def get_all_categories_sync(db: Session = Depends(get_db)):
    """
    Возвращает список всех активных категорий.
    """
    categories = db.scalars(select(CategoryModel).where(CategoryModel.is_active==True)).all()
    return categories

'''@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
#async def create_category(category: CategoryCreate, db: Session = Depends(get_async_db)):
    """
    Создаёт новую категорию.
    """
    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        stmt = select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                           CategoryModel.is_active == True)
        result = await db.scalars(stmt)
        parent = result.first()
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent category not found")

    # Создание новой категории
    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    await db.commit()
    # db.refresh(db_category)
    return db_category'''


@router.post("/sync/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
#async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_async_db)):
def create_category_sync(
        category: CategoryCreate,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
):
    """
    Создаёт новую категорию.
    """
    # Проверка существования parent_id, если указан

    if category.parent_id is not None:
        stmt = select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                           CategoryModel.is_active == True)

        parent = db.scalars(stmt).first()
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent category not found")

    # Создание новой категории
    db_category = CategoryModel(**category.model_dump(), admin_id=current_user.id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category



'''@router.put("/{category_id}", response_model=CategorySchema)
async def update_category(category_id: int, category: CategoryCreate, db: AsyncSession = Depends(get_db)):
#async def update_category(category_id: int, category: CategoryCreate, db: Session = Depends(get_db)):
    """
    Обновляет категорию по её ID.
    """
    # Проверка существования категории
    stmt = select(CategoryModel).where(CategoryModel.id == category_id,
                                       CategoryModel.is_active == True)
    result = await db.scalars(stmt)
    db_category = result.first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        parent_stmt = select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                                  CategoryModel.is_active == True)
        result1 = await db.scalars(parent_stmt)
        parent = result1.first()
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent category not found")

    # Обновление категории
    update_data = category.model_dump(exclude_unset=True)
    await db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(**update_data)
    )
    await db.commit()
    # db.refresh(db_category)
    return db_category'''


@router.put("/sync/{category_id}", response_model=CategorySchema)
#async def update_category(category_id: int, category: CategoryCreate, db: AsyncSession = Depends(get_db)):
def update_category_sync(
        category_id: int,
        category: CategoryCreate,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
):
    """
    Обновляет категорию по её ID.
    """
    # Проверка существования категории
    stmt = select(CategoryModel).where(CategoryModel.id == category_id,
                                       CategoryModel.is_active == True)
    db_category = db.scalars(stmt).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    if db_category.admin_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can only update your own categories")

    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        parent_stmt = select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                                  CategoryModel.is_active == True)

        parent = db.scalars(parent_stmt).first()
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent category not found")

    # Обновление категории
    update_data = category.model_dump(exclude_unset=True)
    db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(**update_data)
    )
    db.commit()
    db.refresh(db_category)
    return db_category


@router.delete("/sync/{category_id}", status_code=status.HTTP_200_OK)
#async def delete_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
def delete_category_sync(
        category_id: int,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
):
    """
    Логически удаляет категорию по её ID, устанавливая is_active=False.
    """
    # Проверка существования активной категории
    stmt = select(CategoryModel).where(CategoryModel.id == category_id, CategoryModel.is_active == True)
    category = db.scalars(stmt).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.admin_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You can only delete your own categories")

    # Логическое удаление категории (установка is_active=False)
    db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(is_active=False)
    )
    db.commit()
    return category