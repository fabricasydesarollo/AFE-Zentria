import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import facturasReducer from '../features/facturas/facturasSlice';
import proveedoresReducer from '../features/proveedores/proveedoresSlice';
import emailConfigReducer from '../features/email-config/emailConfigSlice';
import gruposReducer from '../features/grupos/gruposSlice';

/**
 * Redux Store Configuration
 * Store centralizado para el estado global de la aplicación
 *
 * ENHANCED 2025-12-04: Agregado gruposReducer para multi-tenancy
 */

export const store = configureStore({
  reducer: {
    auth: authReducer,
    facturas: facturasReducer,
    proveedores: proveedoresReducer,
    emailConfig: emailConfigReducer,
    grupos: gruposReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignorar estas rutas para verificación de serialización
        ignoredActions: ['facturas/setFacturas'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
