/**
 * Formatting utilities for Dashboard
 */

/**
 * Format currency amount with Colombian peso formatting
 */
export const formatCurrency = (amount: number | string | null | undefined): string => {
  // Convertir a número y manejar valores inválidos
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;

  if (numAmount === null || numAmount === undefined || isNaN(numAmount)) {
    return '$0.00';
  }

  return `$${numAmount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
};

/**
 * Format date to localized string
 */
export const formatDate = (dateString: string): string => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString();
};

/**
 * Extract date for input fields (YYYY-MM-DD format)
 */
export const extractDateForInput = (dateString?: string): string => {
  if (!dateString) return '';
  return dateString.split('T')[0];
};

/**
 * Get today's date in YYYY-MM-DD format
 */
export const getTodayDate = (): string => {
  return new Date().toISOString().split('T')[0];
};
