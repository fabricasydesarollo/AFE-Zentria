# Backups del Sistema AFE

Esta carpeta contiene backups temporales y scripts de respaldo.

## IMPORTANTE

**Los backups de base de datos NO deben versionarse en Git.**

- Usar `.gitignore` para excluir archivos `.sql`
- Los backups permanentes deben almacenarse en:
  - Servidor externo
  - Sistema de backup automatizado
  - Cloud storage (Google Drive, OneDrive, etc.)

## 📋 Tipos de Backup

### 1. Backup Completo de Base de Datos

```bash
# Crear backup completo
mysqldump -u root -proot bd_afe > backup_bd_afe_$(date +%Y%m%d_%H%M%S).sql

# Restaurar desde backup
mysql -u root -proot bd_afe < backup_bd_afe_YYYYMMDD_HHMMSS.sql
```

### 2. Backup Solo de Datos (sin estructura)

```bash
# Solo datos
mysqldump -u root -proot --no-create-info bd_afe > backup_data_only_$(date +%Y%m%d).sql

# Solo estructura
mysqldump -u root -proot --no-data bd_afe > backup_schema_only_$(date +%Y%m%d).sql
```

### 3. Backup de Tablas Específicas

```bash
# Ejemplo: Solo tabla facturas
mysqldump -u root -proot bd_afe facturas > backup_facturas_$(date +%Y%m%d).sql
```

## 🔄 Automatización de Backups

### Windows (Programador de Tareas)

Crear script `backup_automatico.bat`:

```batch
@echo off
set FECHA=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%
set HORA=%TIME:~0,2%%TIME:~3,2%
set BACKUP_DIR=C:\Users\John Alex\PRIVADO_ODO\backups

mysqldump -u root -proot bd_afe > "%BACKUP_DIR%\backup_bd_afe_%FECHA%_%HORA%.sql"

:: Eliminar backups más antiguos de 30 días
forfiles /p "%BACKUP_DIR%" /s /m backup_*.sql /d -30 /c "cmd /c del @path"
```

### Programar en Windows

```powershell
# Ejecutar cada día a las 2 AM
schtasks /create /tn "Backup AFE DB" /tr "C:\path\backup_automatico.bat" /sc daily /st 02:00
```

## 📦 Ubicación de Backups Recomendada

```
PRIVADO_ODO/
├── backups/                          # Backups locales temporales
│   ├── daily/                        # Backups diarios (30 días)
│   ├── weekly/                       # Backups semanales (3 meses)
│   └── monthly/                      # Backups mensuales (1 año)
│
└── BD/                               # Backups de referencia
    └── backup_schema_reference.sql  # Solo para referencia de estructura
```

## Checklist Antes de Cambios Importantes

Antes de:
- Ejecutar migraciones grandes
- Actualizar dependencias
- Refactorizar código que toca la BD
- Deployment a producción

**Hacer backup:**

```bash
mysqldump -u root -proot bd_afe > "backup_pre_cambio_$(date +%Y%m%d_%H%M%S).sql"
```

##  Restauración de Emergencia

Si algo sale mal:

```bash
# 1. Crear backup del estado actual (por si acaso)
mysqldump -u root -proot bd_afe > backup_estado_corrupto.sql

# 2. Eliminar base de datos
mysql -u root -proot -e "DROP DATABASE bd_afe;"

# 3. Crear base de datos limpia
mysql -u root -proot -e "CREATE DATABASE bd_afe CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 4. Restaurar desde backup
mysql -u root -proot bd_afe < backup_FECHA_ULTIMA_BUENA.sql

# 5. Verificar versión de Alembic
mysql -u root -proot -e "USE bd_afe; SELECT * FROM alembic_version;"

# 6. Si es necesario, ejecutar migraciones pendientes
cd afe-backend
alembic upgrade head
```

## 📊 Verificar Integridad del Backup

Después de crear un backup:

```bash
# Verificar que el archivo no está corrupto
file backup_bd_afe_*.sql

# Ver primeras líneas
head -20 backup_bd_afe_*.sql

# Ver tamaño
ls -lh backup_bd_afe_*.sql
```

## 🔐 Seguridad

**NUNCA** versionar en Git:
-  Backups SQL con datos reales
-  Archivos `.env` con credenciales
-  Dumps de datos de usuarios

**SÍ** versionar:
- Scripts de backup
- Esquemas de BD (sin datos)
- Documentación de procedimientos
