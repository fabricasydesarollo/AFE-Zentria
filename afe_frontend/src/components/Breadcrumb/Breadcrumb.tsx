/**
 * Breadcrumb Component
 *
 * Componente accesible de breadcrumbs (migaja de pan) que muestra
 * la ruta de navegación actual dentro del sistema.
 *
 * Características:
 * - Completamente accesible (WCAG 2.1 AA)
 * - Responsive design
 * - Soporta rutas dinámicas
 * - Último elemento NO clicable (aria-current="page")
 * - Separadores semánticos
 * - Memoizado para rendimiento
 *
 * @author  Backend/Frontend
 * @version 1.0.0
 */

import { memo } from 'react';
import { Link } from 'react-router-dom';
import {
  Box,
  Breadcrumbs,
  Typography,
  useTheme,
  useMediaQuery,
  Stack,
  Skeleton
} from '@mui/material';
import {
  NavigateNext as ChevronIcon,
  Home as HomeIcon,
  Email as EmailIcon
} from '@mui/icons-material';
import { useBreadcrumb } from '../../hooks/useBreadcrumb';
import { BreadcrumbItem } from '../../config/breadcrumb.config';

interface BreadcrumbProps {
  /**
   * Mostrar el icono de inicio
   * @default true
   */
  showHomeIcon?: boolean;

  /**
   * Máximo de caracteres antes de truncar
   * @default 30
   */
  maxLabelLength?: number;

  /**
   * Callback cuando se hace clic en una migaja
   */
  onNavigate?: (path: string) => void;
}

/**
 * Componente que renderiza un item del breadcrumb
 */
const BreadcrumbItemComponent = memo<{
  item: BreadcrumbItem;
  isLast: boolean;
  maxLabelLength: number;
  onNavigate?: (path: string) => void;
}>(({ item, isLast, maxLabelLength, onNavigate }) => {
  const theme = useTheme();

  // Truncar label si es muy largo
  const displayLabel =
    item.label.length > maxLabelLength
      ? `${item.label.substring(0, maxLabelLength)}...`
      : item.label;

  if (isLast) {
    // Último elemento: no clicable, con aria-current
    return (
      <Typography
        color="textPrimary"
        sx={{
          fontWeight: 600,
          fontSize: { xs: '0.875rem', sm: '1rem' },
          display: 'flex',
          alignItems: 'center',
          gap: 0.5
        }}
        aria-current="page"
      >
        {item.icon === 'email' && (
          <EmailIcon
            sx={{
              fontSize: '1.2em',
              color: theme.palette.primary.main
            }}
          />
        )}
        {displayLabel}
      </Typography>
    );
  }

  // Elementos intermedios: clicables
  return (
    <Box
      component={Link}
      to={item.path}
      onClick={() => onNavigate?.(item.path)}
      sx={{
        color: theme.palette.primary.main,
        textDecoration: 'none',
        fontSize: '0.875rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.25rem',
        transition: 'color 0.2s',
        cursor: 'pointer',
        '&:hover': {
          color: theme.palette.primary.dark,
          textDecoration: 'underline'
        }
      }}
      aria-label={`Navegar a ${item.label}`}
    >
      {item.icon === 'email' && (
        <EmailIcon
          sx={{
            fontSize: '1rem',
            color: 'inherit'
          }}
        />
      )}
      {displayLabel}
    </Box>
  );
});

BreadcrumbItemComponent.displayName = 'BreadcrumbItemComponent';

/**
 * Componente principal de Breadcrumb
 */
const BreadcrumbComponent = memo<BreadcrumbProps>(
  ({
    showHomeIcon = true,
    maxLabelLength = 30,
    onNavigate
  }) => {
    const { breadcrumbs, isLoading } = useBreadcrumb();
    const theme = useTheme();
    const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

    // Estado de carga
    if (isLoading) {
      return (
        <Box sx={{ px: 2, py: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Skeleton variant="text" width={100} height={24} />
            <Skeleton variant="text" width={20} height={24} />
            <Skeleton variant="text" width={150} height={24} />
          </Stack>
        </Box>
      );
    }

    // Sin breadcrumbs
    if (breadcrumbs.length === 0) {
      return null;
    }

    // En mobile: mostrar solo el último o los últimos 2 items
    const displayedBreadcrumbs = isMobile
      ? breadcrumbs.slice(Math.max(0, breadcrumbs.length - 2))
      : breadcrumbs;

    return (
      <nav aria-label="breadcrumb" role="navigation">
        <Box
          sx={{
            px: { xs: 1, sm: 2 },
            py: 1.5,
            bgcolor: 'background.paper',
            borderBottom: `1px solid ${theme.palette.divider}`,
            display: 'flex',
            alignItems: 'center',
            gap: 1
          }}
        >
          {/* Icono de inicio */}
          {showHomeIcon && (
            <Link
              to="/dashboard"
              onClick={() => onNavigate?.('/dashboard')}
              style={{
                display: 'flex',
                alignItems: 'center',
                color: theme.palette.primary.main,
                textDecoration: 'none',
                transition: 'color 0.2s'
              }}
              aria-label="Ir a Dashboard"
              title="Dashboard"
            >
              <HomeIcon
                sx={{
                  fontSize: '1.3em',
                  color: 'inherit',
                  '&:hover': {
                    color: theme.palette.primary.dark
                  }
                }}
              />
            </Link>
          )}

          {/* Separator si hay icono */}
          {showHomeIcon && displayedBreadcrumbs.length > 0 && (
            <ChevronIcon
              sx={{
                fontSize: '1.2em',
                color: theme.palette.text.secondary,
                mx: 0.5
              }}
              aria-hidden="true"
            />
          )}

          {/* Breadcrumbs */}
          <Breadcrumbs
            separator={
              <ChevronIcon
                sx={{
                  fontSize: '1.2em',
                  color: theme.palette.text.secondary
                }}
              />
            }
            sx={{
              '& ol': {
                margin: 0,
                padding: 0
              },
              '& li': {
                display: 'flex',
                alignItems: 'center'
              }
            }}
            aria-label="Ruta actual"
          >
            {displayedBreadcrumbs.map((item, index) => (
              <BreadcrumbItemComponent
                key={item.path}
                item={item}
                isLast={index === displayedBreadcrumbs.length - 1}
                maxLabelLength={maxLabelLength}
                onNavigate={onNavigate}
              />
            ))}
          </Breadcrumbs>
        </Box>
      </nav>
    );
  }
);

BreadcrumbComponent.displayName = 'Breadcrumb';

export default BreadcrumbComponent;
