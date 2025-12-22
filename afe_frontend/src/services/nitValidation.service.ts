/**
 * NIT Validation Service
 * Maneja validación y normalización de NITs a través del backend
 *
 * Características:
 * - Valida NITs en cualquier formato (con o sin DV)
 * - Calcula automáticamente el dígito verificador (DV) DIAN
 * - Retorna NITs normalizados en formato XXXXXXXXX-D
 * - Proporciona mensajes de error descriptivos
 */

import apiClient from './api';

/**
 * Respuesta de validación de NIT desde el backend
 */
export interface NitValidationResponse {
  is_valid: boolean;
  nit_normalizado?: string;
  error?: string;
}

/**
 * Resultado de validación formateado para el frontend
 */
export interface ValidationResult {
  isValid: boolean;
  normalizedNit?: string;
  errorMessage?: string;
}

class NitValidationService {
  /**
   * Valida un NIT a través del endpoint backend
   *
   * @param nit - NIT a validar (con o sin DV)
   * @returns Promise con resultado de validación
   *
   * @example
   * const result = await nitService.validateNit('800185449');
   * if (result.isValid) {
   *   console.log(`NIT normalizado: ${result.normalizedNit}`); // 800185449-9
   * }
   */
  async validateNit(nit: string): Promise<ValidationResult> {
    try {
      // Validación básica en cliente antes de enviar al servidor
      if (!nit || typeof nit !== 'string') {
        return {
          isValid: false,
          errorMessage: 'El NIT debe ser una cadena de texto válida'
        };
      }

      const cleanedNit = nit.trim();
      if (cleanedNit.length < 5 || cleanedNit.length > 20) {
        return {
          isValid: false,
          errorMessage: 'El NIT debe tener entre 5 y 20 caracteres'
        };
      }

      // Llamar al endpoint backend para validación completa
      const response = await apiClient.post<NitValidationResponse>(
        '/email-config/validate-nit',
        { nit: cleanedNit }
      );

      const { is_valid, nit_normalizado, error } = response.data;

      return {
        isValid: is_valid,
        normalizedNit: nit_normalizado,
        errorMessage: error
      };
    } catch (error) {
      console.error('Error validando NIT:', error);
      return {
        isValid: false,
        errorMessage: 'Error al validar NIT. Intente nuevamente.'
      };
    }
  }

  /**
   * Valida múltiples NITs en paralelo
   *
   * @param nits - Array de NITs a validar
   * @returns Promise con array de resultados
   */
  async validateMultipleNits(nits: string[]): Promise<ValidationResult[]> {
    try {
      const validationPromises = nits.map(nit => this.validateNit(nit));
      return await Promise.all(validationPromises);
    } catch (error) {
      console.error('Error validando múltiples NITs:', error);
      throw new Error('Error al validar los NITs. Intente nuevamente.');
    }
  }

  /**
   * Valida y normaliza un NIT de forma síncrona (solo validación básica)
   * Para validación completa, usar validateNit()
   *
   * @param nit - NIT a validar
   * @returns true si el NIT cumple validación básica
   */
  isValidBasicFormat(nit: string): boolean {
    if (!nit || typeof nit !== 'string') return false;

    const cleaned = nit.trim().replace(/\./g, '').replace(/-/g, '');

    // Debe ser numérico y tener entre 5 y 20 dígitos
    return /^\d{5,20}$/.test(cleaned);
  }
}

export default new NitValidationService();
