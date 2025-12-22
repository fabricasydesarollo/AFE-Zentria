/**
 * Dashboard constants and configurations
 */

import type { EstadoFactura } from '../types';

// Labels sin emojis para mayor profesionalismo
// REFACTORIZADO: Eliminado estado 'pendiente'
export const ESTADO_LABELS: Record<EstadoFactura | 'todos', string> = {
  todos: 'Todos los estados',
  en_revision: 'En Revisión',
  aprobada: 'Aprobado',
  aprobado: 'Aprobado',
  aprobada_auto: 'Aprobado Automático',
  rechazada: 'Rechazado',
  rechazado: 'Rechazado',
  pagada: 'Pagada',
  validada_contabilidad: 'Validada',
  devuelta_contabilidad: 'Devuelta',
};

// Colores mejorados para estados según mejores prácticas UX/UI
// - Verde: Aprobados (éxito confirmado)
// - Cyan/Info: Aprobados automáticamente + Validadas por Contador
// - Amarillo/Warning: En revisión (requiere atención/pendiente)
// - Rojo/Error: Rechazado + Devuelta por Contador (error/negativo)
// - Default/Gris: Pagada (completado/finalizado)
export const ESTADO_COLORS: Record<EstadoFactura, 'success' | 'info' | 'error' | 'warning' | 'default'> = {
  aprobado: 'success',      // Verde - Aprobado manual
  aprobada: 'success',      // Verde - Aprobado manual
  aprobada_auto: 'info',    // Cyan/Azul - Aprobado automático
  rechazado: 'error',       // Rojo - Rechazado
  rechazada: 'error',       // Rojo - Rechazado
  en_revision: 'warning',   // Amarillo - En revisión/pendiente
  pagada: 'default',        // Gris - Pagada (completado)
  validada_contabilidad: 'info',    // Cyan/Azul - Validada por Contador (diferente a aprobada)
  devuelta_contabilidad: 'error',   // Rojo - Devuelta por Contador (requiere corrección)
};

export const DEFAULT_ROWS_PER_PAGE = 10;

export const ROWS_PER_PAGE_OPTIONS = [5, 10, 25, 50];
