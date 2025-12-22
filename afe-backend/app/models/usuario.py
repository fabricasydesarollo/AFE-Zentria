from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario = Column(String(100), nullable=False, unique=True)  # login
    nombre = Column(String(150))
    email = Column(String(255), nullable=False, unique=True)
    area = Column(String(100))
    telefono = Column(String(50))
    activo = Column(Boolean, server_default=text("1"), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    role_id = Column(BigInteger, ForeignKey("roles.id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable para usuarios OAuth
    must_change_password = Column(Boolean, server_default=text("1"), nullable=False) # obliga a cambiar la contraseña en el primer login

    # Campos para autenticación OAuth
    auth_provider = Column(String(50), server_default=text("'local'"), nullable=False)  # 'local', 'microsoft', 'google', etc.
    oauth_id = Column(String(255), nullable=True, unique=True)  # ID del usuario en el proveedor OAuth
    oauth_picture = Column(String(500), nullable=True)  # URL de la foto de perfil

    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False) # fecha de creación

    # Relaciones
    role = relationship("Role", back_populates="usuarios", lazy="joined")
    facturas = relationship("Factura", back_populates="usuario", lazy="selectin")
    grupos = relationship("ResponsableGrupo", back_populates="usuario", lazy="select")
