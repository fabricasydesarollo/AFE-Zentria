/**
 * TypeScript Types para Sistema Multi-Tenant de Grupos
 */

export interface Grupo {
  id: number;
  codigo_corto: string;
  nombre: string;
  descripcion?: string;
  grupo_padre_id?: number | null;
  nivel: number;
  ruta_jerarquica: string;
  activo: boolean;
  creado_en: string;
  actualizado_en: string;
  creado_por?: string;
  actualizado_por?: string;

  // Relaciones
  parent?: Grupo;
  children?: Grupo[];
}

export interface GrupoTree extends Grupo {
  children: GrupoTree[];
}

export interface GrupoCreate {
  codigo_corto: string;
  nombre: string;
  descripcion?: string;
  grupo_padre_id?: number | null;
  activo?: boolean;
  creado_por?: string;
}

export interface GrupoUpdate {
  codigo_corto?: string;
  nombre?: string;
  descripcion?: string;
  grupo_padre_id?: number | null;
  activo?: boolean;
  actualizado_por?: string;
}

export interface GrupoListResponse {
  grupos: Grupo[];
  total: number;
}

export interface GrupoStats {
  grupo_id: number;
  grupo_nombre: string;
  total_usuarios: number;
  total_facturas: number;
  facturas_pendientes: number;
  facturas_aprobadas: number;
}
