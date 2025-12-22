# app/db/init_db.py
from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.usuario import Usuario
from app.core.security import hash_password
from app.utils.logger import logger


def create_default_roles_and_admin(db: Session):
    # === Crear roles si no existen ===
    roles = {"admin", "responsable"}
    for role_name in roles:
        if not db.query(Role).filter(Role.nombre == role_name).first():
            db.add(Role(nombre=role_name))
            logger.info("Rol creado: %s", role_name)
    db.commit()

    # === Crear usuario admin si no existe ===
    admin = db.query(Usuario).filter(Usuario.usuario == "admin").first()
    if not admin:
        # Verificar si el email ya existe
        email_exists = db.query(Usuario).filter(Usuario.email == "jhontaimal@gmail.com").first()
        if email_exists:
            logger.info("Email jhontaimal@gmail.com ya está asociado a otro usuario, saltando creación de admin")
        else:
            # buscar el rol admin
            admin_role = db.query(Role).filter(Role.nombre == "admin").first()

            admin = Usuario(
                usuario="admin",
                nombre="John Alex",
                email="jhontaimal@gmail.com",
                hashed_password=hash_password("87654321"),
                activo=True,
                role_id=admin_role.id if admin_role else None,
                must_change_password=True  # <-- mejora para seguridad
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info("Admin creado: %s", admin.usuario)
    else:
        logger.info("Admin ya existe: %s", admin.usuario)
