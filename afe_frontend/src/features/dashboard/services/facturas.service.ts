/**
 * Facturas API service
 * Handles all API calls related to facturas
 */

import apiClient from '../../../services/api';
import type { Factura, FacturaFormData } from '../types';

interface FacturasResponse {
  data: Factura[];
  pagination?: {
    total: number;
    page: number;
    per_page: number;
  };
}

interface FetchFacturasParams {
  page?: number;
  per_page?: number;
  solo_asignadas?: boolean;
  mes_actual_only?: boolean;
}

export const facturasService = {
  /**
   * Fetch all facturas with optional filters
   */
  async fetchFacturas(params: FetchFacturasParams = {}): Promise<FacturasResponse> {
    const response = await apiClient.get<FacturasResponse>('/facturas/', { params });
    return response.data;
  },

  /**
   * Create a new factura
   */
  async createFactura(data: FacturaFormData): Promise<Factura> {
    const payload = {
      ...data,
      monto_total: parseFloat(data.monto_total),
      estado: 'pendiente',
    };
    const response = await apiClient.post<Factura>('/facturas/', payload);
    return response.data;
  },

  /**
   * Update an existing factura
   */
  async updateFactura(id: number, data: FacturaFormData): Promise<Factura> {
    const payload = {
      ...data,
      monto_total: parseFloat(data.monto_total),
      estado: 'pendiente',
    };
    const response = await apiClient.put<Factura>(`/facturas/${id}`, payload);
    return response.data;
  },

  /**
   * Delete a factura
   */
  async deleteFactura(id: number): Promise<void> {
    await apiClient.delete(`/facturas/${id}`);
  },

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

  /**
   * Get export URL for CSV
   */
  getExportUrl(estado?: string, soloAsignadas?: boolean): string {
    const params = new URLSearchParams();

    if (estado && estado !== 'todos') {
      params.append('estado', estado);
    }

    if (soloAsignadas) {
      params.append('solo_asignadas', 'true');
    }

    const queryString = params.toString();
    return `/facturas/export/csv${queryString ? '?' + queryString : ''}`;
  },
};
