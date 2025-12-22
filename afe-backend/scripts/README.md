# Scripts de Utilidad - AFE Backend

Esta carpeta contiene scripts de utilidad permanentes para administración del sistema.

## Scripts Disponibles

### Gestión de Usuarios
- **`create_user.py`** - Crear nuevos usuarios en el sistema
- **`reset_password.py`** - Resetear contraseñas de usuarios existentes

### Migración y Configuración
- **`migrate_settings_to_db.py`** - Migrar configuraciones del sistema a la base de datos

### Utilidades
- **`utils/`** - Funciones de utilidad compartidas

---

## Uso

Para ejecutar un script, usar:

```bash
python scripts/nombre_del_script.py
```

---

## Notas

- Todos los scripts deben ejecutarse desde la raíz del proyecto
- Asegúrate de tener las variables de entorno configuradas (.env)
- Los scripts requieren acceso a la base de datos

---

**Última actualización**: 2025-12-21
