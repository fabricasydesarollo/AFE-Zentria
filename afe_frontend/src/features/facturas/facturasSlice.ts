import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { FacturaPendiente, DashboardMetrics, FacturaConWorkflow, ContextoHistorico } from '../../types/factura.types';
import apiClient from '../../services/api';

/**
 * Facturas Slice
 */

interface FacturasState {
  pendientes: FacturaPendiente[];
  selectedFactura: FacturaConWorkflow | null;
  contextoHistorico: ContextoHistorico | null;
  dashboard: DashboardMetrics | null;
  loading: boolean;
  error: string | null;
}

const initialState: FacturasState = {
  pendientes: [],
  selectedFactura: null,
  contextoHistorico: null,
  dashboard: null,
  loading: false,
  error: null,
};

// Async thunks
export const fetchFacturasPendientes = createAsyncThunk(
  'facturas/fetchPendientes',
  async (responsableId: number) => {
    // Usar el endpoint de facturas para obtener todas las facturas en revisión
    const response = await apiClient.get(`/facturas/`, {
      params: {
        page: 1,
        per_page: 500,
        solo_asignadas: true, // Solo las asignadas al responsable actual
        mes_actual_only: true, // Solo facturas del mes actual
      }
    });

    // Filtrar facturas que requieren revisión (pendientes + en_revision + devueltas)
    const facturas = response.data.data || [];
    const facturasEnRevision = facturas.filter((f: any) =>
      f.estado === 'pendiente' ||
      f.estado === 'en_revision' ||
      f.estado === 'devuelta_contabilidad' // Facturas devueltas por contador
    );

    // Transformar al formato que espera el componente
    return facturasEnRevision.map((f: any) => ({
      workflow_id: f.id,
      factura_id: f.id,
      numero_factura: f.numero_factura,
      proveedor: f.nombre_emisor || 'Sin proveedor',
      nit: f.nit_emisor,
      monto: parseFloat(f.total_a_pagar || 0),
      estado: f.estado,
      porcentaje_similitud: null,
      es_identica_mes_anterior: false,
      fecha_asignacion: f.creado_en,
      creado_en: f.creado_en,
      nombre_responsable: f.nombre_responsable || null,
    }));
  }
);

export const fetchFacturaDetalle = createAsyncThunk(
  'facturas/fetchDetalle',
  async (facturaId: number) => {
    const response = await apiClient.get(`/workflow/factura-detalle/${facturaId}`);
    return response.data;
  }
);

export const fetchDashboard = createAsyncThunk(
  'facturas/fetchDashboard',
  async (responsableId: number) => {
    const response = await apiClient.get(`/workflow/dashboard?responsable_id=${responsableId}`);
    return response.data;
  }
);

// Thunks de aprobar/rechazar removidos - ahora se usa facturasService directamente

const facturasSlice = createSlice({
  name: 'facturas',
  initialState,
  reducers: {
    clearSelectedFactura: (state) => {
      state.selectedFactura = null;
      state.contextoHistorico = null;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch pendientes
      .addCase(fetchFacturasPendientes.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchFacturasPendientes.fulfilled, (state, action) => {
        state.loading = false;
        state.pendientes = action.payload;
      })
      .addCase(fetchFacturasPendientes.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Error al cargar facturas';
      })
      // Fetch detalle
      .addCase(fetchFacturaDetalle.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchFacturaDetalle.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedFactura = action.payload;
        state.contextoHistorico = action.payload.contexto_historico || null;
      })
      .addCase(fetchFacturaDetalle.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Error al cargar detalle';
      })
      // Fetch dashboard
      .addCase(fetchDashboard.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.loading = false;
        state.dashboard = action.payload;
      })
      .addCase(fetchDashboard.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Error al cargar dashboard';
      });
  },
});

export const { clearSelectedFactura, clearError } = facturasSlice.actions;
export default facturasSlice.reducer;
