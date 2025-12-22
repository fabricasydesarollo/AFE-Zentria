# Guía de Estilos de Botones de Acción

## 📋 Descripción

Este documento describe los estilos estandarizados para botones de acción (`IconButton`) utilizados en toda la aplicación. Estos estilos garantizan consistencia visual y mejoran la experiencia del usuario (UX).

## 🎨 Estilos Disponibles

### 1. **View** (Ver Detalles - Ojo)
```typescript
import { actionButtonStyles } from '../theme/buttonStyles';

<IconButton sx={actionButtonStyles.view}>
  <Visibility />
</IconButton>
```

**Características:**
- Color: Violeta principal (`zentriaColors.violeta.main`)
- Hover: Fondo violeta translúcido (15% opacidad)
- Escala: 1.15x en hover
- Sombra: Violeta con 40% opacidad

---

### 2. **Edit** (Editar - Lápiz)
```typescript
<IconButton sx={actionButtonStyles.edit}>
  <Edit />
</IconButton>
```

**Características:**
- Color: Naranja principal (`zentriaColors.naranja.main`)
- Hover: Fondo naranja translúcido (15% opacidad)
- Escala: 1.15x en hover
- Sombra: Naranja con 40% opacidad

---

### 3. **Approve** (Aprobar - Check)
```typescript
<IconButton sx={actionButtonStyles.approve}>
  <CheckCircle />
</IconButton>
```

**Características:**
- Color: Verde principal (`zentriaColors.verde.main`)
- Hover: Fondo verde translúcido (15% opacidad)
- Escala: 1.15x en hover
- Sombra: Verde con 40% opacidad

---

### 4. **Reject** (Rechazar - X)
```typescript
<IconButton sx={actionButtonStyles.reject}>
  <Cancel />
</IconButton>
```

**Características:**
- Color: Rojo (`#f44336`)
- Hover: Fondo rojo translúcido (15% opacidad)
- Escala: 1.15x en hover
- Sombra: Rojo con 40% opacidad

---

### 5. **Delete** (Eliminar - Basura)
```typescript
<IconButton sx={actionButtonStyles.delete}>
  <Delete />
</IconButton>
```

**Características:**
- Color: Rojo (`#f44336`)
- Hover: Fondo rojo translúcido (15% opacidad)
- Escala: 1.15x en hover
- Sombra: Rojo con 40% opacidad

---

### 6. **More** (Más Acciones - Tres Puntos)
```typescript
<IconButton sx={actionButtonStyles.more}>
  <MoreVert />
</IconButton>
```

**Características:**
- Color: Por defecto del tema
- Hover: Fondo gris claro (`action.hover`)
- Escala: 1.15x en hover
- Sombra: Gris con 10% opacidad

---

### 7. **Default** (Genérico)
```typescript
<IconButton sx={actionButtonStyles.default}>
  <Icon />
</IconButton>
```

**Características:**
- Sin color específico
- Hover: Fondo gris claro (`action.hover`)
- Escala: 1.15x en hover

---

## 🎯 Props de Tooltip Estandarizados

```typescript
import { tooltipProps } from '../theme/buttonStyles';

<Tooltip title="Descripción de la acción" {...tooltipProps}>
  <IconButton>
    <Icon />
  </IconButton>
</Tooltip>
```

**Características:**
- `arrow: true` - Muestra flecha apuntando al botón
- `placement: 'top'` - Tooltip aparece arriba del botón
- `enterDelay: 300` - Delay de 300ms antes de mostrar
- `leaveDelay: 0` - Se oculta inmediatamente al salir

---

## 📝 Ejemplo Completo

```typescript
import { actionButtonStyles, tooltipProps } from '../theme/buttonStyles';
import { IconButton, Tooltip } from '@mui/material';
import { Visibility, Edit, MoreVert } from '@mui/icons-material';

function ActionButtons({ factura }) {
  return (
    <>
      {/* Botón Ver Detalles */}
      <Tooltip title={`Ver detalles de la factura ${factura.numero}`} {...tooltipProps}>
        <IconButton
          size="small"
          onClick={() => handleView(factura)}
          sx={actionButtonStyles.view}
        >
          <Visibility fontSize="small" />
        </IconButton>
      </Tooltip>

      {/* Botón Editar */}
      <Tooltip title={`Editar factura ${factura.numero}`} {...tooltipProps}>
        <IconButton
          size="small"
          onClick={() => handleEdit(factura)}
          sx={actionButtonStyles.edit}
        >
          <Edit fontSize="small" />
        </IconButton>
      </Tooltip>

      {/* Botón Más Acciones */}
      <Tooltip title="Más acciones" {...tooltipProps}>
        <IconButton
          size="small"
          onClick={(e) => handleMenuClick(e, factura)}
          sx={actionButtonStyles.more}
        >
          <MoreVert fontSize="small" />
        </IconButton>
      </Tooltip>
    </>
  );
}
```

---

## 🎬 Animaciones

Todos los estilos incluyen:

### **Transición Suave**
```css
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1)
```

### **Hover Effect**
- Escala: `transform: scale(1.15)`
- Fondo translúcido del color del botón
- Sombra difusa con el color del botón

### **Active Effect**
- Escala: `transform: scale(0.95)`
- Feedback visual al hacer clic

---

## 📍 Dónde se Usan

### ✅ Implementado en:
- [x] `features/dashboard/components/FacturasTable.tsx`
- [x] `features/facturas/FacturasPage.tsx`

### 🔄 Por Implementar (si es necesario):
- [ ] `features/email-config/EmailConfigPage.tsx`
- [ ] `features/proveedores/tabs/ProveedoresTab.tsx`
- [ ] `features/admin/ResponsablesPage.tsx`

---

## 🔧 Personalización

Si necesitas crear un estilo personalizado:

```typescript
// En buttonStyles.ts
export const actionButtonStyles = {
  // ... estilos existentes

  custom: {
    ...baseActionButtonStyle,
    color: '#YOUR_COLOR',
    '&:hover': {
      bgcolor: '#YOUR_COLOR15',  // 15% opacidad
      transform: 'scale(1.15)',
      boxShadow: '0 2px 8px #YOUR_COLOR40',  // 40% opacidad
    },
  } as SxProps<Theme>,
};
```

---

## 🎨 Paleta de Colores

| Acción | Color | Código HEX |
|--------|-------|------------|
| Ver | Violeta | `zentriaColors.violeta.main` |
| Editar | Naranja | `zentriaColors.naranja.main` |
| Aprobar | Verde | `zentriaColors.verde.main` |
| Rechazar | Rojo | `#f44336` |
| Eliminar | Rojo | `#f44336` |
| Más | Gris | `action.hover` |

---

## ✅ Mejores Prácticas

1. **Siempre usa `tooltipProps`** para consistencia
2. **Describe claramente la acción** en el tooltip (ej: "Ver detalles de la factura E921")
3. **Usa `size="small"`** para botones de acción en tablas
4. **Usa `fontSize="small"`** en los iconos para mejor proporción
5. **Envuelve botones disabled en `<span>`** para que el tooltip funcione

```typescript
// ✅ CORRECTO - Tooltip funciona con botón disabled
<Tooltip title="Aprobar" {...tooltipProps}>
  <span>
    <Button disabled={true}>Aprobar</Button>
  </span>
</Tooltip>

// ❌ INCORRECTO - Tooltip no funciona con botón disabled
<Tooltip title="Aprobar" {...tooltipProps}>
  <Button disabled={true}>Aprobar</Button>
</Tooltip>
```

---

## 📊 Beneficios

✅ **Consistencia Visual** - Mismo look & feel en toda la app
✅ **Mejor UX** - Feedback visual inmediato al usuario
✅ **Código Reutilizable** - Menos código duplicado
✅ **Fácil Mantenimiento** - Cambios centralizados
✅ **Accesibilidad** - Tooltips descriptivos y delays apropiados
✅ **Performance** - Transiciones optimizadas con cubic-bezier

---

## 🚀 Actualización de Componentes Existentes

Para actualizar un componente que usa estilos inline:

### Antes:
```typescript
<IconButton
  sx={{
    color: zentriaColors.violeta.main,
    '&:hover': {
      bgcolor: zentriaColors.violeta.main + '15',
    }
  }}
>
```

### Después:
```typescript
import { actionButtonStyles } from '../theme/buttonStyles';

<IconButton sx={actionButtonStyles.view}>
```

**Resultado:** Menos código, más consistente, mejor UX! 🎉
