/**
 * Servicios API para gestion de Asignaciones NIT-Responsable
 *
 * Sistema unificado que reemplaza responsable-proveedor
 * Usa NITs en lugar de proveedor_id para mayor flexibilidad
 *
 * @version 2.0
 * @date 2025-10-19
 */
import apiClient from './api';

// ============================================================================
// INTERFACES Y TIPOS
// ============================================================================

/**
 * Informacion basica de un responsable
 */
export interface Responsable {
  id: number;
  usuario: string;
  nombre: string;
  email: string;
  area?: string;
  activo?: boolean;
}

/**
 * Informacion de proveedor (para display)
 */
export interface ProveedorInfo {
  id?: number;
  nit: string;
  razon_social: string;
  area?: string;
}

/**
 * Asignacion NIT-Responsable (response del backend)
 */
export interface AsignacionNit {
  id: number;
  nit: string;
  nombre_proveedor: string;
  responsable_id: number;
  grupo_id: number | null;  // ← NUEVO: grupo (sede/subsede) - nullable por compatibilidad con datos existentes
  area: string;
  permitir_aprobacion_automatica: boolean;
  requiere_revision_siempre: boolean;
  activo: boolean;
  creado_en: string;
  actualizado_en?: string;
  // Relaciones opcionales (cuando se usa joinedload)
  responsable?: Responsable;
}

/**
 * Datos para crear una nueva asignacion
 */
export interface AsignacionNitCreate {
  nit: string;
  nombre_proveedor: string;
  responsable_id: number;
  grupo_id: number;  // ← NUEVO: grupo obligatorio (sede/subsede)
  area?: string;
  permitir_aprobacion_automatica?: boolean;
  requiere_revision_siempre?: boolean;
  activo?: boolean;
}

/**
 * Datos para crear multiples asignaciones (bulk)
 */
export interface AsignacionNitBulkCreate {
  responsable_id: number;
  nits: Array<{
    nit: string;
    nombre_proveedor: string;
    area?: string;
  }>;
  permitir_aprobacion_automatica?: boolean;
  activo?: boolean;
}

/**
 * Datos para actualizar una asignacion
 */
export interface AsignacionNitUpdate {
  nombre_proveedor?: string;
  responsable_id?: number;
  area?: string;
  permitir_aprobacion_automatica?: boolean;
  activo?: boolean;
}

/**
 * Response de operacion bulk
 */
export interface BulkCreateResponse {
  total_procesados: number;
  creadas: number;
  actualizadas: number;
  reactivadas?: number;
  omitidas: number;
  errores: string[];
  mensaje: string;
  nits_creados?: string[];
  nits_reactivados?: string[];
  nits_omitidos?: string[];
}

/**
 * Asignaciones agrupadas por responsable
 */
export interface AsignacionesPorResponsable {
  responsable_id: number;
  responsable: {
    usuario: string;
    nombre: string;
    email: string;
  };
  asignaciones: AsignacionNit[];
  total: number;
}

// ============================================================================
// FUNCIONES API
// ============================================================================

/**
 * Listar todas las asignaciones NIT con filtros opcionales
 *
 * @param params - Filtros de busqueda
 * @returns Lista de asignaciones
 */
export const getAsignacionesNit = async (params?: {
  skip?: number;
  limit?: number;
  responsable_id?: number;
  nit?: string;
  activo?: boolean;
}): Promise<AsignacionNit[]> => {
  const response = await apiClient.get('/asignacion-nit/', { params });
  return response.data;
};

/**
 * Obtener una asignacion especifica por ID
 *
 * @param id - ID de la asignacion
 * @returns Asignacion encontrada
 */
export const getAsignacionNit = async (id: number): Promise<AsignacionNit> => {
  const response = await apiClient.get(`/asignacion-nit/${id}`);
  return response.data;
};

/**
 * Crear una nueva asignacion NIT-Responsable
 *
 * @param data - Datos de la asignacion
 * @returns Asignacion creada
 */
export const createAsignacionNit = async (
  data: AsignacionNitCreate
): Promise<AsignacionNit> => {
  const response = await apiClient.post('/asignacion-nit/', data);
  return response.data;
};

/**
 * Crear multiples asignaciones en una sola operacion (bulk)
 * Usa /bulk-simple: requiere que los NITs existan en proveedores
 *
 * @param data - Datos para creacion masiva
 * @returns Resultado de la operacion
 * @deprecated Usar createAsignacionesNitBulkFromConfig en su lugar
 */
export const createAsignacionesNitBulk = async (
  data: { responsable_id: number; nits: string }
): Promise<BulkCreateResponse> => {
  const response = await apiClient.post('/asignacion-nit/bulk-simple', data);
  return response.data;
};

/**
 * Crear multiples asignaciones desde nit_configuracion (bulk)
 * Usa /bulk-nit-config: NO requiere que los NITs existan en proveedores
 * Valida contra nit_configuracion en su lugar
 *
 * @param data - Datos para creacion masiva (responsable_id y NITs como string)
 * @returns Resultado de la operacion
 */
export const createAsignacionesNitBulkFromConfig = async (
  data: { responsable_id: number; nits: string; permitir_aprobacion_automatica?: boolean }
): Promise<BulkCreateResponse> => {
  const response = await apiClient.post('/asignacion-nit/bulk-nit-config', data);
  return response.data;
};

/**
 * Actualizar una asignacion existente
 *
 * @param id - ID de la asignacion
 * @param data - Datos a actualizar
 * @returns Asignacion actualizada
 */
export const updateAsignacionNit = async (
  id: number,
  data: AsignacionNitUpdate
): Promise<AsignacionNit> => {
  const response = await apiClient.put(`/asignacion-nit/${id}`, data);
  return response.data;
};

/**
 * Eliminar (desactivar) una asignacion
 *
 * @param id - ID de la asignacion
 */
export const deleteAsignacionNit = async (id: number): Promise<void> => {
  await apiClient.delete(`/asignacion-nit/${id}`);
};

/**
 * Obtener todas las asignaciones de un responsable especifico
 *
 * @param responsableId - ID del responsable
 * @param activo - Filtrar por estado activo/inactivo (opcional)
 * @returns Asignaciones del responsable
 */
export const getAsignacionesPorResponsable = async (
  responsableId: number,
  activo?: boolean
): Promise<AsignacionesPorResponsable> => {
  const params = activo !== undefined ? { activo } : {};
  const response = await apiClient.get(
    `/asignacion-nit/por-responsable/${responsableId}`,
    { params }
  );
  return response.data;
};

/**
 * Obtener todos los responsables disponibles
 *
 * @param params - Parametros de paginacion
 * @returns Lista de responsables
 */
export const getResponsables = async (params?: {
  skip?: number;
  limit?: number;
  activo?: boolean;
}): Promise<Responsable[]> => {
  const response = await apiClient.get('/usuarios/', { params });
  return response.data;
};

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

/**
 * Obtener NITs asignados a un responsable (solo los NITs)
 *
 * @param responsableId - ID del responsable
 * @returns Array de NITs
 */
export const getNitsDeResponsable = async (
  responsableId: number
): Promise<string[]> => {
  const data = await getAsignacionesPorResponsable(responsableId, true);
  return data.asignaciones.map((asig) => asig.nit);
};

/**
 * Verificar si un NIT esta asignado a algun responsable
 *
 * @param nit - NIT a verificar
 * @returns true si esta asignado, false si no
 */
export const isNitAsignado = async (nit: string): Promise<boolean> => {
  try {
    const asignaciones = await getAsignacionesNit({ nit, activo: true });
    return asignaciones.length > 0;
  } catch {
    return false;
  }
};

/**
 * Obtener el responsable asignado a un NIT especifico
 *
 * @param nit - NIT del proveedor
 * @returns Asignacion encontrada o null
 */
export const getResponsableDeNit = async (
  nit: string
): Promise<AsignacionNit | null> => {
  const asignaciones = await getAsignacionesNit({ nit, activo: true });
  return asignaciones.length > 0 ? asignaciones[0] : null;
};

// ============================================================================
// EXPORT DEFAULT
// ============================================================================

export default {
  // CRUD Operations
  getAsignacionesNit,
  getAsignacionNit,
  createAsignacionNit,
  createAsignacionesNitBulk,
  createAsignacionesNitBulkFromConfig,
  updateAsignacionNit,
  deleteAsignacionNit,

  // Queries
  getAsignacionesPorResponsable,
  getResponsables,

  // Utilities
  getNitsDeResponsable,
  isNitAsignado,
  getResponsableDeNit,
};
