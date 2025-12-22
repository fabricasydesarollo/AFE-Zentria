/**
 * RoleDashboardRouter - Enrutador inteligente de dashboard según rol
 *
 * Redirige automáticamente al dashboard correcto según el rol del usuario:
 * - SuperAdmin -> Dashboard administrativo (/superadmin/dashboard)
 * - Otros roles -> Dashboard operacional de facturas (/dashboard)
 */

import { Navigate } from 'react-router-dom';
import { useAppSelector } from '../../app/hooks';

export default function RoleDashboardRouter() {
  const user = useAppSelector((state) => state.auth.user);
  const userRole = user?.rol?.toLowerCase();

  // SuperAdmin va a su dashboard administrativo
  if (userRole === 'superadmin') {
    return <Navigate to="/superadmin/dashboard" replace />;
  }

  // Todos los demás roles van al dashboard operacional de facturas
  return <Navigate to="/dashboard" replace />;
}
