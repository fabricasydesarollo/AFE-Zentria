/**
 * ReadOnlyWrapper - HOC para modo solo lectura
 * Envuelve cualquier componente y oculta botones de acción para viewers
 *
 */

import React, { useEffect, useRef } from 'react';
import { Box, Alert } from '@mui/material';
import { Visibility } from '@mui/icons-material';
import { useAppSelector } from '../../app/hooks';
import { hasPermission } from '../../constants/roles';

interface ReadOnlyWrapperProps {
  children: React.ReactNode;
  requiredPermission: 'canManageUsers' | 'canManageProviders' | 'canConfigureEmail';
  showBanner?: boolean;
}

/**
 * Wrapper que desactiva interacciones para usuarios sin permisos
 */
export const ReadOnlyWrapper: React.FC<ReadOnlyWrapperProps> = ({
  children,
  requiredPermission,
  showBanner = true,
}) => {
  const user = useAppSelector((state) => state.auth.user);
  const hasPermissionToManage = hasPermission(user?.rol || '', requiredPermission);
  const containerRef = useRef<HTMLDivElement>(null);

  // Ocultar botones de acción usando JavaScript (más confiable que CSS)
  useEffect(() => {
    if (hasPermissionToManage || !containerRef.current) return;

    const hideActionButtons = () => {
      const container = containerRef.current;
      if (!container) return;

      // Buscar y ocultar botones por texto
      const buttons = container.querySelectorAll('button');
      buttons.forEach((button) => {
        const text = button.textContent?.toLowerCase() || '';
        const ariaLabel = button.getAttribute('aria-label')?.toLowerCase() || '';
        const title = button.getAttribute('title')?.toLowerCase() || '';

        // Lista de palabras clave que indican acciones de modificación
        const actionKeywords = [
          'nuevo', 'nueva', 'crear', 'editar', 'eliminar', 'agregar', 'añadir',
          'borrar', 'modificar', 'asignación', 'asignacion', 'masiva'
        ];

        // NO ocultar botones de visualización
        const viewKeywords = ['ver', 'detalle', 'actualizar', 'refresh', 'todo'];

        const hasActionKeyword = actionKeywords.some(keyword =>
          text.includes(keyword) || ariaLabel.includes(keyword) || title.includes(keyword)
        );

        const hasViewKeyword = viewKeywords.some(keyword =>
          text.includes(keyword) || ariaLabel.includes(keyword) || title.includes(keyword)
        );

        if (hasActionKeyword && !hasViewKeyword) {
          (button as HTMLElement).style.display = 'none';
        }
      });

      // Ocultar IconButtons con íconos de editar/eliminar
      const iconButtons = container.querySelectorAll('.MuiIconButton-root');
      iconButtons.forEach((iconButton) => {
        const title = iconButton.getAttribute('title')?.toLowerCase() || '';
        const ariaLabel = iconButton.getAttribute('aria-label')?.toLowerCase() || '';

        // Palabras clave para detectar acciones de modificación en iconos
        const iconActionKeywords = ['editar', 'eliminar', 'borrar', 'delete', 'remove', 'crear'];

        const hasActionIcon = iconActionKeywords.some(keyword =>
          title.includes(keyword) || ariaLabel.includes(keyword)
        );

        if (hasActionIcon) {
          (iconButton as HTMLElement).style.display = 'none';
        }

        // También ocultar por color (iconos rojos suelen ser eliminar)
        const svgElement = iconButton.querySelector('svg');
        if (svgElement) {
          const color = svgElement.getAttribute('color');
          // Buscar también en el path del SVG
          const pathElement = svgElement.querySelector('path');
          const fill = pathElement?.getAttribute('fill');

          if (color === 'error' || fill?.includes('error') ||
              iconButton.getAttribute('class')?.includes('error')) {
            (iconButton as HTMLElement).style.display = 'none';
          }
        }
      });

      // Ocultar columnas de tabla con header "Acciones"
      const tableHeaders = container.querySelectorAll('th');
      tableHeaders.forEach((header, index) => {
        const headerText = header.textContent?.toLowerCase() || '';
        if (headerText.includes('acciones')) {
          // Ocultar el header
          (header as HTMLElement).style.display = 'none';

          // Ocultar todas las celdas de esa columna
          const table = header.closest('table');
          if (table) {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach((row) => {
              const cells = row.querySelectorAll('td');
              if (cells[index]) {
                (cells[index] as HTMLElement).style.display = 'none';
              }
            });
          }
        }
      });
    };

    // Ejecutar al montar y cuando cambie el DOM
    hideActionButtons();
    const observer = new MutationObserver(hideActionButtons);
    observer.observe(containerRef.current, { childList: true, subtree: true });

    return () => observer.disconnect();
  }, [hasPermissionToManage]);

  // Si tiene permisos, renderizar normalmente
  if (hasPermissionToManage) {
    return <>{children}</>;
  }

  // Modo solo lectura para viewer
  return (
    <Box ref={containerRef}>
      {showBanner && (
        <Alert
          severity="info"
          icon={<Visibility />}
          sx={{ mb: 3 }}
        >
          <strong>Modo solo lectura</strong> - Puedes visualizar la información pero no realizar cambios.
        </Alert>
      )}

      {children}
    </Box>
  );
};

export default ReadOnlyWrapper;
