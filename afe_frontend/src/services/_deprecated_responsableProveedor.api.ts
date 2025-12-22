/**
 * Servicios API para gestión de asignaciones Responsable-Proveedor
 *
 * ⚠️ DEPRECATED - Este archivo está obsoleto
 *
 * @deprecated Usar asignacionNit.api.ts en su lugar
 * @see asignacionNit.api.ts
 *
 * Este servicio fue reemplazado por el sistema unificado de asignaciones NIT.
 * El backend ya no tiene el endpoint /responsable-proveedor/
 *
 * Migración:
 * - getAsignaciones() -> getAsignacionesNit()
 * - createAsignacion() -> createAsignacionNit()
 * - getProveedoresDeResponsable() -> getAsignacionesPorResponsable()
 *
 * Fecha de deprecación: 2025-10-19
 * Eliminar después de: 2025-11-19 (30 días)
 */
import apiClient from './api';

export interface Responsable {
  id: number;
  usuario: string;
  nombre: string;
  email: string;
}

export interface ProveedorInfo {
  id: number;
  nit: string;
  razon_social: string;
  area?: string;
}

export interface AsignacionResponsableProveedor {
  id: number;
  responsable_id: number;
  proveedor_id: number;
  activo: boolean;
  creado_en: string;
  responsable: Responsable;
  proveedor: ProveedorInfo;
}

export interface AsignacionCreate {
  responsable_id: number;
  proveedor_id: number;
  activo?: boolean;
}

export interface AsignacionBulkCreate {
  responsable_id: number;
  proveedor_ids: number[];
  activo?: boolean;
}

export interface AsignacionUpdate {
  responsable_id?: number;
  activo?: boolean;
}

/**
 * Listar todas las asignaciones con filtros opcionales
 */
export const getAsignaciones = async (params?: {
  skip?: number;
  limit?: number;
  responsable_id?: number;
  proveedor_id?: number;
  activo?: boolean;
}): Promise<AsignacionResponsableProveedor[]> => {
  const response = await apiClient.get('/responsable-proveedor/', { params });
  return response.data;
};

/**
 * Obtener una asignación específica por ID
 */
export const getAsignacion = async (
  id: number
): Promise<AsignacionResponsableProveedor> => {
  const response = await apiClient.get(`/responsable-proveedor/${id}`);
  return response.data;
};

/**
 * Crear una nueva asignación
 */
export const createAsignacion = async (data: AsignacionCreate): Promise<any> => {
  const response = await apiClient.post('/responsable-proveedor/', data);
  return response.data;
};

/**
 * Crear múltiples asignaciones (bulk)
 */
export const createAsignacionesBulk = async (
  data: AsignacionBulkCreate
): Promise<{
  total_procesados: number;
  creadas: number;
  omitidas: number;
  errores: string[];
  mensaje: string;
}> => {
  const response = await apiClient.post('/responsable-proveedor/bulk', data);
  return response.data;
};

/**
 * Actualizar una asignación existente
 */
export const updateAsignacion = async (
  id: number,
  data: AsignacionUpdate
): Promise<any> => {
  const response = await apiClient.put(`/responsable-proveedor/${id}`, data);
  return response.data;
};

/**
 * Eliminar una asignación
 */
export const deleteAsignacion = async (id: number): Promise<void> => {
  await apiClient.delete(`/responsable-proveedor/${id}`);
};

/**
 * Obtener todos los responsables (usuarios)
 */
export const getResponsables = async (params?: {
  skip?: number;
  limit?: number;
}): Promise<Responsable[]> => {
  const response = await apiClient.get('/usuarios/', { params });
  return response.data;
};

/**
 * Obtener todos los responsables asignados a un proveedor
 */
export const getResponsablesDeProveedor = async (
  proveedorId: number
): Promise<{
  proveedor_id: number;
  proveedor: { nit: string; razon_social: string };
  responsables: Array<{
    asignacion_id: number;
    responsable_id: number;
    usuario: string;
    nombre: string;
    email: string;
    activo: boolean;
  }>;
  total: number;
}> => {
  const response = await apiClient.get(
    `/responsable-proveedor/proveedor/${proveedorId}/responsables`
  );
  return response.data;
};

/**
 * Obtener todos los proveedores asignados a un responsable
 */
export const getProveedoresDeResponsable = async (
  responsableId: number,
  activo?: boolean
): Promise<{
  responsable_id: number;
  responsable: { usuario: string; nombre: string };
  proveedores: Array<{
    asignacion_id: number;
    proveedor_id: number;
    nit: string;
    razon_social: string;
    area?: string;
    activo: boolean;
  }>;
  total: number;
}> => {
  const params = activo !== undefined ? { activo } : {};
  const response = await apiClient.get(
    `/responsable-proveedor/responsable/${responsableId}/proveedores`,
    { params }
  );
  return response.data;
};
