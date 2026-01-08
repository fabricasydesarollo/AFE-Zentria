/**
 * useCuarentenaData - Hook to load quarantine information
 *
 * Fetches quarantine data from the dashboard endpoint
 * Backend: GET /api/v1/dashboard/mes-actual → { cuarentena: {...} }
 *
 * Architecture: Multi-Tenant (2025-12-29)
 */

import { useState, useEffect } from 'react';
import apiClient from '../../../services/api';

interface CuarentenaGrupo {
  grupo_id: number;
  nombre_grupo: string;
  codigo_grupo: string;
  total_facturas: number;
  impacto_financiero: number;
  url_asignar_responsables: string;
}

interface CuarentenaInfo {
  total_facturas: number;
  total_grupos_afectados: number;
  impacto_financiero_total: number;
  grupos: CuarentenaGrupo[];
}

interface DashboardResponse {
  cuarentena?: CuarentenaInfo | null;
  // ... other dashboard fields
}

export function useCuarentenaData(userRole?: string) {
  const [cuarentena, setCuarentena] = useState<CuarentenaInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Solo cargar para superadmin y admin
    if (userRole !== 'superadmin' && userRole !== 'admin') {
      return;
    }

    const loadCuarentena = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.get<DashboardResponse>('/dashboard/mes-actual');

        // El backend incluye el campo `cuarentena` si es admin/superadmin
        if (response.data.cuarentena) {
          setCuarentena(response.data.cuarentena);
        } else {
          setCuarentena(null);
        }
      } catch (err) {
        console.error('Error cargando información de cuarentena:', err);
        setError('Error al cargar información de cuarentena');
        setCuarentena(null);
      } finally {
        setLoading(false);
      }
    };

    loadCuarentena();
  }, [userRole]);

  return {
    cuarentena,
    loading,
    error,
  };
}
