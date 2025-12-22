from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.role import RoleRead
from app.crud.role import list_roles
from app.core.security import require_role

router = APIRouter(tags=["Roles y Permisos"])


@router.get(
    "/",
    response_model=List[RoleRead],
    summary="Listar roles",
    description="Obtiene la lista de roles disponibles en el sistema."
)
def list_all(
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["superadmin", "admin", "viewer"])),
):
    return list_roles(db)
