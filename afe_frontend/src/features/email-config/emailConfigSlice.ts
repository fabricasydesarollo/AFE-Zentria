/**
 * Email Config Redux Slice
 * Estado global para configuración de extracción de correos
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import emailConfigService, {
  CuentaCorreoSummary,
  CuentaCorreoDetalle,
  NitConfiguracion,
  HistorialExtraccion,
  EstadisticasExtraccion,
} from '../../services/emailConfigService';

// ==================== ESTADO ====================

interface EmailConfigState {
  // Cuentas
  cuentas: CuentaCorreoSummary[];
  cuentaActual: CuentaCorreoDetalle | null;
  loadingCuentas: boolean;
  loadingCuentaActual: boolean;

  // NITs
  nits: NitConfiguracion[];
  loadingNits: boolean;

  // Historial y estadísticas
  historial: HistorialExtraccion[];
  estadisticas: EstadisticasExtraccion | null;
  loadingHistorial: boolean;
  loadingEstadisticas: boolean;

  // UI State
  filtros: {
    solo_activas: boolean;
    organizacion: string | null;
    busqueda: string;
  };

  // Errores
  error: string | null;
}

const initialState: EmailConfigState = {
  cuentas: [],
  cuentaActual: null,
  loadingCuentas: false,
  loadingCuentaActual: false,

  nits: [],
  loadingNits: false,

  historial: [],
  estadisticas: null,
  loadingHistorial: false,
  loadingEstadisticas: false,

  filtros: {
    solo_activas: false,
    organizacion: null,
    busqueda: '',
  },

  error: null,
};

// ==================== THUNKS ====================

// Cargar cuentas
export const cargarCuentas = createAsyncThunk(
  'emailConfig/cargarCuentas',
  async (params?: { solo_activas?: boolean; organizacion?: string }) => {
    return await emailConfigService.listarCuentas(params);
  }
);

// Cargar detalle de cuenta
export const cargarCuentaDetalle = createAsyncThunk(
  'emailConfig/cargarCuentaDetalle',
  async (cuentaId: number) => {
    return await emailConfigService.obtenerCuenta(cuentaId);
  }
);

// Crear cuenta
export const crearCuenta = createAsyncThunk(
  'emailConfig/crearCuenta',
  async (data: {
    email: string;
    nombre_descriptivo?: string;
    fetch_limit?: number;
    fetch_days?: number;
    organizacion?: string;
    grupo_id?: number;
    nits?: string[];
  }) => {
    return await emailConfigService.crearCuenta(data);
  }
);

// Actualizar cuenta
export const actualizarCuenta = createAsyncThunk(
  'emailConfig/actualizarCuenta',
  async (payload: {
    cuentaId: number;
    data: {
      nombre_descriptivo?: string;
      fetch_limit?: number;
      fetch_days?: number;
      max_correos_por_ejecucion?: number;
      ventana_inicial_dias?: number;
      activa?: boolean;
      organizacion?: string;
      actualizada_por?: string;
    };
  }) => {
    const { cuentaId, data } = payload;
    return await emailConfigService.actualizarCuenta(cuentaId, data);
  }
);

// Toggle cuenta activa
export const toggleCuentaActiva = createAsyncThunk(
  'emailConfig/toggleCuentaActiva',
  async (payload: { cuentaId: number; activa: boolean }) => {
    const { cuentaId, activa } = payload;
    return await emailConfigService.toggleCuentaActiva(cuentaId, activa);
  }
);

// Eliminar cuenta
export const eliminarCuenta = createAsyncThunk(
  'emailConfig/eliminarCuenta',
  async (cuentaId: number) => {
    await emailConfigService.eliminarCuenta(cuentaId);
    return cuentaId;
  }
);

// Cargar NITs
export const cargarNits = createAsyncThunk(
  'emailConfig/cargarNits',
  async (payload: { cuentaId: number; solo_activos?: boolean }) => {
    const { cuentaId, solo_activos = false } = payload;
    return await emailConfigService.listarNits(cuentaId, solo_activos);
  }
);

// Crear NIT
export const crearNit = createAsyncThunk(
  'emailConfig/crearNit',
  async (data: {
    cuenta_correo_id: number;
    nit: string;
    nombre_proveedor?: string;
    notas?: string;
  }) => {
    return await emailConfigService.crearNit(data);
  }
);

// Crear NITs en bulk
export const crearNitsBulk = createAsyncThunk(
  'emailConfig/crearNitsBulk',
  async (data: { cuenta_correo_id: number; nits: string[] }) => {
    return await emailConfigService.crearNitsBulk(data);
  }
);

// Toggle NIT activo
export const toggleNitActivo = createAsyncThunk(
  'emailConfig/toggleNitActivo',
  async (payload: { nitId: number; activo: boolean }) => {
    const { nitId, activo } = payload;
    return await emailConfigService.toggleNitActivo(nitId, activo);
  }
);

// Eliminar NIT
export const eliminarNit = createAsyncThunk(
  'emailConfig/eliminarNit',
  async (nitId: number) => {
    await emailConfigService.eliminarNit(nitId);
    return nitId;
  }
);

// Cargar historial
export const cargarHistorial = createAsyncThunk(
  'emailConfig/cargarHistorial',
  async (payload: { cuentaId: number; limit?: number }) => {
    const { cuentaId, limit = 50 } = payload;
    return await emailConfigService.obtenerHistorial(cuentaId, limit);
  }
);

// Cargar estadísticas
export const cargarEstadisticas = createAsyncThunk(
  'emailConfig/cargarEstadisticas',
  async (payload: { cuentaId: number; dias?: number }) => {
    const { cuentaId, dias = 30 } = payload;
    return await emailConfigService.obtenerEstadisticas(cuentaId, dias);
  }
);

// ==================== SLICE ====================

const emailConfigSlice = createSlice({
  name: 'emailConfig',
  initialState,
  reducers: {
    // Actualizar filtros
    setFiltros: (
      state,
      action: PayloadAction<Partial<EmailConfigState['filtros']>>
    ) => {
      state.filtros = { ...state.filtros, ...action.payload };
    },

    // Limpiar cuenta actual
    limpiarCuentaActual: (state) => {
      state.cuentaActual = null;
      state.nits = [];
      state.historial = [];
      state.estadisticas = null;
    },

    // Limpiar error
    limpiarError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // ===== CARGAR CUENTAS =====
    builder
      .addCase(cargarCuentas.pending, (state) => {
        state.loadingCuentas = true;
        state.error = null;
      })
      .addCase(cargarCuentas.fulfilled, (state, action) => {
        state.loadingCuentas = false;
        state.cuentas = action.payload;
      })
      .addCase(cargarCuentas.rejected, (state, action) => {
        state.loadingCuentas = false;
        state.error = action.error.message || 'Error al cargar cuentas';
      });

    // ===== CARGAR DETALLE DE CUENTA =====
    builder
      .addCase(cargarCuentaDetalle.pending, (state) => {
        state.loadingCuentaActual = true;
        state.error = null;
      })
      .addCase(cargarCuentaDetalle.fulfilled, (state, action) => {
        state.loadingCuentaActual = false;
        state.cuentaActual = action.payload;
        state.nits = action.payload.nits;
      })
      .addCase(cargarCuentaDetalle.rejected, (state, action) => {
        state.loadingCuentaActual = false;
        state.error = action.error.message || 'Error al cargar cuenta';
      });

    // ===== CREAR CUENTA =====
    builder
      .addCase(crearCuenta.pending, (state) => {
        state.error = null;
      })
      .addCase(crearCuenta.fulfilled, (state, action) => {
        // Agregar a la lista si cumple con los filtros actuales
        if (
          !state.filtros.solo_activas ||
          (state.filtros.solo_activas && action.payload.activa)
        ) {
          // Crear resumen para la lista
          const nuevaCuenta: CuentaCorreoSummary = {
            id: action.payload.id,
            email: action.payload.email,
            nombre_descriptivo: action.payload.nombre_descriptivo,
            activa: action.payload.activa,
            organizacion: action.payload.organizacion,
            total_nits: action.payload.nits.length,
            total_nits_activos: action.payload.nits.filter((n) => n.activo).length,
            creada_en: action.payload.creada_en,
          };
          state.cuentas.unshift(nuevaCuenta);
        }
      })
      .addCase(crearCuenta.rejected, (state, action) => {
        state.error = action.error.message || 'Error al crear cuenta';
      });

    // ===== TOGGLE CUENTA ACTIVA =====
    builder
      .addCase(toggleCuentaActiva.fulfilled, (state, action) => {
        // Actualizar en la lista
        const index = state.cuentas.findIndex((c) => c.id === action.payload.id);
        if (index !== -1) {
          state.cuentas[index].activa = action.payload.activa;
        }
        // Actualizar cuenta actual si está cargada
        if (state.cuentaActual?.id === action.payload.id) {
          state.cuentaActual.activa = action.payload.activa;
        }
      });

    // ===== ELIMINAR CUENTA =====
    builder
      .addCase(eliminarCuenta.fulfilled, (state, action) => {
        state.cuentas = state.cuentas.filter((c) => c.id !== action.payload);
        if (state.cuentaActual?.id === action.payload) {
          state.cuentaActual = null;
        }
      });

    // ===== CARGAR NITS =====
    builder
      .addCase(cargarNits.pending, (state) => {
        state.loadingNits = true;
        state.error = null;
      })
      .addCase(cargarNits.fulfilled, (state, action) => {
        state.loadingNits = false;
        state.nits = action.payload;
      })
      .addCase(cargarNits.rejected, (state, action) => {
        state.loadingNits = false;
        state.error = action.error.message || 'Error al cargar NITs';
      });

    // ===== CREAR NIT =====
    builder
      .addCase(crearNit.fulfilled, (state, action) => {
        state.nits.push(action.payload);
        // Actualizar contador en la cuenta actual
        if (state.cuentaActual?.id === action.payload.cuenta_correo_id) {
          state.cuentaActual.nits.push(action.payload);
        }
      });

    // ===== TOGGLE NIT ACTIVO =====
    builder
      .addCase(toggleNitActivo.fulfilled, (state, action) => {
        const index = state.nits.findIndex((n) => n.id === action.payload.id);
        if (index !== -1) {
          state.nits[index] = action.payload;
        }
      });

    // ===== ELIMINAR NIT =====
    builder
      .addCase(eliminarNit.fulfilled, (state, action) => {
        state.nits = state.nits.filter((n) => n.id !== action.payload);
        if (state.cuentaActual) {
          state.cuentaActual.nits = state.cuentaActual.nits.filter(
            (n) => n.id !== action.payload
          );
        }
      });

    // ===== CARGAR HISTORIAL =====
    builder
      .addCase(cargarHistorial.pending, (state) => {
        state.loadingHistorial = true;
        state.error = null;
      })
      .addCase(cargarHistorial.fulfilled, (state, action) => {
        state.loadingHistorial = false;
        state.historial = action.payload;
      })
      .addCase(cargarHistorial.rejected, (state, action) => {
        state.loadingHistorial = false;
        state.error = action.error.message || 'Error al cargar historial';
      });

    // ===== CARGAR ESTADÍSTICAS =====
    builder
      .addCase(cargarEstadisticas.pending, (state) => {
        state.loadingEstadisticas = true;
        state.error = null;
      })
      .addCase(cargarEstadisticas.fulfilled, (state, action) => {
        state.loadingEstadisticas = false;
        state.estadisticas = action.payload;
      })
      .addCase(cargarEstadisticas.rejected, (state, action) => {
        state.loadingEstadisticas = false;
        state.error = action.error.message || 'Error al cargar estadísticas';
      });
  },
});

export const { setFiltros, limpiarCuentaActual, limpiarError } = emailConfigSlice.actions;

export default emailConfigSlice.reducer;
