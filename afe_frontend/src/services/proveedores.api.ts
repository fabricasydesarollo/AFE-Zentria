/**
 * Servicios API para gestión de Proveedores
 */
import apiClient from './api';

export interface Proveedor {
  id: number;
  nit: string;
  razon_social: string;
  area?: string;
  contacto_email?: string;
  telefono?: string;
  direccion?: string;
  activo: boolean;
  creado_en?: string;
}

export interface ProveedorCreate {
  nit: string;
  razon_social: string;
  area?: string;
  contacto_email?: string;
  telefono?: string;
  direccion?: string;
  activo?: boolean;
}

export interface ProveedorUpdate extends Partial<ProveedorCreate> {}

/**
 * Obtener lista de proveedores
 */
export const getProveedores = async (params?: {
  skip?: number;
  limit?: number;
}): Promise<Proveedor[]> => {
  const response = await apiClient.get('/proveedores/', { params });
  return response.data;
};

/**
 * Obtener un proveedor por ID
 */
export const getProveedor = async (id: number): Promise<Proveedor> => {
  const response = await apiClient.get(`/proveedores/${id}`);
  return response.data;
};

/**
 * Crear un nuevo proveedor
 */
export const createProveedor = async (data: ProveedorCreate): Promise<Proveedor> => {
  const response = await apiClient.post('/proveedores/', data);
  return response.data;
};

/**
 * Actualizar un proveedor existente
 */
export const updateProveedor = async (
  id: number,
  data: ProveedorUpdate
): Promise<Proveedor> => {
  const response = await apiClient.put(`/proveedores/${id}`, data);
  return response.data;
};

/**
 * Eliminar un proveedor
 */
export const deleteProveedor = async (id: number): Promise<void> => {
  await apiClient.delete(`/proveedores/${id}`);
};

/**
 * Buscar proveedores por NIT o razón social
 */
export const searchProveedores = async (query: string): Promise<Proveedor[]> => {
  const response = await apiClient.get('/proveedores/', {
    params: { search: query, limit: 50 }
  });
  return response.data;
};
