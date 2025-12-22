/**
 * Payment Service - API calls para el sistema de pagos
 *
 * Proporciona funciones para:
 * - Registrar pagos de facturas
 * - Obtener historial de pagos
 * - Obtener facturas pendientes de pago
 * - Validar referencias de pago (evitar duplicados)
 */

import axios, { AxiosError } from 'axios';
import apiClient from './api';
import {
  Pago,
  PagoRequest,
  PagoResponse,
  FacturaConPagos,
  FacturasPendientesResponse,
  PagosPaginados
} from '../types/payment.types';

class PaymentService {
  /**
   * Registrar un nuevo pago para una factura
   *
   * @param facturaId - ID de la factura
   * @param datos - PagoRequest con monto_pagado, referencia_pago, metodo_pago
   * @returns FacturaConPagos con información actualizada de pagos
   * @throws Error si hay validación fallida, referencia duplicada, etc.
   */
  async registrarPago(
    facturaId: number,
    datos: PagoRequest
  ): Promise<FacturaConPagos> {
    try {
      const response = await apiClient.post<FacturaConPagos>(
        `/accounting/facturas/${facturaId}/marcar-pagada`,
        {
          monto_pagado: datos.monto_pagado.toString(),
          referencia_pago: datos.referencia_pago.toUpperCase().trim(),
          metodo_pago: datos.metodo_pago || 'otro'
        }
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Obtener factura actual con información de pagos
   *
   * @param facturaId - ID de la factura
   * @returns FacturaConPagos con historial completo de pagos
   */
  async obtenerFacturaConPagos(facturaId: number): Promise<FacturaConPagos> {
    try {
      const response = await apiClient.get<FacturaConPagos>(
        `/facturas/${facturaId}`
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Obtener lista de facturas pendientes de pago
   *
   * @param page - Número de página (default: 1)
   * @param perPage - Items por página (default: 20)
   * @returns Lista de facturas pendientes con paginación
   */
  async obtenerFacturasPendientes(
    page: number = 1,
    perPage: number = 20
  ): Promise<FacturasPendientesResponse> {
    try {
      const response = await apiClient.get<FacturasPendientesResponse>(
        `/accounting/facturas/pendientes`,
        {
          params: {
            page,
            per_page: perPage
          }
        }
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Obtener historial completo de pagos registrados
   *
   * @returns Lista de todos los pagos con detalles completos
   */
  async obtenerHistorialPagosCompleto(): Promise<any> {
    try {
      const response = await apiClient.get(
        `/accounting/historial-pagos`
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Obtener historial de pagos para una factura
   *
   * @param facturaId - ID de la factura
   * @returns Array de pagos ordenados por fecha
   */
  async obtenerHistorialPagos(facturaId: number): Promise<Pago[]> {
    try {
      const factura = await this.obtenerFacturaConPagos(facturaId);
      // Los pagos vienen en el objeto factura, ordenados por fecha_pago
      return factura.pagos.sort((a, b) =>
        new Date(b.fecha_pago).getTime() - new Date(a.fecha_pago).getTime()
      );
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Validar si una referencia de pago ya existe
   *
   * @param referencia - Referencia de pago a validar
   * @returns true si la referencia es única, false si ya existe
   */
  async validarReferenciaunica(referencia: string): Promise<boolean> {
    try {
      // Obtener todas las facturas pendientes y revisarlas
      // En una implementación real, habría un endpoint específico para esto
      const response = await apiClient.get(
        `/accounting/facturas/pendientes?per_page=1000`
      );

      const facturas = response.data.facturas || [];

      for (const factura of facturas) {
        if (factura.pagos && factura.pagos.length > 0) {
          const existeReferencia = factura.pagos.some(
            (pago: Pago) => pago.referencia_pago.toUpperCase() === referencia.toUpperCase()
          );
          if (existeReferencia) {
            return false; // Referencia ya existe
          }
        }
      }

      return true; // Referencia es única
    } catch (error) {
      // Si hay error al validar, permitir proceder (el backend lo validará)
      console.warn('Error validando referencia:', error);
      return true;
    }
  }

  /**
   * Obtener estadísticas de pagos
   *
   * @returns Estadísticas generales de pagos
   */
  async obtenerEstadisticasPagos() {
    try {
      const response = await apiClient.get(
        `/accounting/estadisticas-pagos`
      );

      return response.data;
    } catch (error) {
      // Si el endpoint no existe, retornar datos vacíos
      console.warn('Estadísticas de pagos no disponibles:', error);
      return {
        total_facturas: 0,
        facturas_pagadas: 0,
        facturas_por_pagar: 0,
        total_monto: '0.00',
        total_pagado: '0.00',
        total_pendiente: '0.00'
      };
    }
  }

  /**
   * Manejo centralizado de errores de la API
   *
   * @param error - Error de axios
   * @returns Objeto Error con mensaje legible
   */
  private handleError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;

      if (axiosError.response) {
        // Error response del backend
        const status = axiosError.response.status;
        const data = axiosError.response.data as { detail?: string };

        switch (status) {
          case 400:
            return new Error(
              data?.detail || 'Validación fallida. Verifique los datos ingresados'
            );
          case 403:
            return new Error('No tiene permisos para registrar pagos. Solo usuarios con rol contador pueden hacerlo');
          case 404:
            return new Error('Factura no encontrada');
          case 409:
            return new Error(
              data?.detail || 'La referencia de pago ya existe. Ingrese una referencia única'
            );
          case 500:
            return new Error('Error del servidor. Intente más tarde');
          default:
            return new Error(data?.detail || 'Error al procesar la solicitud');
        }
      } else if (axiosError.request) {
        // Request hecho pero sin response
        return new Error('No hay respuesta del servidor. Verifique su conexión');
      }
    }

    // Error desconocido
    return new Error(
      error instanceof Error ? error.message : 'Error desconocido'
    );
  }
}

// Exportar instancia única del servicio
export const paymentService = new PaymentService();

export default paymentService;
