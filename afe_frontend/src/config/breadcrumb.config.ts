/**
 * Breadcrumb Configuration
 *
 * Sistema centralizado de configuración de rutas con soporte para breadcrumbs.
 * Cada ruta puede tener:
 * - breadcrumb: nombre a mostrar en la migaja
 * - getDynamicLabel: función para obtener nombres dinámicos (parámetros, estado, etc.)
 *
 * @author  Backend/Frontend
 * @version 1.0.0
 */

export interface BreadcrumbItem {
  path: string;
  label: string;
  icon?: string;
}

export interface RouteConfig {
  path: string;
  name: string;
  breadcrumb?: string;
  /**
   * Función para obtener label dinámico basado en estado o parámetros
   * @param params - Parámetros de ruta extraídos de la URL
   * @param state - Estado de Redux o context
   * @returns Label a mostrar en la migaja
   */
  getDynamicLabel?: (params: Record<string, any>, state?: any) => string | null;
  children?: RouteConfig[];
}

/**
 * Configuración centralizada de todas las rutas
 * Mantener en orden jerárquico para facilitar la navegación
 *
 * IMPORTANTE:
 * - Cada ruta debe tener un breadcrumb descriptivo
 * - Para rutas con parámetros dinámicos, usar getDynamicLabel
 * - El orden importa para la construcción de migas
 */
export const routeConfig: RouteConfig[] = [
  {
    path: '/',
    name: 'Inicio',
    breadcrumb: 'Dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    breadcrumb: 'Dashboard'
  },

  // === EMAIL CONFIGURATION ROUTES ===
  {
    path: '/email-config',
    name: 'Email Configuration',
    breadcrumb: 'Configuración de Correos',
    children: [
      {
        path: '/email-config/:id',
        name: 'Email Account Details',
        breadcrumb: 'Detalles',
        getDynamicLabel: (params, state) => {
          // Prioridad: obtener email actual del Redux
          if (state?.emailConfig?.cuentaActual?.email) {
            return state.emailConfig.cuentaActual.email;
          }
          // Fallback: usar el parámetro ID
          return params.id ? `Cuenta #${params.id}` : null;
        }
      }
    ]
  },

  // === INVOICE ROUTES ===
  {
    path: '/facturas',
    name: 'Por Revisar',
    breadcrumb: 'Por Revisar'
  },

  // === ADMIN ROUTES ===
  {
    path: '/admin/responsables',
    name: 'User Management',
    breadcrumb: 'Gestión de Usuarios'
  },
  {
    path: '/gestion/proveedores',
    name: 'Provider Management',
    breadcrumb: 'Gestión de Proveedores'
  },

  // === CONTADOR ROUTES ===
  {
    path: '/contabilidad/pendientes',
    name: 'Pending Invoices',
    breadcrumb: 'Facturas Pendientes'
  },

  // === SUPERADMIN ROUTES ===
  {
    path: '/superadmin/metricas',
    name: 'SuperAdmin Dashboard',
    breadcrumb: 'Métricas Sistema'
  },
  {
    path: '/superadmin/grupos',
    name: 'Groups Management',
    breadcrumb: 'Grupos y Sedes'
  },
  {
    path: '/superadmin/usuarios',
    name: 'Global Users',
    breadcrumb: 'Usuarios Globales'
  },
  {
    path: '/superadmin/roles',
    name: 'Roles Management',
    breadcrumb: 'Gestión de Roles'
  }
];

/**
 * Buscar una ruta en la configuración recursivamente
 */
export const findRouteConfig = (
  path: string,
  config: RouteConfig[] = routeConfig
): RouteConfig | null => {
  for (const route of config) {
    if (route.path === path) {
      return route;
    }
    if (route.children) {
      const found = findRouteConfig(path, route.children);
      if (found) return found;
    }
  }
  return null;
};

/**
 * Convertir parámetros de ruta (p. ej., :id) a valores reales
 * Útil para construir URLs clicables
 */
export const substitutePathParams = (
  path: string,
  params: Record<string, string>
): string => {
  let result = path;
  Object.entries(params).forEach(([key, value]) => {
    result = result.replace(`:${key}`, value);
  });
  return result;
};
