/**
 * Facturas API service para Por Revisar
 * Handles all API calls related to facturas
 */

import apiClient from '../../../services/api';

// ============================================================================
// INTERFACES Y TIPOS
// ============================================================================

export interface DevolucionRequest {
  observaciones: string;
  notificar_proveedor: boolean;
  notificar_responsable: boolean;
}

export interface DevolucionResponse {
  success: boolean;
  factura_id: number;
  numero_factura: string;
  estado_anterior: string;
  estado_nuevo: string;
  notificaciones_enviadas: number;
  destinatarios: string[];
  mensaje: string;
  timestamp: string;
}

export interface FacturaPendiente {
  id: number;
  numero_factura: string;
  proveedor: string | null;
  monto: string; // String para precisión en cálculos monetarios
  fecha_emision: string | null;
  estado: string;
  total_pagado: number; // Cantidad ya pagada
  pendiente_pagar: number; // Cantidad aún pendiente
  esta_completamente_pagada: boolean; // true si ya fue pagada completamente
}

export interface FacturasPendientesResponse {
  total: number;
  facturas: FacturaPendiente[];
}

// ============================================================================
// SERVICE
// ============================================================================

export const facturasService = {
  /**
   * Approve a factura
   */
  async approveFactura(id: number, aprobadoPor: string, observaciones?: string): Promise<void> {
    await apiClient.post(`/facturas/${id}/aprobar`, {
      aprobado_por: aprobadoPor,
      observaciones: observaciones || undefined,
    });
  },

  /**
   * Reject a factura
   */
  async rejectFactura(id: number, rechazadoPor: string, motivo: string, detalle?: string): Promise<void> {
    await apiClient.post(`/facturas/${id}/rechazar`, {
      rechazado_por: rechazadoPor,
      motivo,
      detalle: detalle || undefined,
    });
  },

  // ============================================================================
  // NUEVOS MÉTODOS - CONTADOR (2025-11-18)
  // ============================================================================

  /**
   * Abre el PDF de una factura en una nueva ventana con autenticación
   * CORREGIDO 2025-11-18: Ahora incluye el token de autenticación Bearer
   *
   * @param id - ID de la factura
   * @param download - Si es true, fuerza descarga. Si es false (default), abre inline en navegador
   */
  async openPdfInNewTab(id: number, download: boolean = false): Promise<void> {
    try {
      const downloadParam = download ? '?download=true' : '';

      // Usar apiClient que ya tiene el token Bearer configurado automáticamente
      const response = await apiClient.get(`/facturas/${id}/pdf${downloadParam}`, {
        responseType: 'blob',
      });

      // Verificar que recibimos un PDF válido
      if (!response.data || response.data.size === 0) {
        throw new Error('Documento vacío\n\nEl archivo PDF está vacío o corrupto. Por favor, contacta al administrador para verificar el estado del documento.');
      }

      // Crear URL del blob y abrirlo en nueva pestaña
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);

      // Abrir en nueva ventana
      const newWindow = window.open(url, '_blank');

      if (!newWindow) {
        throw new Error('Ventana bloqueada\n\nTu navegador está bloqueando ventanas emergentes. Por favor, permite las ventanas emergentes para este sitio en la configuración de tu navegador.');
      }

      // Limpiar URL después de que se haya cargado
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    } catch (error: any) {
      console.error('Error abriendo PDF:', error);

      // Proporcionar mensaje de error más específico
      if (error.response?.status === 404) {
        throw new Error('Documento no disponible\n\nEl archivo PDF solicitado no se encuentra en el sistema. Esto puede ocurrir si la factura fue registrada sin adjuntar el documento original.');
      } else if (error.response?.status === 401 || error.response?.status === 403) {
        throw new Error('Acceso denegado\n\nNo cuentas con los permisos necesarios para visualizar este documento. Por favor, verifica tu sesión o contacta al administrador del sistema.');
      } else {
        throw new Error(error.message || 'Error al procesar la solicitud\n\nNo fue posible cargar el documento PDF. Por favor, verifica tu conexión e intenta nuevamente.');
      }
    }
  },

  /**
   * @deprecated Use openPdfInNewTab() instead. This method doesn't include authentication.
   */
  getPdfUrl(id: number, download: boolean = false): string {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const downloadParam = download ? '?download=true' : '';
    return `${baseUrl}/api/v1/facturas/${id}/pdf${downloadParam}`;
  },

  /**
   * Devuelve una factura aprobada al proveedor solicitando información adicional
   * Solo disponible para rol 'contador'
   *
   * @param id - ID de la factura a devolver
   * @param request - Datos de la devolución (observaciones, flags de notificación)
   * @returns Respuesta con resultado de la devolución
   */
  async devolverFactura(id: number, request: DevolucionRequest): Promise<DevolucionResponse> {
    const response = await apiClient.post<DevolucionResponse>(
      `/accounting/facturas/${id}/devolver`,
      request
    );
    return response.data;
  },

  /**
   * Obtiene todas las facturas aprobadas pendientes de procesar por contabilidad
   * Solo disponible para rol 'contador'
   *
   * @returns Lista de facturas pendientes
   */
  async getFacturasPendientes(): Promise<FacturasPendientesResponse> {
    const response = await apiClient.get<FacturasPendientesResponse>(
      '/accounting/facturas/pendientes'
    );
    return response.data;
  },

  /**
   * Obtiene información de documentos (PDF/XML) de una factura sin descargarlos
   * Útil para mostrar en UI si hay PDF disponible y su tamaño
   *
   * @param id - ID de la factura
   * @returns Metadata de los documentos
   */
  async getDocumentosInfo(id: number): Promise<any> {
    const response = await apiClient.get(`/facturas/${id}/documentos/info`);
    return response.data;
  },
};
