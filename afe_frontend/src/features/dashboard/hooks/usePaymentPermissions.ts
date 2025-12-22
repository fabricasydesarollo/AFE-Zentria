/**
 * usePaymentPermissions - Hook para gestionar permisos de pago por rol
 *
 * Encapsula toda la lógica de verificación de permisos para módulo de pagos,
 * reutilizando el sistema de permisos existente en constants/roles.ts
 *
 * Uso:
 * const { canViewPayments, canRegisterPayment, isCounterOrAdmin } = usePaymentPermissions();
 */

import { useSelector } from 'react-redux';
import { hasPermission } from '../../../constants/roles';
import { ROLES } from '../../../constants/roles';
import type { RootState } from '../../../app/store';

interface PaymentPermissions {
  // Permisos granulares de pago
  canViewPayments: boolean;
  canRegisterPayment: boolean;
  canViewPaymentHistory: boolean;
  canEditPayment: boolean;
  canDeletePayment: boolean;

  // Permisos agregados convenientes
  isCounterOrAdmin: boolean;
  hasAnyPaymentPermission: boolean;

  // Información del usuario
  userRole: string | null;
  userName: string | null;
}

/**
 * Hook que proporciona todos los permisos de pago para el usuario actual
 *
 * @returns {PaymentPermissions} Objeto con permisos y rol del usuario
 *
 * @example
 * const permissions = usePaymentPermissions();
 * if (permissions.canRegisterPayment) {
 *   // Mostrar botón de registrar pago
 * }
 */
export function usePaymentPermissions(): PaymentPermissions {
  // Obtener usuario del store Redux
  const user = useSelector((state: RootState) => state.auth.user);
  const userRole = user?.rol || null;

  // Verificar cada permiso individual usando la función existente
  const canViewPayments = hasPermission(userRole || '', 'canViewPayments');
  const canRegisterPayment = hasPermission(userRole || '', 'canRegisterPayment');
  const canViewPaymentHistory = hasPermission(userRole || '', 'canViewPaymentHistory');
  const canEditPayment = hasPermission(userRole || '', 'canEditPayment');
  const canDeletePayment = hasPermission(userRole || '', 'canDeletePayment');

  // Permisos agregados para conveniencia
  const isCounterOrAdmin = userRole === ROLES.CONTADOR || userRole === ROLES.ADMIN;
  const hasAnyPaymentPermission =
    canViewPayments || canRegisterPayment || canViewPaymentHistory || canEditPayment || canDeletePayment;

  return {
    // Permisos granulares
    canViewPayments,
    canRegisterPayment,
    canViewPaymentHistory,
    canEditPayment,
    canDeletePayment,

    // Permisos agregados
    isCounterOrAdmin,
    hasAnyPaymentPermission,

    // Info del usuario
    userRole,
    userName: user?.nombre || null,
  };
}

/**
 * Hook para verificar un permiso específico de pago
 *
 * Útil cuando solo necesitas verificar un permiso particular
 *
 * @param permission - Nombre del permiso a verificar
 * @returns {boolean} true si el usuario tiene el permiso
 *
 * @example
 * const canRegister = usePaymentPermission('canRegisterPayment');
 */
export function usePaymentPermission(
  permission: keyof Omit<PaymentPermissions, 'isCounterOrAdmin' | 'hasAnyPaymentPermission' | 'userRole' | 'userName'>
): boolean {
  const permissions = usePaymentPermissions();
  return permissions[permission];
}

/**
 * Hook para verificar si el usuario puede acceder al módulo de pagos
 *
 * Retorna true si el usuario tiene CUALQUIER permiso de pago
 *
 * @returns {boolean} true si tiene acceso al módulo
 *
 * @example
 * const hasAccess = useCanAccessPayments();
 * if (!hasAccess) return <Redirect />;
 */
export function useCanAccessPayments(): boolean {
  const { hasAnyPaymentPermission } = usePaymentPermissions();
  return hasAnyPaymentPermission;
}

/**
 * Hook para verificar si el usuario es contador o admin
 *
 * Versión abreviada útil en muchos casos
 *
 * @returns {boolean} true si es contador o admin
 *
 * @example
 * const isCounterOrAdmin = useIsCounterOrAdmin();
 * {isCounterOrAdmin && <PaymentButtons />}
 */
export function useIsCounterOrAdmin(): boolean {
  const { isCounterOrAdmin } = usePaymentPermissions();
  return isCounterOrAdmin;
}
