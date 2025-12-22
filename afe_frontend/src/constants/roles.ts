/**
 * Constantes y utilidades para roles de usuario
 */

// Roles del sistema
export const ROLES = {
  SUPERADMIN: 'superadmin',
  ADMIN: 'admin',
  RESPONSABLE: 'responsable',
  CONTADOR: 'contador', //  Valida factras y devuelve facturas
  VIEWER: 'viewer',
} as const;

// Tipo para roles
export type Role = typeof ROLES[keyof typeof ROLES];

// Traducciones de roles para UI
export const ROLE_LABELS: Record<Role, string> = {
  [ROLES.SUPERADMIN]: 'Super Administrador',
  [ROLES.ADMIN]: 'Administrador',
  [ROLES.RESPONSABLE]: 'Responsable',
  [ROLES.CONTADOR]: 'Contador',
  [ROLES.VIEWER]: 'Visualizador',
};

// Descripciones de roles
export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  [ROLES.SUPERADMIN]: 'Control total del sistema - Acceso global a todos los grupos',
  [ROLES.ADMIN]: 'Control total del sistema - Limitado a sus grupos',
  [ROLES.RESPONSABLE]: 'Aprueba y rechaza facturas asignadas',
  [ROLES.CONTADOR]: 'Valida y devuelve facturas para corrección',
  [ROLES.VIEWER]: 'Solo visualización, sin acciones',
};

// Permisos por rol
export const ROLE_PERMISSIONS = {
  [ROLES.SUPERADMIN]: {
    canCreate: false,              // NO puede crear facturas (Separation of Duties)
    canEdit: false,                // NO puede editar facturas (Separation of Duties)
    canDelete: false,              // NO puede eliminar facturas (Separation of Duties)
    canApprove: false,             // NO puede aprobar facturas (Separation of Duties)
    canReject: false,              // NO puede rechazar facturas (Separation of Duties)
    canViewAll: true,              // Puede ver todas las facturas (solo lectura)
    canManageUsers: true,
    canManageProviders: true,
    canConfigureEmail: true,
    canViewUsers: true,
    canViewProviders: true,
    canViewFullUserData: true,
    canViewPDF: true,
    canDevolverFactura: false,
    // FASE 2 - Permisos de pagos (SuperAdmin: acceso total global)
    canViewPayments: true,
    canRegisterPayment: true,
    canViewPaymentHistory: true,
    canEditPayment: true,
    canDeletePayment: true,
  },
  [ROLES.ADMIN]: {
    canCreate: true,
    canEdit: true,
    canDelete: true,
    canApprove: true,
    canReject: true,
    canViewAll: true,
    canManageUsers: true,
    canManageProviders: true,
    canConfigureEmail: true,
    canViewUsers: true,
    canViewProviders: true,
    canViewFullUserData: true,
    canViewPDF: true,               //  NUEVO: Puede ver PDFs
    canDevolverFactura: false,      //  NUEVO: NO devuelve facturas (no es su rol)
    // FASE 2 - Permisos de pagos (Admin: acceso total)
    canViewPayments: true,
    canRegisterPayment: true,
    canViewPaymentHistory: true,
    canEditPayment: true,
    canDeletePayment: true,
  },
  [ROLES.RESPONSABLE]: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    canApprove: true,
    canReject: true,
    canViewAll: false,
    canManageUsers: false,
    canManageProviders: false,
    canConfigureEmail: false,
    canViewUsers: false,
    canViewProviders: false,
    canViewFullUserData: false,
    canViewPDF: true,               // NUEVO: Puede ver PDFs
    canDevolverFactura: false,      // NUEVO: NO devuelve facturas
    // FASE 2 - Permisos de pagos (Responsable: NO tiene acceso)
    canViewPayments: false,
    canRegisterPayment: false,
    canViewPaymentHistory: false,
    canEditPayment: false,
    canDeletePayment: false,
  },
  [ROLES.CONTADOR]: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    canApprove: false,              // NO puede aprobar (solo contabilidad)
    canReject: false,               // NO puede rechazar (solo contabilidad)
    canViewAll: true,               // Puede ver todas las facturas
    canManageUsers: false,
    canManageProviders: false,
    canConfigureEmail: false,
    canViewUsers: true,             // Puede ver usuarios
    canViewProviders: true,         // Puede ver proveedores
    canViewFullUserData: false,     // NO ve datos sensibles completos
    canViewPDF: true,               //  NUEVO: Puede ver PDFs (esencial para su trabajo)
    canDevolverFactura: true,       //  NUEVO: Puede devolver facturas al proveedor
    // FASE 2 - Permisos de pagos (Contador: acceso total para registrar)
    canViewPayments: true,
    canRegisterPayment: true,
    canViewPaymentHistory: true,
    canEditPayment: false,
    canDeletePayment: false,
  },
  [ROLES.VIEWER]: {
    canCreate: false,
    canEdit: false,
    canDelete: false,
    canApprove: false,
    canReject: false,
    canViewAll: true,
    canManageUsers: false,
    canManageProviders: false,
    canConfigureEmail: false,
    canViewUsers: true,             //  NUEVO: Puede ver usuarios
    canViewProviders: true,         //  NUEVO: Puede ver proveedores
    canViewFullUserData: false,     //  NUEVO: NO ve datos sensibles completos
    canViewPDF: true,               //  NUEVO: Puede ver PDFs
    canDevolverFactura: false,      //  NUEVO: NO devuelve facturas
    // FASE 2 - Permisos de pagos (Viewer: NO tiene acceso)
    canViewPayments: false,
    canRegisterPayment: false,
    canViewPaymentHistory: false,
    canEditPayment: false,
    canDeletePayment: false,
  },
};

/**
 * Obtiene la etiqueta traducida de un rol
 */
export function getRoleLabel(role: string): string {
  return ROLE_LABELS[role as Role] || role;
}

/**
 * Obtiene la descripción de un rol
 */
export function getRoleDescription(role: string): string {
  return ROLE_DESCRIPTIONS[role as Role] || '';
}

/**
 * Verifica si un rol tiene un permiso específico
 */
export function hasPermission(role: string, permission: keyof typeof ROLE_PERMISSIONS.admin): boolean {
  const permissions = ROLE_PERMISSIONS[role as Role];
  return permissions ? permissions[permission] : false;
}
