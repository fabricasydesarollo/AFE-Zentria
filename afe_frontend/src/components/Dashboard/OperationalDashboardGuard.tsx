/**
 * OperationalDashboardGuard - Permite acceso al dashboard operacional
 *
 * ARQUITECTURA 2025-12-09:
 * - SuperAdmin: Puede ver dashboard operacional en MODO SOLO LECTURA (Separation of Duties)
 * - Otros roles: Acceso normal con permisos según su rol
 *
 * El modo solo lectura para SuperAdmin se controla mediante:
 * - Permisos en roles.ts (canApprove: false, canReject: false, canDelete: false)
 * - Indicador visual en DashboardPage.tsx
 */

import { useAppSelector } from '../../app/hooks';
import DashboardPage from '../../features/dashboard/DashboardPage';

export default function OperationalDashboardGuard() {
  const user = useAppSelector((state) => state.auth.user);

  // TODOS los roles pueden acceder al dashboard operacional
  // SuperAdmin verá el dashboard en modo solo lectura (sin botones de acción)
  // Los permisos se manejan en roles.ts y la UI se adapta automáticamente
  return <DashboardPage />;
}
