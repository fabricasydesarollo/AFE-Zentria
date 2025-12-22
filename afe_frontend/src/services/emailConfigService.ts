/**
 * Email Configuration Service
 * Servicio para gestión de configuración de extracción de correos corporativos
 */

import apiClient from './api';

// ==================== TIPOS ====================

export interface CuentaCorreoSummary {
  id: number;
  email: string;
  nombre_descriptivo: string | null;
  activa: boolean;
  organizacion: string | null;
  total_nits: number;
  total_nits_activos: number;
  creada_en: string;
}

export interface NitConfiguracion {
  id: number;
  cuenta_correo_id: number;
  nit: string;
  nombre_proveedor: string | null;
  activo: boolean;
  notas: string | null;
  creado_en: string;
  actualizado_en: string;
  creado_por: string;
  actualizado_por: string | null;
}

export interface CuentaCorreoDetalle {
  id: number;
  email: string;
  nombre_descriptivo: string | null;
  fetch_limit: number;
  fetch_days: number;
  max_correos_por_ejecucion: number;
  ventana_inicial_dias: number;
  activa: boolean;
  organizacion: string | null;
  creada_en: string;
  actualizada_en: string;
  creada_por: string;
  actualizada_por: string | null;
  nits: NitConfiguracion[];
}

export interface HistorialExtraccion {
  id: number;
  cuenta_correo_id: number;
  fecha_ejecucion: string;
  correos_procesados: number;
  facturas_encontradas: number;
  facturas_creadas: number;
  facturas_actualizadas: number;
  facturas_ignoradas: number;
  exito: boolean;
  mensaje_error: string | null;
  tiempo_ejecucion_ms: number | null;
  fetch_limit_usado: number | null;
  fetch_days_usado: number | null;
  nits_usados: number | null;
}

export interface EstadisticasExtraccion {
  cuenta_correo_id: number;
  email: string;
  total_ejecuciones: number;
  ultima_ejecucion: string | null;
  total_facturas_encontradas: number;
  total_facturas_creadas: number;
  tasa_exito: number;
  promedio_tiempo_ms: number | null;
}

export interface CreateCuentaCorreo {
  email: string;
  nombre_descriptivo?: string;
  fetch_limit?: number;
  fetch_days?: number;
  activa?: boolean;
  organizacion?: string;
  grupo_id?: number;
  nits?: string[];
}

export interface UpdateCuentaCorreo {
  nombre_descriptivo?: string;
  fetch_limit?: number;
  fetch_days?: number;
  max_correos_por_ejecucion?: number;
  ventana_inicial_dias?: number;
  activa?: boolean;
  organizacion?: string;
  actualizada_por?: string;
}

export interface CreateNit {
  cuenta_correo_id: number;
  nit: string;
  nombre_proveedor?: string;
  activo?: boolean;
  notas?: string;
}

export interface BulkCreateNits {
  cuenta_correo_id: number;
  nits: string[];
}

export interface BulkNitsResponse {
  cuenta_correo_id: number;
  nits_agregados: number;
  nits_duplicados: number;
  nits_fallidos: number;
  detalles: Array<{
    nit: string;
    status: 'agregado' | 'duplicado' | 'error';
    id?: number;
    mensaje?: string;
  }>;
}

// ==================== SERVICIOS ====================

const BASE_PATH = '/email-config';

/**
 * CUENTAS DE CORREO
 */

export const emailConfigService = {
  // Listar cuentas
  listarCuentas: async (params?: {
    skip?: number;
    limit?: number;
    solo_activas?: boolean;
    organizacion?: string;
  }): Promise<CuentaCorreoSummary[]> => {
    const response = await apiClient.get(`${BASE_PATH}/cuentas`, { params });
    return response.data;
  },

  // Obtener detalle de cuenta
  obtenerCuenta: async (cuentaId: number): Promise<CuentaCorreoDetalle> => {
    const response = await apiClient.get(`${BASE_PATH}/cuentas/${cuentaId}`);
    return response.data;
  },

  // Crear cuenta
  crearCuenta: async (data: CreateCuentaCorreo): Promise<CuentaCorreoDetalle> => {
    const response = await apiClient.post(`${BASE_PATH}/cuentas`, data);
    return response.data;
  },

  // Actualizar cuenta
  actualizarCuenta: async (
    cuentaId: number,
    data: UpdateCuentaCorreo
  ): Promise<CuentaCorreoDetalle> => {
    const response = await apiClient.put(`${BASE_PATH}/cuentas/${cuentaId}`, data);
    return response.data;
  },

  // Eliminar cuenta
  eliminarCuenta: async (cuentaId: number): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/cuentas/${cuentaId}`);
  },

  // Toggle activa/inactiva
  toggleCuentaActiva: async (cuentaId: number, activa: boolean): Promise<CuentaCorreoDetalle> => {
    const response = await apiClient.post(
      `${BASE_PATH}/cuentas/${cuentaId}/toggle-activa`,
      null,
      { params: { activa } }
    );
    return response.data;
  },

  /**
   * NITS
   */

  // Listar NITs de una cuenta
  listarNits: async (
    cuentaId: number,
    solo_activos: boolean = false
  ): Promise<NitConfiguracion[]> => {
    const response = await apiClient.get(`${BASE_PATH}/nits/cuenta/${cuentaId}`, {
      params: { solo_activos },
    });
    return response.data;
  },

  // Crear NIT individual
  crearNit: async (data: CreateNit): Promise<NitConfiguracion> => {
    const response = await apiClient.post(`${BASE_PATH}/nits`, data);
    return response.data;
  },

  // Crear múltiples NITs (bulk)
  crearNitsBulk: async (data: BulkCreateNits): Promise<BulkNitsResponse> => {
    const response = await apiClient.post(`${BASE_PATH}/nits/bulk`, data);
    return response.data;
  },

  // Actualizar NIT
  actualizarNit: async (
    nitId: number,
    data: {
      nombre_proveedor?: string;
      activo?: boolean;
      notas?: string;
    }
  ): Promise<NitConfiguracion> => {
    const response = await apiClient.put(`${BASE_PATH}/nits/${nitId}`, data);
    return response.data;
  },

  // Eliminar NIT
  eliminarNit: async (nitId: number): Promise<void> => {
    await apiClient.delete(`${BASE_PATH}/nits/${nitId}`);
  },

  // Toggle NIT activo/inactivo
  toggleNitActivo: async (nitId: number, activo: boolean): Promise<NitConfiguracion> => {
    const response = await apiClient.post(
      `${BASE_PATH}/nits/${nitId}/toggle-activo`,
      null,
      { params: { activo } }
    );
    return response.data;
  },

  /**
   * HISTORIAL Y ESTADÍSTICAS
   */

  // Obtener historial de extracciones
  obtenerHistorial: async (
    cuentaId: number,
    limit: number = 50
  ): Promise<HistorialExtraccion[]> => {
    const response = await apiClient.get(`${BASE_PATH}/historial/cuenta/${cuentaId}`, {
      params: { limit },
    });
    return response.data;
  },

  // Obtener estadísticas de una cuenta
  obtenerEstadisticas: async (
    cuentaId: number,
    dias: number = 30
  ): Promise<EstadisticasExtraccion> => {
    const response = await apiClient.get(`${BASE_PATH}/estadisticas/cuenta/${cuentaId}`, {
      params: { dias },
    });
    return response.data;
  },

  // Obtener configuración para extractor (JSON legacy)
  obtenerConfiguracionExtractor: async (): Promise<{
    users: Array<{
      email: string;
      nits: string[];
      fetch_limit: number;
      fetch_days: number;
    }>;
    total_cuentas: number;
    total_nits: number;
    generado_en: string;
  }> => {
    const response = await apiClient.get(`${BASE_PATH}/configuracion-extractor`);
    return response.data;
  },
};

export default emailConfigService;
