"""
Script para resetear la contraseña de un responsable.
Uso: python scripts/reset_password.py <usuario_o_email> <nueva_password>
"""
import sys
from passlib.context import CryptContext
from app.db.session import SessionLocal
from app.models.usuario import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

try:
    # Obtener argumentos
    usuario_input = sys.argv[1] if len(sys.argv) > 1 else "alexander.taimal"
    nueva_password = sys.argv[2] if len(sys.argv) > 2 else "12345678"

    # Buscar usuario por usuario o email
    usuario = db.query(Usuario).filter(
        (Usuario.usuario == usuario_input) | (Usuario.email == usuario_input)
    ).first()

    if not usuario:
        print(f" Usuario '{usuario_input}' no encontrado")
    else:
        # Generar nuevo hash
        nuevo_hash = pwd_context.hash(nueva_password)

        print(f"Usuario encontrado: {usuario.nombre}")
        print(f"Hash anterior: {usuario.hashed_password[:50]}...")
        print(f"Hash nuevo:    {nuevo_hash[:50]}...")

        # Actualizar
        usuario.hashed_password = nuevo_hash
        db.commit()

        # Verificar
        es_valida = pwd_context.verify(nueva_password, usuario.hashed_password)
        print(f"\n  Contraseña actualizada exitosamente!")
        print(f"   Verificación: {'  VÁLIDA' if es_valida else ' INVÁLIDA'}")
        print(f"\nCredenciales:")
        print(f"   Usuario: {usuario.usuario}")
        print(f"   Contraseña: {nueva_password}")

except Exception as e:
    print(f" Error: {e}")
    db.rollback()
finally:
    db.close()
