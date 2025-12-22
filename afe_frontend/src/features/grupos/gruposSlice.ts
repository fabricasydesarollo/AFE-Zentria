/**
 * Redux Slice para gestión de grupos multi-tenant
 *
 * Maneja el estado global de:
 * - Lista de grupos disponibles
 * - Árbol jerárquico de grupos
 * - Grupo actualmente seleccionado
 * - Estadísticas del grupo actual
 *
 * @author 
 * @date 2025-12-04
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import gruposService from '../../services/grupos.api';
import { Grupo, GrupoTree, GrupoStats } from '../../types/grupo.types';

// Estado del slice
interface GruposState {
  // Datos
  grupos: Grupo[];
  gruposTree: GrupoTree[];
  grupoActual: Grupo | null;
  estadisticas: GrupoStats | null;

  // Estados de carga
  loading: boolean;
  loadingTree: boolean;
  loadingStats: boolean;

  // Errores
  error: string | null;
}

// Estado inicial
const initialState: GruposState = {
  grupos: [],
  gruposTree: [],
  grupoActual: null,
  estadisticas: null,
  loading: false,
  loadingTree: false,
  loadingStats: false,
  error: null,
};

// ==================== ASYNC THUNKS ====================

/**
 * Cargar lista de grupos disponibles
 */
export const cargarGrupos = createAsyncThunk(
  'grupos/cargarGrupos',
  async (_, { rejectWithValue }) => {
    try {
      const response = await gruposService.listarGrupos();
      return response.grupos;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar grupos');
    }
  }
);

/**
 * Cargar árbol jerárquico completo de grupos
 */
export const cargarArbolGrupos = createAsyncThunk(
  'grupos/cargarArbolGrupos',
  async (_, { rejectWithValue }) => {
    try {
      return await gruposService.obtenerArbolGrupos();
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar árbol de grupos');
    }
  }
);

/**
 * Cargar detalle de un grupo específico y establecerlo como actual
 */
export const cargarGrupoActual = createAsyncThunk(
  'grupos/cargarGrupoActual',
  async (grupoId: number, { rejectWithValue }) => {
    try {
      return await gruposService.obtenerGrupo(grupoId);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar grupo');
    }
  }
);

/**
 * Cargar estadísticas del grupo actual
 */
export const cargarEstadisticas = createAsyncThunk(
  'grupos/cargarEstadisticas',
  async (grupoId: number, { rejectWithValue }) => {
    try {
      return await gruposService.obtenerEstadisticas(grupoId);
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar estadísticas');
    }
  }
);

/**
 * Cargar grupos del usuario actual
 * Útil para poblar el selector de grupos
 */
export const cargarMisGrupos = createAsyncThunk(
  'grupos/cargarMisGrupos',
  async (_, { rejectWithValue }) => {
    try {
      return await gruposService.obtenerMisGrupos();
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar mis grupos');
    }
  }
);

// ==================== SLICE ====================

const gruposSlice = createSlice({
  name: 'grupos',
  initialState,
  reducers: {
    /**
     * Establecer grupo actual manualmente
     * También actualiza localStorage para persistencia
     */
    setGrupoActual: (state, action: PayloadAction<Grupo | null>) => {
      state.grupoActual = action.payload;
      if (action.payload) {
        localStorage.setItem('grupo_id', action.payload.id.toString());
      } else {
        localStorage.removeItem('grupo_id');
      }
    },

    /**
     * Limpiar errores del estado
     */
    clearError: (state) => {
      state.error = null;
    },

    /**
     * Resetear estado completo (útil en logout)
     */
    resetGruposState: () => initialState,
  },

  extraReducers: (builder) => {
    // ========== cargarGrupos ==========
    builder
      .addCase(cargarGrupos.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(cargarGrupos.fulfilled, (state, action) => {
        state.loading = false;
        state.grupos = action.payload;
      })
      .addCase(cargarGrupos.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // ========== cargarArbolGrupos ==========
    builder
      .addCase(cargarArbolGrupos.pending, (state) => {
        state.loadingTree = true;
        state.error = null;
      })
      .addCase(cargarArbolGrupos.fulfilled, (state, action) => {
        state.loadingTree = false;
        state.gruposTree = action.payload;
      })
      .addCase(cargarArbolGrupos.rejected, (state, action) => {
        state.loadingTree = false;
        state.error = action.payload as string;
      });

    // ========== cargarGrupoActual ==========
    builder
      .addCase(cargarGrupoActual.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(cargarGrupoActual.fulfilled, (state, action) => {
        state.loading = false;
        state.grupoActual = action.payload;
        // Persistir en localStorage
        localStorage.setItem('grupo_id', action.payload.id.toString());
      })
      .addCase(cargarGrupoActual.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // ========== cargarEstadisticas ==========
    builder
      .addCase(cargarEstadisticas.pending, (state) => {
        state.loadingStats = true;
        state.error = null;
      })
      .addCase(cargarEstadisticas.fulfilled, (state, action) => {
        state.loadingStats = false;
        state.estadisticas = action.payload;
      })
      .addCase(cargarEstadisticas.rejected, (state, action) => {
        state.loadingStats = false;
        state.error = action.payload as string;
      });

    // ========== cargarMisGrupos ==========
    builder
      .addCase(cargarMisGrupos.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(cargarMisGrupos.fulfilled, (state, action) => {
        state.loading = false;
        state.grupos = action.payload;
      })
      .addCase(cargarMisGrupos.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

// Exportar acciones
export const { setGrupoActual, clearError, resetGruposState } = gruposSlice.actions;

// Exportar reducer
export default gruposSlice.reducer;
