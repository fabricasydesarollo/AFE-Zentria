/**
 * TypeScript Types para Facturas y Workflow
 */

export interface Factura {
  id: number;
  numero_factura: string;
  cufe: string;
  fecha_emision: string | null;
  fecha_vencimiento?: string | null;
  nit?: string;
  proveedor_id: number | null;
  proveedor?: Proveedor;
  subtotal: number;
  iva: number;
  total: number;
  total_a_pagar: number;
  moneda: string;
  estado: EstadoFactura;
  observaciones?: string;
  periodo_factura?: string;

  // Campos de workflow (computed properties desde backend)
  aprobado_por_workflow?: string;
  fecha_aprobacion_workflow?: string;
  rechazado_por_workflow?: string;
  fecha_rechazo_workflow?: string;
  motivo_rechazo_workflow?: string;
  tipo_aprobacion_workflow?: 'automatica' | 'manual' | 'masiva' | 'forzada';
}

export interface Proveedor {
  id: number;
  nit: string;
  razon_social: string;
  area?: string;
}

export interface Workflow {
  id: number;
  factura_id: number;
  factura?: Factura;
  estado: EstadoWorkflow;
  tipo_aprobacion?: TipoAprobacion;
  responsable_id: number;
  area_responsable?: string;
  nit_proveedor?: string;
  es_identica_mes_anterior: boolean;
  porcentaje_similitud?: number;
  diferencias_detectadas?: Diferencia[];
  criterios_comparacion?: Record<string, any>;
  // Campos de aprobación/rechazo (desde workflow_aprobacion_facturas)
  fecha_aprobacion?: string;
  aprobada_por?: string;  // Nota: en workflow se llama aprobada_por
  fecha_rechazo?: string;
  rechazada_por?: string;  // Nota: en workflow se llama rechazada_por
  detalle_rechazo?: string;  // Nota: en workflow se llama detalle_rechazo
  factura_mes_anterior?: FacturaAnterior;
  factura_referencia?: Factura;
}

export interface FacturaAnterior {
  id: number;
  numero: string;
  total: number;
  fecha?: string;
}

export interface Diferencia {
  campo: string;
  actual: any;
  anterior: any;
  variacion_pct?: number;
}

export interface FacturaConWorkflow {
  factura: Factura;
  workflow?: Workflow;
  contexto_historico?: ContextoHistorico;
  tiene_workflow: boolean;
}

export interface ContextoHistorico {
  tipo_patron: 'TIPO_A' | 'TIPO_B' | 'TIPO_C';
  recomendacion: 'LISTA_PARA_APROBAR' | 'REQUIERE_ANALISIS';
  motivo: string;
  confianza: number;
  estadisticas: {
    pagos_analizados: number;
    meses_con_pagos: number;
    monto_promedio: number;
    monto_minimo: number;
    monto_maximo: number;
    coeficiente_variacion: number;
  };
  rango_esperado?: {
    inferior: number;
    superior: number;
  };
  ultimo_pago?: {
    fecha: string;
    monto: number;
  };
  pagos_historicos: PagoHistorico[];
  contexto_adicional: Record<string, any>;
}

export interface PagoHistorico {
  periodo: string;
  monto: number;
  factura_id: number;
  fecha: string | null;
}

export interface FacturaPendiente extends Workflow {
  workflow_id: number;
  numero_factura: string;
  proveedor: string;
  nit: string;
  monto: number;
  fecha_emision?: string;
  fecha_asignacion?: string;
  dias_pendiente: number;
  nombre_responsable?: string; // Nombre del responsable asignado
  contexto_historico?: ContextoHistorico; // Contexto histórico de la factura
}

export interface DashboardMetrics {
  resumen: {
    total_facturas: number;
    pendientes_revision: number;
    aprobadas_auto: number;
    aprobadas_manual: number;
    rechazadas: number;
  };
  metricas: {
    tasa_aprobacion_auto: number;
    tiempo_promedio_aprobacion_horas: number;
    facturas_vencidas: number;
  };
  por_proveedor: ProveedorMetric[];
}

export interface ProveedorMetric {
  proveedor: string;
  nit: string;
  total_facturas: number;
  pendientes: number;
}

/**
 * Estados de factura (refactorizado - eliminado 'pendiente')
 *
 * - en_revision: Factura requiere revisión manual (estado único de espera)
 * - aprobada: Factura aprobada manualmente por usuario
 * - aprobada_auto: Factura aprobada automáticamente por el sistema
 * - rechazada: Factura rechazada por usuario
 * - pagada: Factura procesada para pago
 */
export type EstadoFactura =
  | 'en_revision'
  | 'aprobada'
  | 'rechazada'
  | 'aprobada_auto'
  | 'pagada';

export type EstadoWorkflow =
  | 'recibida'
  | 'en_analisis'
  | 'aprobada_auto'
  | 'pendiente_revision'
  | 'en_revision'
  | 'aprobada_manual'
  | 'rechazada'
  | 'observada'
  | 'enviada_contabilidad'
  | 'procesada';

export type TipoAprobacion = 'automatica' | 'manual';

export interface AprobacionRequest {
  // El backend maneja automáticamente la creación/actualización del workflow
  // Solo se necesita el usuario que aprueba
  aprobado_por: string;
  observaciones?: string;
}

export interface RechazoRequest {
  // El backend maneja automáticamente la creación/actualización del workflow
  // Solo se necesita el usuario que rechaza y el motivo
  rechazado_por: string;
  motivo: string;
  detalle?: string;
}
