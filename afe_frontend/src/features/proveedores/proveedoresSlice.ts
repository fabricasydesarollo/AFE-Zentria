/**
 * Redux Slice para gestión de Proveedores y Asignaciones NIT
 * Implementa patrón de estado normalizado y manejo de loading/error states
 *
 * @version 2.0 - Migrado a asignacion-nit
 * @date 2025-10-19
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../../app/store';
import {
  getProveedores,
  getProveedor,
  createProveedor,
  updateProveedor,
  deleteProveedor,
  type Proveedor,
  type ProveedorCreate,
  type ProveedorUpdate,
} from '../../services/proveedores.api';
import {
  getAsignacionesNit,
  createAsignacionNit,
  updateAsignacionNit,
  deleteAsignacionNit,
  type AsignacionNit,
  type AsignacionNitCreate,
  type AsignacionNitUpdate,
} from '../../services/asignacionNit.api';

// ==================== TYPES ====================

interface ProveedoresState {
  // Proveedores
  proveedores: Proveedor[];
  selectedProveedor: Proveedor | null;
  proveedoresLoading: boolean;
  proveedoresError: string | null;

  // Asignaciones NIT (nuevo sistema)
  asignaciones: AsignacionNit[];
  selectedAsignacion: AsignacionNit | null;
  asignacionesLoading: boolean;
  asignacionesError: string | null;

  // UI State
  lastSync: string | null;
}

const initialState: ProveedoresState = {
  proveedores: [],
  selectedProveedor: null,
  proveedoresLoading: false,
  proveedoresError: null,

  asignaciones: [],
  selectedAsignacion: null,
  asignacionesLoading: false,
  asignacionesError: null,

  lastSync: null,
};

// ==================== ASYNC THUNKS - PROVEEDORES ====================

export const fetchProveedores = createAsyncThunk(
  'proveedores/fetchProveedores',
  async (params: { skip?: number; limit?: number } | undefined, { rejectWithValue }) => {
    try {
      const data = await getProveedores(params);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar proveedores');
    }
  }
);

export const fetchProveedorById = createAsyncThunk(
  'proveedores/fetchProveedorById',
  async (id: number, { rejectWithValue }) => {
    try {
      const data = await getProveedor(id);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar proveedor');
    }
  }
);

export const createProveedorThunk = createAsyncThunk(
  'proveedores/createProveedor',
  async (payload: ProveedorCreate, { rejectWithValue }) => {
    try {
      const data = await createProveedor(payload);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al crear proveedor');
    }
  }
);

export const updateProveedorThunk = createAsyncThunk(
  'proveedores/updateProveedor',
  async ({ id, data }: { id: number; data: ProveedorUpdate }, { rejectWithValue }) => {
    try {
      const updatedData = await updateProveedor(id, data);
      return updatedData;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al actualizar proveedor');
    }
  }
);

export const deleteProveedorThunk = createAsyncThunk(
  'proveedores/deleteProveedor',
  async (id: number, { rejectWithValue }) => {
    try {
      await deleteProveedor(id);
      return id;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al eliminar proveedor');
    }
  }
);

// ==================== ASYNC THUNKS - ASIGNACIONES NIT ====================

export const fetchAsignaciones = createAsyncThunk(
  'proveedores/fetchAsignaciones',
  async (
    params: {
      skip?: number;
      limit?: number;
      responsable_id?: number;
      nit?: string;
      activo?: boolean;
    } | undefined,
    { rejectWithValue }
  ) => {
    try {
      const data = await getAsignacionesNit(params);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al cargar asignaciones');
    }
  }
);

export const createAsignacionThunk = createAsyncThunk(
  'proveedores/createAsignacion',
  async (payload: AsignacionNitCreate, { rejectWithValue }) => {
    try {
      const data = await createAsignacionNit(payload);
      return data;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al crear asignación');
    }
  }
);

export const updateAsignacionThunk = createAsyncThunk(
  'proveedores/updateAsignacion',
  async ({ id, data }: { id: number; data: AsignacionNitUpdate }, { rejectWithValue }) => {
    try {
      const updatedData = await updateAsignacionNit(id, data);
      return updatedData;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al actualizar asignación');
    }
  }
);

export const deleteAsignacionThunk = createAsyncThunk(
  'proveedores/deleteAsignacion',
  async (id: number, { rejectWithValue }) => {
    try {
      await deleteAsignacionNit(id);
      return id;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Error al eliminar asignación');
    }
  }
);

// ==================== SLICE ====================

const proveedoresSlice = createSlice({
  name: 'proveedores',
  initialState,
  reducers: {
    // Limpiar errores
    clearProveedoresError: (state) => {
      state.proveedoresError = null;
    },
    clearAsignacionesError: (state) => {
      state.asignacionesError = null;
    },

    // Seleccionar proveedor
    selectProveedor: (state, action: PayloadAction<Proveedor | null>) => {
      state.selectedProveedor = action.payload;
    },

    // Seleccionar asignación
    selectAsignacion: (state, action: PayloadAction<AsignacionNit | null>) => {
      state.selectedAsignacion = action.payload;
    },

    // Actualizar último sync
    updateLastSync: (state) => {
      state.lastSync = new Date().toISOString();
    },

    // Reset state
    resetProveedoresState: () => initialState,
  },
  extraReducers: (builder) => {
    // ========== FETCH PROVEEDORES ==========
    builder
      .addCase(fetchProveedores.pending, (state) => {
        state.proveedoresLoading = true;
        state.proveedoresError = null;
      })
      .addCase(fetchProveedores.fulfilled, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedores = action.payload;
        state.lastSync = new Date().toISOString();
      })
      .addCase(fetchProveedores.rejected, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedoresError = action.payload as string;
      });

    // ========== FETCH PROVEEDOR BY ID ==========
    builder
      .addCase(fetchProveedorById.pending, (state) => {
        state.proveedoresLoading = true;
        state.proveedoresError = null;
      })
      .addCase(fetchProveedorById.fulfilled, (state, action) => {
        state.proveedoresLoading = false;
        state.selectedProveedor = action.payload;
      })
      .addCase(fetchProveedorById.rejected, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedoresError = action.payload as string;
      });

    // ========== CREATE PROVEEDOR ==========
    builder
      .addCase(createProveedorThunk.pending, (state) => {
        state.proveedoresLoading = true;
        state.proveedoresError = null;
      })
      .addCase(createProveedorThunk.fulfilled, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedores.push(action.payload);
        state.lastSync = new Date().toISOString();
      })
      .addCase(createProveedorThunk.rejected, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedoresError = action.payload as string;
      });

    // ========== UPDATE PROVEEDOR ==========
    builder
      .addCase(updateProveedorThunk.pending, (state) => {
        state.proveedoresLoading = true;
        state.proveedoresError = null;
      })
      .addCase(updateProveedorThunk.fulfilled, (state, action) => {
        state.proveedoresLoading = false;
        const index = state.proveedores.findIndex((p) => p.id === action.payload.id);
        if (index !== -1) {
          state.proveedores[index] = action.payload;
        }
        if (state.selectedProveedor?.id === action.payload.id) {
          state.selectedProveedor = action.payload;
        }
        state.lastSync = new Date().toISOString();
      })
      .addCase(updateProveedorThunk.rejected, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedoresError = action.payload as string;
      });

    // ========== DELETE PROVEEDOR ==========
    builder
      .addCase(deleteProveedorThunk.pending, (state) => {
        state.proveedoresLoading = true;
        state.proveedoresError = null;
      })
      .addCase(deleteProveedorThunk.fulfilled, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedores = state.proveedores.filter((p) => p.id !== action.payload);
        if (state.selectedProveedor?.id === action.payload) {
          state.selectedProveedor = null;
        }
        state.lastSync = new Date().toISOString();
      })
      .addCase(deleteProveedorThunk.rejected, (state, action) => {
        state.proveedoresLoading = false;
        state.proveedoresError = action.payload as string;
      });

    // ========== FETCH ASIGNACIONES ==========
    builder
      .addCase(fetchAsignaciones.pending, (state) => {
        state.asignacionesLoading = true;
        state.asignacionesError = null;
      })
      .addCase(fetchAsignaciones.fulfilled, (state, action) => {
        state.asignacionesLoading = false;
        // Filtro adicional de seguridad: solo mostrar asignaciones activas
        state.asignaciones = action.payload.filter((a) => a.activo !== false);
        state.lastSync = new Date().toISOString();
      })
      .addCase(fetchAsignaciones.rejected, (state, action) => {
        state.asignacionesLoading = false;
        state.asignacionesError = action.payload as string;
      });

    // ========== CREATE ASIGNACION ==========
    builder
      .addCase(createAsignacionThunk.pending, (state) => {
        state.asignacionesLoading = true;
        state.asignacionesError = null;
      })
      .addCase(createAsignacionThunk.fulfilled, (state) => {
        state.asignacionesLoading = false;
        state.lastSync = new Date().toISOString();
      })
      .addCase(createAsignacionThunk.rejected, (state, action) => {
        state.asignacionesLoading = false;
        state.asignacionesError = action.payload as string;
      });

    // ========== UPDATE ASIGNACION ==========
    builder
      .addCase(updateAsignacionThunk.pending, (state) => {
        state.asignacionesLoading = true;
        state.asignacionesError = null;
      })
      .addCase(updateAsignacionThunk.fulfilled, (state) => {
        state.asignacionesLoading = false;
        state.lastSync = new Date().toISOString();
      })
      .addCase(updateAsignacionThunk.rejected, (state, action) => {
        state.asignacionesLoading = false;
        state.asignacionesError = action.payload as string;
      });

    // ========== DELETE ASIGNACION ==========
    builder
      .addCase(deleteAsignacionThunk.pending, (state) => {
        state.asignacionesLoading = true;
        state.asignacionesError = null;
      })
      .addCase(deleteAsignacionThunk.fulfilled, (state, action) => {
        state.asignacionesLoading = false;
        state.asignaciones = state.asignaciones.filter((a) => a.id !== action.payload);
        if (state.selectedAsignacion?.id === action.payload) {
          state.selectedAsignacion = null;
        }
        state.lastSync = new Date().toISOString();
      })
      .addCase(deleteAsignacionThunk.rejected, (state, action) => {
        state.asignacionesLoading = false;
        state.asignacionesError = action.payload as string;
      });
  },
});

// ==================== EXPORTS ====================

export const {
  clearProveedoresError,
  clearAsignacionesError,
  selectProveedor,
  selectAsignacion,
  updateLastSync,
  resetProveedoresState,
} = proveedoresSlice.actions;

// Selectors
export const selectProveedoresState = (state: RootState) => state.proveedores;
export const selectProveedoresList = (state: RootState) => state.proveedores.proveedores;
export const selectProveedoresLoading = (state: RootState) => state.proveedores.proveedoresLoading;
export const selectProveedoresError = (state: RootState) => state.proveedores.proveedoresError;
export const selectSelectedProveedor = (state: RootState) => state.proveedores.selectedProveedor;

export const selectAsignacionesList = (state: RootState) => state.proveedores.asignaciones;
export const selectAsignacionesLoading = (state: RootState) => state.proveedores.asignacionesLoading;
export const selectAsignacionesError = (state: RootState) => state.proveedores.asignacionesError;
export const selectSelectedAsignacion = (state: RootState) => state.proveedores.selectedAsignacion;

export const selectLastSync = (state: RootState) => state.proveedores.lastSync;

export default proveedoresSlice.reducer;
