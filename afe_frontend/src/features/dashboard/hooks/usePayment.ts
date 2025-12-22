/**
 * Custom Hook: usePayment
 *
 * Proporciona funcionalidad para:
 * - Registrar pagos
 * - Obtener historial de pagos
 * - Validar datos de pago
 * - Manejo de estado local y errores
 */

import { useState, useCallback } from 'react';
import {
  FacturaConPagos,
  PagoRequest,
  ValidacionPago,
  Pago
} from '../../../types/payment.types';
import paymentService from '../../../services/paymentService';

interface UsePaymentReturn {
  // Estado
  isLoading: boolean;
  error: string | null;
  factura: FacturaConPagos | null;
  historialPagos: Pago[];

  // Funciones
  registrarPago: (facturaId: number, datos: PagoRequest) => Promise<FacturaConPagos>;
  obtenerFactura: (facturaId: number) => Promise<FacturaConPagos>;
  obtenerHistorial: (facturaId: number) => Promise<Pago[]>;
  validarPago: (datos: PagoRequest, facturaId: number, pendiente: string) => ValidacionPago;
  validarReferencia: (referencia: string) => Promise<boolean>;
  limpiarError: () => void;
}

/**
 * Hook para manejo de pagos
 */
export const usePayment = (): UsePaymentReturn => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [factura, setFactura] = useState<FacturaConPagos | null>(null);
  const [historialPagos, setHistorialPagos] = useState<Pago[]>([]);

  /**
   * Registrar un nuevo pago
   */
  const registrarPago = useCallback(
    async (facturaId: number, datos: PagoRequest): Promise<FacturaConPagos> => {
      setIsLoading(true);
      setError(null);

      try {
        const resultado = await paymentService.registrarPago(facturaId, datos);
        setFactura(resultado);
        setHistorialPagos(resultado.pagos);
        return resultado;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Error al registrar pago';
        setError(errorMsg);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Obtener información actualizada de la factura
   */
  const obtenerFactura = useCallback(
    async (facturaId: number): Promise<FacturaConPagos> => {
      setIsLoading(true);
      setError(null);

      try {
        const resultado = await paymentService.obtenerFacturaConPagos(facturaId);
        setFactura(resultado);
        setHistorialPagos(resultado.pagos);
        return resultado;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Error al obtener factura';
        setError(errorMsg);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Obtener historial de pagos
   */
  const obtenerHistorial = useCallback(
    async (facturaId: number): Promise<Pago[]> => {
      setIsLoading(true);
      setError(null);

      try {
        const resultado = await paymentService.obtenerHistorialPagos(facturaId);
        setHistorialPagos(resultado);
        return resultado;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Error al obtener historial';
        setError(errorMsg);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Validar datos de pago antes de enviar
   */
  const validarPago = useCallback(
    (datos: PagoRequest, facturaId: number, pendiente: string): ValidacionPago => {
      const errors: ValidacionPago['errors'] = {};

      // Validar monto
      const monto = typeof datos.monto_pagado === 'string'
        ? parseFloat(datos.monto_pagado)
        : datos.monto_pagado;

      if (!monto || monto <= 0) {
        errors.monto_pagado = 'El monto debe ser mayor a 0';
      }

      const pendienteNum = parseFloat(pendiente);
      if (monto > pendienteNum) {
        errors.monto_pagado = `El monto no puede exceder el pendiente de $${pendiente}`;
      }

      // Validar referencia
      const referencia = datos.referencia_pago?.trim() || '';
      if (referencia.length < 3) {
        errors.referencia_pago = 'La referencia debe tener al menos 3 caracteres';
      }
      if (referencia.length > 100) {
        errors.referencia_pago = 'La referencia no puede exceder 100 caracteres';
      }
      if (!referencia.match(/^[A-Z0-9\-_]+$/i)) {
        errors.referencia_pago = 'La referencia solo puede contener letras, números, guiones y guiones bajos';
      }

      return {
        isValid: Object.keys(errors).length === 0,
        errors
      };
    },
    []
  );

  /**
   * Validar si referencia es única
   */
  const validarReferencia = useCallback(
    async (referencia: string): Promise<boolean> => {
      try {
        return await paymentService.validarReferenciaunica(referencia);
      } catch (err) {
        console.warn('Error validando referencia:', err);
        return true; // Permitir proceder si hay error en validación
      }
    },
    []
  );

  /**
   * Limpiar error
   */
  const limpiarError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isLoading,
    error,
    factura,
    historialPagos,
    registrarPago,
    obtenerFactura,
    obtenerHistorial,
    validarPago,
    validarReferencia,
    limpiarError
  };
};

export default usePayment;
