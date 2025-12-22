# Sistema de Automatización de Facturas Recurrentes

## Descripción General

El sistema de automatización de facturas recurrentes está diseñado para identificar y procesar automáticamente facturas que siguen patrones regulares, reduciendo la carga de trabajo manual y mejorando la eficiencia del proceso de aprobación.

## Arquitectura del Sistema

### Componentes Principales

1. **FingerprintGenerator** (`app/services/automation/fingerprint_generator.py`)
   - Genera "huellas digitales" únicas para cada factura
   - Normaliza conceptos y detecta categorías médicas
   - Implementa múltiples estrategias de fingerprinting

2. **PatternDetector** (`app/services/automation/pattern_detector.py`)
   - Analiza patrones temporales y de montos en facturas históricas
   - Detecta recurrencia y calcula niveles de confianza
   - Identifica variaciones normales vs. anomalías

3. **DecisionEngine** (`app/services/automation/decision_engine.py`)
   - Toma decisiones finales sobre aprobación automática
   - Evalúa múltiples criterios con pesos configurables
   - Genera explicaciones detalladas de las decisiones

4. **AutomationService** (`app/services/automation/automation_service.py`)
   - Orquesta todos los componentes del sistema
   - Maneja el flujo completo de procesamiento
   - Proporciona APIs para integración

5. **NotificationService** (`app/services/automation/notification_service.py`)
   - Envía notificaciones cuando se requiere intervención manual
   - Genera reportes de procesamiento
   - Maneja diferentes canales de comunicación

## Flujo de Procesamiento

```
1. Factura Pendiente
   ↓
2. Generación de Fingerprints
   ↓
3. Búsqueda de Facturas Históricas
   ↓
4. Análisis de Patrones
   ↓
5. Evaluación de Criterios
   ↓
6. Decisión Final
   ↓
7. Actualización en BD + Notificaciones
```



### Umbrales de Decisión

- **Aprobación Automática**: Confianza ≥ 85%
- **Revisión Manual**: Confianza < 85%
- **Rechazo Automático**: No implementado (todas van a revisión)

## Campos de Base de Datos

Los siguientes campos fueron agregados a la tabla `facturas` para soportar la automatización:

```sql
-- Campos de identificación y categorización
concepto_principal VARCHAR(500)      -- Concepto principal extraído
concepto_normalizado VARCHAR(300)    -- Concepto normalizado
concepto_hash VARCHAR(64)           -- Hash para búsqueda rápida
tipo_factura VARCHAR(100)           -- Categoría de la factura
items_resumen JSON                  -- Resumen de items de la factura

-- Campos de trazabilidad
orden_compra_numero VARCHAR(100)    -- Número de orden de compra
orden_compra_sap VARCHAR(100)      -- Referencia SAP

-- Campos de automatización
patron_recurrencia VARCHAR(50)      -- Tipo de patrón detectado
confianza_automatica DECIMAL(5,4)   -- Nivel de confianza (0-1)
factura_referencia_id INT          -- ID de factura de referencia
motivo_decision TEXT               -- Explicación de la decisión
procesamiento_info JSON           -- Metadata del procesamiento
notas_adicionales TEXT           -- Notas del proceso

-- Campos de control
fecha_procesamiento_auto DATETIME  -- Cuándo fue procesada
version_algoritmo VARCHAR(10)     -- Versión del algoritmo usado
```

## APIs Disponibles

### Endpoints Principales

```
POST /api/v1/automation/procesar
GET  /api/v1/automation/estadisticas
GET  /api/v1/automation/facturas-procesadas
GET  /api/v1/automation/configuracion
PUT  /api/v1/automation/configuracion
POST /api/v1/automation/reprocesar/{factura_id}
GET  /api/v1/automation/patrones/{proveedor_id}
POST /api/v1/automation/notificar-resumen
```

### Ejemplo de Uso - Procesar Facturas

```bash
curl -X POST "http://localhost:8000/api/v1/automation/procesar" \
  -H "Content-Type: application/json" \
  -d '{
    "limite_facturas": 20,
    "modo_debug": true,
    "solo_proveedor_id": 123
  }'
```

### Ejemplo de Respuesta

```json
{
  "success": true,
  "message": "Procesadas 15 facturas",
  "data": {
    "resumen_general": {
      "facturas_procesadas": 15,
      "aprobadas_automaticamente": 12,
      "enviadas_revision": 3,
      "errores": 0,
      "tasa_automatizacion": 80.0
    },
    "facturas_procesadas": [
      {
        "factura_id": 1001,
        "numero_factura": "FAC-2024-001",
        "decision": "aprobacion_automatica",
        "confianza": 0.92,
        "motivo": "Factura recurrente con patrón mensual consistente",
        "es_recurrente": true,
        "patron_temporal": "mensual_fijo"
      }
    ]
  }
}
```

## Configuración

### Parámetros Configurables

```python
# Configuración del motor de decisiones
decision_engine_config = {
    "confianza_minima_aprobacion": 0.85,
    "requiere_orden_compra": False,
    "peso_recurrencia": 0.25,
    "peso_patron_temporal": 0.20,
    "peso_estabilidad_monto": 0.20
}

# Configuración del detector de patrones
pattern_detector_config = {
    "dias_historico": 90,
    "min_facturas_patron": 3,
    "tolerancia_variacion_monto": 0.10,
    "tolerancia_dias_patron": 7
}
```

### Configuración de Notificaciones

```python
# Configuración de notificaciones
notification_config = {
    "activar_email": True,
    "activar_sistema": True,
    "incluir_detalles_tecnicos": False,
    "idioma": "es"
}
```

## Tareas Programadas

### Ejecución Automática

El sistema incluye tareas programadas para procesamiento automático:

```python
# app/tasks/automation_tasks.py
from app.tasks import ejecutar_automatizacion_programada

# Ejecutar cada hora en horario laboral
resultado = ejecutar_automatizacion_programada()
```

### Configuración con Cron

```bash
# Ejecutar cada hora de 9 AM a 5 PM, lunes a viernes
0 9-17 * * 1-5 cd /path/to/afe-backend && python -c "from app.tasks import ejecutar_automatizacion_programada; ejecutar_automatizacion_programada()"
```

## Monitoreo y Auditoría

### Logs de Auditoría

Todas las decisiones automáticas se registran en la tabla `audit_logs` con:

- **Acción**: `aprobacion_automatica` o `revision_requerida`
- **Usuario**: `sistema_automatico`
- **Detalles**: Criterios evaluados, confianza, patrones detectados

### Métricas Clave

- **Tasa de Automatización**: % de facturas aprobadas automáticamente
- **Precisión**: % de facturas automáticas sin errores posteriores
- **Tiempo de Procesamiento**: Promedio por factura
- **Cobertura**: % de facturas elegibles para automatización

## Algoritmos de Detección

### Generación de Fingerprints

1. **Fingerprint Principal**: Hash SHA-256 del concepto normalizado
2. **Fingerprint de Concepto**: Basado en palabras clave principales
3. **Fingerprint Tolerante**: Permite variaciones menores en montos
4. **Fingerprint de Orden de Compra**: Para facturas con OC

### Normalización de Conceptos

```python
def normalizar_concepto(concepto_original):
    # 1. Convertir a minúsculas
    # 2. Remover acentos y caracteres especiales
    # 3. Eliminar números de referencia variables
    # 4. Expandir abreviaciones comunes
    # 5. Aplicar diccionario de términos médicos
    # 6. Remover palabras de relleno
```

### Detección de Patrones Temporales

- **Mensual Fijo**: Facturas cada 30±7 días
- **Quincenal**: Facturas cada 15±3 días
- **Semanal**: Facturas cada 7±2 días
- **Trimestral**: Facturas cada 90±15 días
- **Irregular pero Consistente**: Variación <50% en intervalos

## Casos de Uso Soportados

### 1. Facturas de Servicios Médicos Recurrentes
- Consultas médicas regulares
- Terapias programadas
- Medicamentos periódicos

### 2. Facturas de Proveedores Confiables
- Servicios de limpieza
- Mantenimiento programado
- Suministros regulares

### 3. Facturas con Orden de Compra
- Material médico autorizado
- Equipos con contrato marco

## Limitaciones y Consideraciones

### Limitaciones Actuales

1. **Nuevos Proveedores**: Requieren mínimo 3 facturas históricas
2. **Variaciones Grandes**: Cambios >10% en monto requieren revisión
3. **Conceptos Nuevos**: Facturas con conceptos no vistos anteriormente
4. **Fechas Irregulares**: Patrones muy variables no son detectados

### Consideraciones de Seguridad

1. **Auditoría Completa**: Todas las decisiones se registran
2. **Revisión Periódica**: Validación manual de decisiones automáticas
3. **Umbrales Conservadores**: Preferencia por falsos negativos vs. falsos positivos
4. **Rollback**: Posibilidad de deshacer decisiones automáticas

## Mantenimiento

### Actualización de Algoritmos

1. **Versionado**: Cada cambio incrementa `version_algoritmo`
2. **Migración**: Reprocesamiento de facturas con versiones anteriores
3. **A/B Testing**: Comparación de versiones en paralelo

### Optimización de Performance

1. **Índices de BD**: En campos de búsqueda frecuente
2. **Cache**: Resultados de normalización y fingerprints
3. **Batch Processing**: Procesamiento en lotes para eficiencia

## Roadmap Futuro

### Mejoras Planificadas

1. **Machine Learning**: Algoritmos de aprendizaje automático
2. **OCR Avanzado**: Extracción mejorada de datos de PDFs
3. **Integración ERP**: Conexión directa con sistemas empresariales
4. **Dashboard**: Interface web para monitoreo en tiempo real
5. **APIs Externas**: Validación con bases de datos gubernamentales

### Nuevas Funcionalidades

1. **Aprobación por Monto**: Límites automáticos por proveedor
2. **Flujos Personalizados**: Reglas específicas por departamento
3. **Alertas Proactivas**: Detección de anomalías en patrones
4. **Reportería Avanzada**: Analytics de automatización

---

## Contacto y Soporte

Para consultas sobre el sistema de automatización:

- **Documentación**: Ver archivo README.md del proyecto
- **Logs**: Revisar logs en `/var/log/afe-backend/automation.log`
- **Auditoría**: Consultar tabla `audit_logs` en base de datos
- **Configuración**: Modificar via API `/automation/configuracion`