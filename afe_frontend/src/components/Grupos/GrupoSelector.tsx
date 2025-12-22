/**
 * Componente GrupoSelector - Selector de grupos multi-tenant
 *
 * Permite a los usuarios cambiar entre los grupos a los que tienen acceso.
 * - Usuarios normales: Solo ven su grupo (readonly)
 * - Administradores: Pueden cambiar entre todos los grupos
 *
 * @author 
 * @date 2025-12-04
 */

import React, { useEffect } from 'react';
import {
  FormControl,
  Select,
  MenuItem,
  Box,
  Typography,
  CircularProgress,
  SelectChangeEvent,
  Chip,
} from '@mui/material';
import { Business as BusinessIcon } from '@mui/icons-material';
import { useAppSelector } from '../../app/hooks';
import { useLocation } from 'react-router-dom';

interface GrupoSelectorProps {
  disabled?: boolean;
  variant?: 'outlined' | 'filled' | 'standard';
  size?: 'small' | 'medium';
}

/**
 * Selector de grupos para cambiar el contexto multi-tenant
 *
 * Características:
 * - Si usuario tiene 1 grupo: Muestra solo texto (readonly)
 * - Si usuario tiene múltiples grupos: Muestra selector
 * - Al cambiar grupo: Recarga la página para aplicar nuevo contexto
 * - Persiste selección en localStorage
 */
export const GrupoSelector: React.FC<GrupoSelectorProps> = ({
  disabled = false,
  variant = 'outlined',
  size = 'small',
}) => {
  const { user } = useAppSelector((state) => state.auth);
  const location = useLocation();

  const isSuperAdmin = user?.rol?.toLowerCase() === 'superadmin';
  const grupos = user?.grupos || [];

  /**
   * ARQUITECTURA KISS (Keep It Simple, Stupid) 2025-12-09:
   * Grupo raíz (grupo_padre_id = NULL) = Vista Global
   *
   * Semánticamente correcto: el grupo corporativo raíz representa toda la organización.
   * Simple, sin campos adicionales en BD, sin hardcodear nombres.
   */
  const grupoVistaGlobal = grupos.find(g => g.grupo_padre_id === null) || null;

  const grupoIdStorage = localStorage.getItem('grupo_id');
  const valorInicial = grupoIdStorage ? parseInt(grupoIdStorage) : (isSuperAdmin && grupoVistaGlobal ? grupoVistaGlobal.id : null);

  const [grupoActualId, setGrupoActualId] = React.useState<number | null>(valorInicial);

  // Sincronizar con localStorage al montar
  useEffect(() => {
    const storedGrupoId = localStorage.getItem('grupo_id');
    if (storedGrupoId) {
      // Hay un grupo específico seleccionado
      setGrupoActualId(parseInt(storedGrupoId));
    } else if (isSuperAdmin && grupoVistaGlobal) {
      // Vista global: grupo raíz seleccionado pero SIN grupo_id en localStorage
      setGrupoActualId(grupoVistaGlobal.id);
      // IMPORTANTE: NO guardar en localStorage para mantener vista global
    }
  }, [isSuperAdmin, grupoVistaGlobal]);

  // Si no hay usuario, no mostrar nada (después de los hooks)
  if (!user) {
    return null;
  }

  /**
   * ARQUITECTURA PROFESIONAL 2025-12-09:
   * Ocultar selector en rutas administrativas donde no aplica filtrado
   *
   * Rutas donde NO se muestra (vistas globales):
   * - /superadmin/dashboard (Dashboard Admin)
   * - /superadmin/grupos (Gestión de Grupos)
   * - /superadmin/usuarios (Gestión de Usuarios)
   * - /superadmin/roles (Gestión de Roles)
   *
   * Rutas donde SÍ se muestra (vistas operacionales):
   * - /dashboard (Vista Operacional - con opción "Todos los Grupos")
   * - /facturas (Por Revisar)
   * - /gestion/proveedores (Proveedores)
   * - /email-config (Configuración de Correos)
   */
  const rutasAdministrativas = [
    '/superadmin/dashboard',
    '/superadmin/grupos',
    '/superadmin/usuarios',
    '/superadmin/roles'
  ];

  const estaEnRutaAdministrativa = rutasAdministrativas.some(
    ruta => location.pathname.startsWith(ruta)
  );

  if (isSuperAdmin && estaEnRutaAdministrativa) {
    return null; // Ocultar selector en rutas administrativas
  }

  const grupoActual = grupos.find((g) => g.id === grupoActualId);

  // Loading state - Solo mostrar si realmente está cargando (tiene grupos pero aún no seleccionó)
  // NO mostrar loading si es SuperAdmin con Zentria Colombia (vista global válida)
  if (!grupoActual && grupos.length > 0 && !isSuperAdmin) {
    return (
      <Box display="flex" alignItems="center" gap={1} px={2}>
        <CircularProgress size={16} />
        <Typography variant="caption" color="text.secondary">
          Cargando grupo...
        </Typography>
      </Box>
    );
  }

  // Si no tiene grupos asignados
  if (grupos.length === 0) {
    return (
      <Box display="flex" alignItems="center" gap={1} px={2}>
        <BusinessIcon fontSize="small" color="disabled" />
        <Typography variant="body2" color="text.secondary">
          Sin grupo asignado
        </Typography>
      </Box>
    );
  }

  // Si solo tiene 1 grupo: Mostrar readonly
  if (grupos.length === 1) {
    return (
      <Box display="flex" alignItems="center" gap={1} px={2}>
        <BusinessIcon fontSize="small" color="action" />
        <Typography variant="body2" fontWeight={600} color="text.primary">
          {grupos[0].nombre}
        </Typography>
      </Box>
    );
  }

  // Usuario tiene múltiples grupos: Mostrar selector
  const handleCambiarGrupo = (event: SelectChangeEvent<number>) => {
    const nuevoGrupoId = event.target.value as number;

    /**
     * ARQUITECTURA KISS 2025-12-09:
     * Grupo raíz (grupo_padre_id = NULL) = Vista Global
     *
     * Cuando SuperAdmin selecciona grupo raíz:
     * - NO se almacena grupo_id en localStorage
     * - Backend recibe request SIN X-Grupo-Id header
     * - Resultado: Vista de TODAS las facturas (todos los grupos)
     *
     * Cuando selecciona cualquier otro grupo:
     * - SÍ se almacena grupo_id en localStorage
     * - Backend recibe request CON X-Grupo-Id header
     * - Resultado: Vista filtrada por ese grupo específico
     */
    const esGrupoRaiz = isSuperAdmin && grupoVistaGlobal && nuevoGrupoId === grupoVistaGlobal.id;

    // Mensaje personalizado según el cambio
    let mensaje = '¿Cambiar de grupo? Se recargará la página para aplicar los cambios.';
    if (esGrupoRaiz) {
      const nombreGrupo = grupoVistaGlobal?.nombre || 'grupo raíz';
      mensaje = `¿Cambiar a vista global (${nombreGrupo})? Verás facturas de todos los grupos.`;
    }

    // Confirmar cambio
    if (window.confirm(mensaje)) {
      // Actualizar localStorage según la lógica semántica
      if (esGrupoRaiz) {
        // Grupo raíz = Vista Global → NO enviar X-Grupo-Id header
        localStorage.removeItem('grupo_id');
      } else {
        // Cualquier otro grupo = Vista Específica → Enviar X-Grupo-Id header
        localStorage.setItem('grupo_id', nuevoGrupoId.toString());
      }

      // Recargar página para aplicar nuevo contexto
      window.location.reload();
    }
  };

  return (
    <FormControl
      variant={variant}
      size={size}
      disabled={disabled}
      sx={{
        minWidth: 220,
        bgcolor: 'background.paper',
        borderRadius: 1,
      }}
    >
      <Select
        value={grupoActualId ?? (grupoVistaGlobal?.id ?? 0)}
        onChange={handleCambiarGrupo}
        displayEmpty
        startAdornment={
          <BusinessIcon
            fontSize="small"
            sx={{ mr: 1, color: 'action.active' }}
          />
        }
        sx={{
          '& .MuiSelect-select': {
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          },
        }}
      >
        {/* Placeholder si no hay grupo seleccionado */}
        {!grupoActualId && !isSuperAdmin && (
          <MenuItem value={0} disabled>
            <Typography variant="body2" color="text.secondary">
              Seleccionar grupo...
            </Typography>
          </MenuItem>
        )}

        {/* Lista de grupos */}
        {grupos.map((grupo) => {
          const esGrupoRaiz = isSuperAdmin && grupoVistaGlobal && grupo.id === grupoVistaGlobal.id;

          return (
            <MenuItem key={grupo.id} value={grupo.id}>
              <Box sx={{ width: '100%' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight={600}>
                    {grupo.nombre}
                  </Typography>
                  {esGrupoRaiz && (
                    <Chip
                      label="Vista Global"
                      size="small"
                      sx={{
                        height: 18,
                        fontSize: '0.65rem',
                        background: 'linear-gradient(135deg, #80006a, #e91e63)',
                        color: 'white',
                        fontWeight: 700,
                        '& .MuiChip-label': {
                          px: 1,
                        },
                      }}
                    />
                  )}
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {grupo.codigo}
                  {esGrupoRaiz && ' • Incluye todos los grupos del sistema'}
                </Typography>
              </Box>
            </MenuItem>
          );
        })}
      </Select>
    </FormControl>
  );
};

export default GrupoSelector;
