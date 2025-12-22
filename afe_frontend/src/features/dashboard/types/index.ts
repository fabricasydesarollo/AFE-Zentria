/**
 * Types and interfaces for Dashboard feature
 */

export interface Factura {
  id: number;
  numero_factura: string;
  cufe?: string;
  nit_emisor: string;
  nombre_emisor: string;
  monto_total: number;
  fecha_emision: string;
  fecha_vencimiento?: string;
  estado: EstadoFactura;
  responsable_id?: number;
  observaciones?: string;
  archivo_adjunto?: string;
  // Campos de auditoría (para ADMIN) - Desde workflow
  nombre_responsable?: string;
  aprobado_por_workflow?: string;
  fecha_aprobacion_workflow?: string;
  rechazado_por_workflow?: string;
  fecha_rechazo_workflow?: string;
  motivo_rechazo_workflow?: string;
  tipo_aprobacion_workflow?: 'automatica' | 'manual' | 'masiva' | 'forzada';
  // Campos calculados
  accion_por?: string;
  fecha_accion?: string;
  // FASE 2 - Campos de pago (desde backend)
  total_calculado?: string;
  total_pagado?: string;
  pendiente_pagar?: string;
  esta_completamente_pagada?: boolean;
}

/**
 * Estados de factura (refactorizado - eliminado 'pendiente')
 */
export type EstadoFactura =
  | 'en_revision'
  | 'aprobada'
  | 'aprobado'
  | 'aprobada_auto'
  | 'rechazada'
  | 'rechazado'
  | 'pagada'
  | 'validada_contabilidad'
  | 'devuelta_contabilidad';

export interface DashboardStats {
  total: number;
  pendientes: number;  // Ahora mapea a 'en_revision'
  en_revision: number;
  aprobadas: number;
  aprobadas_auto: number;
  rechazadas: number;
  pagadas?: number;
}

export interface FacturaFormData {
  numero_factura: string;
  nit_emisor: string;
  nombre_emisor: string;
  monto_total: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  observaciones: string;
}

export type DialogMode = 'view' | 'edit' | 'create';

export type VistaFacturas = 'todas' | 'asignadas';

export interface FacturasFilters {
  searchTerm: string;
  filterEstado: EstadoFactura | 'todos';
  vistaFacturas: VistaFacturas;
}

export interface PaginationState {
  page: number;
  rowsPerPage: number;
}
