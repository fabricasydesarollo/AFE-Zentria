import { Routes, Route, Navigate } from 'react-router-dom';
import { useAppSelector } from './app/hooks';
import MainLayout from './components/Layout/MainLayout';
import LoginPage from './features/auth/LoginPage';
import MicrosoftCallbackPage from './features/auth/MicrosoftCallbackPage';
import FacturasPage from './features/facturas/FacturasPage';
import FacturasPendientesPage from './features/facturas/FacturasPendientesPage';
import ResponsablesPage from './features/admin/ResponsablesPage';
import ProveedoresManagementPage from './features/proveedores/ProveedoresManagementPage';
import EmailConfigPage from './features/email-config/EmailConfigPage';
import CuentaDetailPage from './features/email-config/CuentaDetailPage';
import GruposPage from './features/grupos/GruposPage';
import { SuperAdminDashboard, UsuariosGlobalesPage, RolesPage } from './features/superadmin';
import RoleGuard from './components/Auth/RoleGuard';
import RoleDashboardRouter from './components/Dashboard/RoleDashboardRouter';
import OperationalDashboardGuard from './components/Dashboard/OperationalDashboardGuard';

/**
 * App Routes Configuration
 */

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/microsoft/callback" element={<MicrosoftCallbackPage />} />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<RoleDashboardRouter />} />
        <Route path="dashboard" element={<OperationalDashboardGuard />} />
        <Route path="facturas" element={<FacturasPage />} />

        {/* Ruta para contadores - Facturas Pendientes (NUEVO 2025-11-18) */}
        <Route
          path="contabilidad/pendientes"
          element={
            <RoleGuard allowedRoles={['contador']}>
              <FacturasPendientesPage />
            </RoleGuard>
          }
        />

        {/* Rutas de administración - admin y viewer (solo lectura) */}
        <Route
          path="admin/responsables"
          element={
            <RoleGuard allowedRoles={['admin', 'viewer']}>
              <ResponsablesPage />
            </RoleGuard>
          }
        />

        {/* Gestión consolidada de proveedores y asignaciones - admin, viewer y superadmin */}
        <Route
          path="gestion/proveedores"
          element={
            <RoleGuard allowedRoles={['admin', 'viewer', 'superadmin']}>
              <ProveedoresManagementPage />
            </RoleGuard>
          }
        />

        {/* Configuración de Correos - admin y superadmin */}
        <Route
          path="email-config"
          element={
            <RoleGuard allowedRoles={['admin', 'superadmin']}>
              <EmailConfigPage />
            </RoleGuard>
          }
        />
        <Route
          path="email-config/:id"
          element={
            <RoleGuard allowedRoles={['admin', 'superadmin']}>
              <CuentaDetailPage />
            </RoleGuard>
          }
        />

        {/* Rutas SuperAdmin - Gestión Global */}
        <Route
          path="superadmin/metricas"
          element={
            <RoleGuard allowedRoles={['superadmin']}>
              <SuperAdminDashboard />
            </RoleGuard>
          }
        />
        <Route
          path="superadmin/grupos"
          element={
            <RoleGuard allowedRoles={['superadmin']}>
              <GruposPage />
            </RoleGuard>
          }
        />
        <Route
          path="superadmin/usuarios"
          element={
            <RoleGuard allowedRoles={['superadmin']}>
              <UsuariosGlobalesPage />
            </RoleGuard>
          }
        />
        <Route
          path="superadmin/roles"
          element={
            <RoleGuard allowedRoles={['superadmin']}>
              <RolesPage />
            </RoleGuard>
          }
        />

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}

export default AppRoutes;
