"""
Script para crear la tabla de usuarios y un usuario de prueba.
"""
from passlib.context import CryptContext
from app.core.database import engine, SessionLocal
from app.models import Base, Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Crear tablas
print("Creando tabla de usuarios...")
Base.metadata.create_all(bind=engine)

# Crear usuario de prueba
db = SessionLocal()

try:
    # Verificar si ya existe
    existing = db.query(Usuario).filter(Usuario.usuario == "alex.taimal").first()

    if existing:
        print(f"  Usuario 'alex.taimal' ya existe (ID: {existing.id})")
    else:
        # Crear usuario
        usuario = Usuario(
            nombre="Alex Taimal",
            email="alex.taimal@zentria.com",
            usuario="alex.taimal",
            password_hash=pwd_context.hash("zentria2025"),
            area="Tecnología",
            rol="admin",
            activo=True
        )

        db.add(usuario)
        db.commit()
        db.refresh(usuario)

        print(f"  Usuario creado exitosamente!")
        print(f"   Usuario: alex.taimal")
        print(f"   Contraseña: zentria2025")
        print(f"   ID: {usuario.id}")

except Exception as e:
    print(f" Error: {e}")
    db.rollback()
finally:
    db.close()
