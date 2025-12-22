/**
 * Types y interfaces para el sistema de pagos (Payment System)
 * Fase 2: Frontend Implementation
 *
 * Defines data structures for payment recording, history, and invoice payment status
 */

/** Estados posibles de un pago */
export enum EstadoPago {
  COMPLETADO = 'completado',
  FALLIDO = 'fallido',
  CANCELADO = 'cancelado'
}

/** Métodos de pago disponibles */
export enum MetodoPago {
  CHEQUE = 'cheque',
  TRANSFERENCIA = 'transferencia',
  EFECTIVO = 'efectivo',
  TARJETA = 'tarjeta',
  OTRO = 'otro'
}

/** Información de un pago registrado */
export interface Pago {
  id: number;
  factura_id: number;
  numero_factura?: string; // Número de factura asociada (opcional, viene del historial completo)
  proveedor?: string; // Razón social del proveedor (opcional, viene del historial completo)
  monto_pagado: string | number; // Cantidad como string o number para evitar pérdida de precisión
  referencia_pago: string; // Identificador único del pago (CHQ-001, TRF-001, etc)
  metodo_pago: string;
  estado_pago: EstadoPago;
  procesado_por: string; // Email del contador que registró el pago
  fecha_pago: string; // ISO 8601 datetime
  creado_en: string;
  actualizado_en?: string; // Opcional para compatibilidad con diferentes endpoints
}

/** Request para registrar un pago */
export interface PagoRequest {
  monto_pagado: number | string;
  referencia_pago: string;
  metodo_pago?: string;
}

/** Response después de registrar un pago */
export interface PagoResponse {
  id: number;
  factura_id: number;
  monto_pagado: string;
  referencia_pago: string;
  metodo_pago: string;
  estado_pago: EstadoPago;
  procesado_por: string;
  fecha_pago: string;
}

/** Información de estado de pago de una factura */
export interface EstadoPagoFactura {
  total_pagado: string; // Suma de todos los pagos completados
  pendiente_pagar: string; // Total a pagar - total pagado
  esta_completamente_pagada: boolean; // true si total_pagado >= total_calculado
  pagos: Pago[]; // Historial de pagos
}

/** Factura con información de pagos incluida */
export interface FacturaConPagos {
  id: number;
  numero_factura: string;
  estado: string; // 'en_revision', 'aprobada', 'pagada', etc.
  total_calculado: string;
  subtotal: string;
  iva: string;
  total_a_pagar: string;
  monto_total: string;
  fecha_emision: string;

  // Información de pagos
  total_pagado: string;
  pendiente_pagar: string;
  esta_completamente_pagada: boolean;
  pagos: Pago[];

  // Información del proveedor
  proveedor: {
    id: number;
    nit: string;
    razon_social: string;
  };

  // Información del responsable
  responsable: {
    id: number;
    nombre: string;
    usuario: string;
  };

  // Auditoría
  accion_por: string;
  fecha_accion: string;
  creado_en: string;
  actualizado_en: string;
}

/** Response con list de facturas pendientes de pago */
export interface FacturasPendientesResponse {
  total: number;
  facturas: FacturaConPagos[];
}

/** Estado para el modal de registro de pago */
export interface ModalRegistroPagoState {
  isOpen: boolean;
  facturaId: number | null;
  isLoading: boolean;
  error: string | null;
}

/** Estado para el modal de historial de pagos */
export interface ModalHistorialPagosState {
  isOpen: boolean;
  facturaId: number | null;
  factura: FacturaConPagos | null;
  isLoading: boolean;
  error: string | null;
}

/** Estado general de pagos en la aplicación */
export interface PaymentState {
  facturaActual: FacturaConPagos | null;
  facturasPendientes: FacturaConPagos[];
  modalRegistroPago: ModalRegistroPagoState;
  modalHistorialPagos: ModalHistorialPagosState;
  isLoading: boolean;
  error: string | null;
  lastPaymentReference: string | null; // Para evitar duplicados
}

/** Validación de formulario de pago */
export interface ValidacionPago {
  isValid: boolean;
  errors: {
    monto_pagado?: string;
    referencia_pago?: string;
    metodo_pago?: string;
  };
}

/** Estadísticas de pagos para dashboard */
export interface EstadisticasPagos {
  total_facturas: number;
  facturas_pagadas: number;
  facturas_por_pagar: number;
  total_monto: string;
  total_pagado: string;
  total_pendiente: string;
  promedio_dias_pago: number;
}

/** Filtros para lista de facturas */
export interface FiltrosPagos {
  estado_pago?: 'pagada' | 'por_pagar' | 'todas';
  fecha_inicio?: string;
  fecha_fin?: string;
  proveedor_id?: number;
  responsable_id?: number;
  monto_minimo?: number;
  monto_maximo?: number;
}

/** Opciones para paginación de pagos */
export interface PaginacionPagos {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

/** Response paginado con lista de pagos */
export interface PagosPaginados {
  data: Pago[];
  pagination: PaginacionPagos;
}
