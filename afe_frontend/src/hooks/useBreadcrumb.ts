/**
 * useBreadcrumb Hook
 *
 * Hook personalizado para generar breadcrumbs basados en la ruta actual
 * y la configuración centralizada.
 *
 * Características:
 * - Extrae parámetros dinámicos de la URL
 * - Obtiene labels dinámicos del estado (Redux)
 * - Genera rutas clicables válidas
 * - Memoizado para evitar recálculos innecesarios
 * - Maneja rutas no configuradas gracefully
 *
 * @author  Backend/Frontend
 * @version 1.0.0
 */

import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useAppSelector } from '../app/hooks';
import {
  BreadcrumbItem,
  findRouteConfig
} from '../config/breadcrumb.config';

interface UseBreadcrumbReturn {
  breadcrumbs: BreadcrumbItem[];
  isLoading: boolean;
}

/**
 * Extraer parámetros de ruta de la URL
 * Ejemplo: /email-config/3 → { id: '3' }
 */
const extractPathParams = (
  currentPath: string,
  routePath: string
): Record<string, string> => {
  const pathSegments = currentPath.split('/').filter(Boolean);
  const routeSegments = routePath.split('/').filter(Boolean);

  const params: Record<string, string> = {};

  for (let i = 0; i < routeSegments.length; i++) {
    if (routeSegments[i].startsWith(':')) {
      const paramName = routeSegments[i].slice(1);
      params[paramName] = pathSegments[i] || '';
    }
  }

  return params;
};

/**
 * Construir breadcrumbs a partir de la ruta actual
 */
const buildBreadcrumbs = (
  currentPath: string,
  state: any
): BreadcrumbItem[] => {
  const breadcrumbs: BreadcrumbItem[] = [];
  const pathSegments = currentPath === '/' ? [''] : currentPath.split('/').filter(Boolean);

  let accumulatedPath = '';

  for (let i = 0; i < pathSegments.length; i++) {
    const segment = pathSegments[i] || '';
    accumulatedPath = i === 0 ? '/' + segment : accumulatedPath + '/' + segment;

    // Buscar la configuración de ruta que coincida
    const routeConfig = findRouteConfig(accumulatedPath);

    if (!routeConfig) continue;

    const params = extractPathParams(accumulatedPath, routeConfig.path);

    // Obtener el label (dinámico o estático)
    let label = routeConfig.breadcrumb || routeConfig.name;

    if (routeConfig.getDynamicLabel) {
      const dynamicLabel = routeConfig.getDynamicLabel(params, state);
      if (dynamicLabel) {
        label = dynamicLabel;
      }
    }

    breadcrumbs.push({
      path: accumulatedPath,
      label,
      icon: routeConfig.breadcrumb?.includes('Correos') ? 'email' : undefined
    });
  }

  // Siempre incluir Dashboard al inicio
  if (
    breadcrumbs.length === 0 ||
    (breadcrumbs[0]?.path !== '/' && breadcrumbs[0]?.path !== '/dashboard')
  ) {
    breadcrumbs.unshift({
      path: '/dashboard',
      label: 'Dashboard'
    });
  }

  return breadcrumbs;
};

/**
 * Hook principal para obtener breadcrumbs
 *
 * @returns {UseBreadcrumbReturn} Objeto con breadcrumbs y estado de carga
 *
 * @example
 * const { breadcrumbs } = useBreadcrumb();
 *
 * breadcrumbs.forEach(crumb => {
 *   console.log(crumb.label, crumb.path);
 * });
 */
export const useBreadcrumb = (): UseBreadcrumbReturn => {
  const location = useLocation();
  const emailConfigState = useAppSelector(state => state.emailConfig);

  // Memoizar el cálculo de breadcrumbs
  // Solo recalcular si cambia la ruta o el estado relevante
  const breadcrumbs = useMemo(() => {
    return buildBreadcrumbs(location.pathname, { emailConfig: emailConfigState });
  }, [location.pathname, emailConfigState?.cuentaActual?.email]);

  return {
    breadcrumbs,
    isLoading: false // Puede ser true si estás cargando datos
  };
};

export default useBreadcrumb;
