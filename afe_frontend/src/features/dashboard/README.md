# Dashboard Feature - Arquitectura Modular

## Descripción General

El módulo Dashboard ha sido refactorizado siguiendo las mejores prácticas de arquitectura frontend moderna, transformando un archivo monolítico de estructura modular, mantenible y escalable.

## Estructura de Carpetas

```
dashboard/
├── components/              # Componentes UI reutilizables
│   ├── StatsCards.tsx      # Tarjetas de estadísticas
│   ├── FilterBar.tsx       # Barra de filtros y búsqueda
│   ├── FacturasTable.tsx   # Tabla de facturas con paginación
│   ├── FacturaFormModal.tsx # Modal profesional para crear/editar facturas
│   ├── FacturaActionsMenu.tsx  # Menú de acciones contextuales
│   └── index.ts            # Barrel export
├── hooks/                   # Custom React Hooks
│   ├── useDashboardData.ts # Hook para gestión de datos del dashboard
│   ├── useFacturaDialog.ts # Hook para gestión del diálogo
│   └── index.ts            # Barrel export
├── services/                # Capa de servicios API
│   └── facturas.service.ts # Servicio de facturas (API calls)
├── types/                   # Definiciones de tipos TypeScript
│   └── index.ts            # Tipos e interfaces
├── utils/                   # Funciones utilitarias
│   ├── formatters.ts       # Formateo de datos (moneda, fechas)
│   ├── estadoHelpers.ts    # Helpers para estados de facturas
│   └── index.ts            # Barrel export
├── constants/               # Constantes y configuraciones
│   └── index.ts            # Estados, colores, configuraciones
├── DashboardPage.tsx        # Componente principal (270 líneas)
└── README.md               # Esta documentación
```

## Beneficios de la Refactorización

### 1. **Separación de Responsabilidades**
- **Componentes**: UI pura sin lógica de negocio
- **Hooks**: Lógica de estado y efectos secundarios
- **Services**: Comunicación con API
- **Utils**: Funciones puras y reutilizables
- **Types**: Definiciones de tipos centralizadas

### 2. **Reusabilidad**
- Componentes pueden ser usados en otras partes de la aplicación
- Hooks pueden ser compartidos entre features
- Servicios proporcionan una interfaz consistente para la API

### 3. **Mantenibilidad**
- Código organizado y fácil de encontrar
- Cambios aislados en módulos específicos
- Menos conflictos en git al trabajar en equipo

### 4. **Testabilidad**
- Componentes UI pueden ser testeados de forma aislada
- Hooks pueden ser testeados con `@testing-library/react-hooks`
- Servicios pueden ser mockeados fácilmente

### 5. **Type Safety**
- Tipos centralizados en un solo lugar
- Autocompletado mejorado en IDE
- Menos errores en tiempo de ejecución

## Componentes Principales

### StatsCards
Muestra las tarjetas de estadísticas del dashboard.

**Props:**
- `stats: DashboardStats` - Estadísticas a mostrar

### FilterBar
Barra de filtros y búsqueda con botones de vista (admin).

**Props:**
- `searchTerm: string`
- `onSearchChange: (value: string) => void`
- `filterEstado: EstadoFactura | 'todos'`
- `onFilterEstadoChange: (value: EstadoFactura | 'todos') => void`
- `vistaFacturas?: VistaFacturas`
- `onVistaFacturasChange?: (value: VistaFacturas) => void`
- `totalTodasFacturas?: number`
- `totalAsignadas?: number`
- `onExport: () => void`
- `isAdmin?: boolean`

### FacturasTable
Tabla de facturas con paginación y acciones.

**Props:**
- `facturas: Factura[]`
- `page: number`
- `rowsPerPage: number`
- `onPageChange: (newPage: number) => void`
- `onRowsPerPageChange: (newRowsPerPage: number) => void`
- `onOpenDialog: (mode: DialogMode, factura: Factura) => void`
- `onMenuClick: (event: React.MouseEvent<HTMLElement>, factura: Factura) => void`
- `isAdmin?: boolean`

### FacturaFormModal
Modal profesional y moderno para crear y editar facturas con diseño de gradientes, validación de formularios y UX mejorada.

**Props:**
- `open: boolean` - Controla si el modal está abierto
- `mode: DialogMode` - 'create' | 'edit' (no incluye 'view')
- `formData: FacturaFormData` - Datos del formulario
- `onFormChange: (field: keyof FacturaFormData, value: string) => void` - Manejador de cambios
- `onClose: () => void` - Callback para cerrar el modal
- `onSave: () => void` - Callback para guardar
- `error?: string` - Mensaje de error opcional

**Nota:** Para ver detalles de factura se usa `FacturaDetailModal` importado desde `../../components/Facturas/`

### FacturaActionsMenu
Menú contextual con acciones sobre facturas (aprobar, rechazar, eliminar).

**Props:**
- `anchorEl: HTMLElement | null`
- `factura: Factura | null`
- `onClose: () => void`
- `onApprove: (factura: Factura) => void`
- `onReject: (factura: Factura) => void`
- `onDelete: (factura: Factura) => void`

## Hooks Personalizados

### useDashboardData
Hook principal para gestión de datos del dashboard.

**Parámetros:**
```typescript
{
  userRole?: string;
  filterEstado: EstadoFactura | 'todos';
  vistaFacturas: VistaFacturas;
}
```

**Retorna:**
```typescript
{
  facturas: Factura[];
  stats: DashboardStats;
  totalTodasFacturas: number;
  totalAsignadas: number;
  loading: boolean;
  error: string;
  loadData: () => Promise<void>;
  clearError: () => void;
}
```

### useFacturaDialog
Hook para gestión del estado del diálogo de facturas.

**Retorna:**
```typescript
{
  openDialog: boolean;
  dialogMode: DialogMode;
  selectedFactura: Factura | null;
  formData: FacturaFormData;
  setFormData: React.Dispatch<React.SetStateAction<FacturaFormData>>;
  openDialogWith: (mode: DialogMode, factura?: Factura) => void;
  closeDialog: () => void;
}
```

## Servicios

### facturasService
Servicio centralizado para todas las operaciones de API relacionadas con facturas.

**Métodos:**
- `fetchFacturas(params)` - Obtener facturas con filtros
- `createFactura(data)` - Crear nueva factura
- `updateFactura(id, data)` - Actualizar factura existente
- `deleteFactura(id)` - Eliminar factura
- `approveFactura(id, aprobadoPor)` - Aprobar factura
- `rejectFactura(id, rechazadoPor, motivo)` - Rechazar factura
- `getExportUrl(estado?, soloAsignadas?)` - Obtener URL de exportación

## Utilidades

### Formatters
- `formatCurrency(amount)` - Formatear moneda
- `formatDate(dateString)` - Formatear fecha
- `extractDateForInput(dateString)` - Extraer fecha para inputs
- `getTodayDate()` - Obtener fecha actual

### Estado Helpers
- `getEstadoColor(estado)` - Obtener color del estado
- `getEstadoLabel(estado)` - Obtener etiqueta del estado
- `isEstadoAprobado(estado)` - Verificar si está aprobado
- `isEstadoRechazado(estado)` - Verificar si está rechazado

## Tipos Principales

```typescript
interface Factura {
  id: number;
  numero_factura: string;
  cufe?: string;
  nit_emisor: string;
  nombre_emisor: string;
  monto_total: number;
  fecha_emision: string;
  fecha_vencimiento?: string;
  estado: EstadoFactura;
  responsable_id?: number;
  observaciones?: string;
  archivo_adjunto?: string;
}

interface DashboardStats {
  total: number;
  pendientes: number;
  en_revision: number;
  aprobadas: number;
  aprobadas_auto: number;
  rechazadas: number;
}

type EstadoFactura =
 
  | 'en_revision'
  | 'aprobada'
  | 'aprobado'
  | 'aprobada_auto'
  | 'rechazada'
  | 'rechazado';

type DialogMode = 'view' | 'edit' | 'create';
type VistaFacturas = 'todas' | 'asignadas';
```

## Comparación: Antes vs Después

### Antes (Monolítico)
- ✗ 1 archivo de 1070 líneas
- ✗ Todo mezclado: UI, lógica, servicios, tipos
- ✗ Difícil de mantener y testear
- ✗ Componentes no reutilizables
- ✗ Difícil de escalar

### Después (Modular)
- ✓ 18 archivos organizados por responsabilidad
- ✓ Separación clara: UI, lógica, servicios, tipos
- ✓ Fácil de mantener y testear
- ✓ Componentes reutilizables
- ✓ Escalable y extensible
- ✓ Mejor experiencia de desarrollo (DX)

## Mejores Prácticas Aplicadas

1. **Single Responsibility Principle**: Cada archivo tiene una única responsabilidad
2. **DRY (Don't Repeat Yourself)**: Código reutilizable en utils y helpers
3. **Composition over Inheritance**: Componentes pequeños y componibles
4. **Custom Hooks**: Lógica de estado encapsulada y reutilizable
5. **Service Layer**: Abstracción de llamadas API
6. **TypeScript**: Tipado fuerte para prevenir errores
7. **Barrel Exports**: Importaciones limpias y organizadas
8. **Separation of Concerns**: UI, lógica y datos separados

## Próximos Pasos Recomendados

1. **Testing**: Agregar tests unitarios para componentes, hooks y servicios
2. **Error Boundaries**: Implementar manejo de errores a nivel de componente
3. **Optimización**: Implementar React.memo para componentes pesados
4. **Storybook**: Documentar componentes visualmente
5. **Internacionalización**: Agregar soporte i18n si es necesario
6. **Accessibility**: Mejorar accesibilidad (ARIA labels, keyboard navigation)

## Contribución

Al agregar nuevas funcionalidades al dashboard:

1. Crear componentes pequeños y reutilizables en `components/`
2. Extraer lógica compleja a custom hooks en `hooks/`
3. Agregar llamadas API al servicio en `services/`
4. Definir tipos en `types/`
5. Agregar constantes en `constants/`
6. Crear helpers/utils en `utils/`

---

