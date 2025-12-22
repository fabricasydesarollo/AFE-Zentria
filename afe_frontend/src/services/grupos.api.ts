/**
 * Servicio API para gestión de grupos multi-tenant
 *
 * Proporciona comunicación con el backend para:
 * - Listar grupos disponibles
 * - Obtener árbol jerárquico de grupos
 * - Gestionar grupos (CRUD - solo admin)
 * - Obtener estadísticas por grupo
 *
 * @author 
 * @date 2025-12-04
 */

import apiClient from './api';
import {
  Grupo,
  GrupoTree,
  GrupoCreate,
  GrupoUpdate,
  GrupoListResponse,
  GrupoStats,
} from '../types/grupo.types';

/**
 * Servicio centralizado para operaciones con grupos
 */
class GruposService {
  private baseUrl = '/grupos';

  /**
   * Listar todos los grupos disponibles
   * @param params Filtros opcionales (activo, parent_id, nivel)
   * @returns Lista de grupos con metadata
   */
  async listarGrupos(params?: {
    activo?: boolean;
    parent_id?: number;
    nivel?: number;
  }): Promise<GrupoListResponse> {
    const response = await apiClient.get<GrupoListResponse>(this.baseUrl, { params });
    return response.data;
  }

  /**
   * Obtener árbol jerárquico completo de grupos
   * Útil para mostrar estructura organizacional
   * @returns Árbol de grupos con relaciones padre-hijo
   */
  async obtenerArbolGrupos(): Promise<GrupoTree[]> {
    const response = await apiClient.get<GrupoTree[]>(`${this.baseUrl}/tree`);
    return response.data;
  }

  /**
   * Obtener detalle de un grupo específico
   * @param id ID del grupo
   * @returns Información completa del grupo
   */
  async obtenerGrupo(id: number): Promise<Grupo> {
    const response = await apiClient.get<Grupo>(`${this.baseUrl}/${id}`);
    return response.data;
  }

  /**
   * Crear nuevo grupo (solo admin)
   * @param data Datos del nuevo grupo
   * @returns Grupo creado
   */
  async crearGrupo(data: GrupoCreate): Promise<Grupo> {
    const response = await apiClient.post<Grupo>(this.baseUrl, data);
    return response.data;
  }

  /**
   * Actualizar grupo existente (solo admin)
   * @param id ID del grupo a actualizar
   * @param data Datos a actualizar
   * @returns Grupo actualizado
   */
  async actualizarGrupo(id: number, data: GrupoUpdate): Promise<Grupo> {
    const response = await apiClient.put<Grupo>(`${this.baseUrl}/${id}`, data);
    return response.data;
  }

  /**
   * Eliminar grupo (solo admin)
   * Nota: Solo permite eliminar grupos sin dependencias
   * @param id ID del grupo a eliminar
   */
  async eliminarGrupo(id: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${id}`);
  }

  /**
   * Obtener estadísticas del grupo
   * Incluye: total usuarios, facturas, métricas de aprobación
   * @param id ID del grupo
   * @returns Estadísticas del grupo
   */
  async obtenerEstadisticas(id: number): Promise<GrupoStats> {
    const response = await apiClient.get<GrupoStats>(`${this.baseUrl}/${id}/stats`);
    return response.data;
  }

  /**
   * Obtener grupos del usuario actual
   * Útil para poblar selector de grupos
   * @returns Lista de grupos a los que el usuario tiene acceso
   */
  async obtenerMisGrupos(): Promise<Grupo[]> {
    const response = await apiClient.get<Grupo[]>(`${this.baseUrl}/mis-grupos`);
    return response.data;
  }

  // ========================================
  // FUNCIONES SUPERADMIN - Gestión de Usuarios en Grupos
  // ========================================

  /**
   * Obtener usuarios asignados a un grupo (SuperAdmin)
   * @param grupoId ID del grupo
   * @returns Lista de usuarios con acceso al grupo
   */
  async obtenerUsuariosGrupo(grupoId: number): Promise<any[]> {
    const response = await apiClient.get(`${this.baseUrl}/${grupoId}/responsables`);
    return response.data || [];
  }

  /**
   * Asignar usuario a un grupo (SuperAdmin)
   * @param grupoId ID del grupo
   * @param usuarioId ID del usuario a asignar
   * @returns Confirmación de asignación
   */
  async asignarUsuario(grupoId: number, usuarioId: number): Promise<any> {
    const payload = { responsable_id: usuarioId, activo: true };
    const response = await apiClient.post(`${this.baseUrl}/${grupoId}/responsables`, payload);
    return response.data;
  }

  /**
   * Remover usuario de un grupo (SuperAdmin)
   * @param grupoId ID del grupo
   * @param usuarioId ID del usuario a remover
   */
  async removerUsuario(grupoId: number, usuarioId: number): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${grupoId}/responsables/${usuarioId}`);
  }

  /**
   * Obtener todos los usuarios disponibles para asignar a grupos (SuperAdmin)
   * @returns Lista de todos los usuarios del sistema
   */
  async obtenerTodosUsuarios(): Promise<any[]> {
    const response = await apiClient.get('/usuarios');
    return response.data.usuarios || response.data;
  }
}

// Exportar instancia única del servicio
export default new GruposService();
