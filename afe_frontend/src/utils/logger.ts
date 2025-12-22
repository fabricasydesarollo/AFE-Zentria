/**
 * Logger utility para desarrollo y producción
 *
 * En desarrollo: muestra logs en consola
 * En producción: solo muestra errores críticos
 */

const isDevelopment = import.meta.env.DEV;

export const logger = {
  debug: (message: string, ...args: any[]) => {
    if (isDevelopment) {
      console.log(`[DEBUG] ${message}`, ...args);
    }
  },

  info: (message: string, ...args: any[]) => {
    if (isDevelopment) {
      console.info(`[INFO] ${message}`, ...args);
    }
  },

  warn: (message: string, ...args: any[]) => {
    console.warn(`[WARN] ${message}`, ...args);
  },

  error: (message: string, error?: any) => {
    console.error(`[ERROR] ${message}`, error);
    // Aquí podrías integrar un servicio de error tracking como Sentry
    // Sentry.captureException(error);
  },
};

export default logger;
