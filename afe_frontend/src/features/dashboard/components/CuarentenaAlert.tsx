/**
 * CuarentenaAlert - Professional quarantine management alert
 *
 * Displays quarantine information from the backend dashboard endpoint
 * Shows groups affected and allows quick navigation to assign responsibles
 *
 * Architecture: Multi-Tenant (2025-12-29)
 * Backend: GET /api/v1/dashboard/mes-actual → cuarentena object
 */

import { Alert, AlertTitle, Box, Button, Chip, Stack, Typography } from '@mui/material';
import { Warning as WarningIcon, Group as GroupIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { zentriaColors } from '../../../theme/colors';

interface CuarentenaGrupo {
  grupo_id: number;
  nombre_grupo: string;
  codigo_grupo: string;
  total_facturas: number;
  impacto_financiero: number;
  url_asignar_responsables: string;
}

interface CuarentenaInfo {
  total_facturas: number;
  total_grupos_afectados: number;
  impacto_financiero_total: number;
  grupos: CuarentenaGrupo[];
}

interface CuarentenaAlertProps {
  cuarentena?: CuarentenaInfo | null;
}

export function CuarentenaAlert({ cuarentena }: CuarentenaAlertProps) {
  const navigate = useNavigate();

  // No mostrar si no hay datos o no hay facturas
  if (!cuarentena || cuarentena.total_facturas === 0) {
    return null;
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <Alert
      severity="warning"
      icon={<WarningIcon />}
      sx={{
        mb: 3,
        borderLeft: `4px solid ${zentriaColors.naranja.main}`,
        backgroundColor: 'rgba(255, 152, 0, 0.05)',
        '& .MuiAlert-icon': {
          color: zentriaColors.naranja.main,
        },
      }}
    >
      <AlertTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Typography variant="h6" component="span" fontWeight="bold">
            {cuarentena.total_facturas} factura{cuarentena.total_facturas !== 1 ? 's' : ''} en cuarentena
          </Typography>
          <Chip
            label={`${cuarentena.total_grupos_afectados} grupo${cuarentena.total_grupos_afectados !== 1 ? 's' : ''} afectado${cuarentena.total_grupos_afectados !== 1 ? 's' : ''}`}
            size="small"
            color="warning"
            sx={{ ml: 1 }}
          />
        </Box>
      </AlertTitle>

      <Typography variant="body2" sx={{ mb: 2 }}>
        Estas facturas no tienen responsables asignados.
        Asigna responsables a cada grupo para procesarlas automáticamente.
      </Typography>

      <Typography variant="body2" fontWeight="bold" sx={{ mb: 2 }}>
        Impacto financiero total: {formatCurrency(cuarentena.impacto_financiero_total)}
      </Typography>

      {/* Lista de grupos afectados */}
      <Stack spacing={1.5} sx={{ mt: 2 }}>
        {cuarentena.grupos.slice(0, 5).map((grupo) => (
          <Box
            key={grupo.grupo_id}
            sx={{
              p: 2,
              bgcolor: 'background.paper',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'divider',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
            }}
          >
            <Box flex={1}>
              <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                <GroupIcon fontSize="small" color="action" />
                <Typography variant="subtitle2" fontWeight="bold">
                  {grupo.nombre_grupo}
                </Typography>
                <Chip label={grupo.codigo_grupo} size="small" variant="outlined" />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {grupo.total_facturas} factura{grupo.total_facturas !== 1 ? 's' : ''} · {formatCurrency(grupo.impacto_financiero)}
              </Typography>
            </Box>

            <Button
              variant="outlined"
              size="small"
              startIcon={<GroupIcon />}
              onClick={() => navigate(grupo.url_asignar_responsables)}
              sx={{
                whiteSpace: 'nowrap',
                borderColor: zentriaColors.violeta.main,
                color: zentriaColors.violeta.main,
                '&:hover': {
                  borderColor: zentriaColors.violeta.main,
                  backgroundColor: `${zentriaColors.violeta.main}10`,
                },
              }}
            >
              Asignar Responsables
            </Button>
          </Box>
        ))}

        {cuarentena.grupos.length > 5 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
            ... y {cuarentena.grupos.length - 5} grupo{cuarentena.grupos.length - 5 !== 1 ? 's' : ''} más
          </Typography>
        )}
      </Stack>

      {/* Nota importante */}
      <Box
        sx={{
          mt: 3,
          p: 2,
          bgcolor: 'rgba(255, 152, 0, 0.05)',
          borderRadius: 1,
          border: '1px dashed',
          borderColor: zentriaColors.naranja.main,
        }}
      >
        <Typography variant="caption" display="block" fontWeight="bold" gutterBottom>
          ℹ️ Importante:
        </Typography>
        <Typography variant="caption" display="block">
          • Las facturas en cuarentena son <strong>históricas</strong> (ciclo anterior)
        </Typography>
        <Typography variant="caption" display="block">
          • Al asignar responsables, se crearán workflows <strong>sin notificaciones</strong>
        </Typography>
        <Typography variant="caption" display="block">
          • Facturas <strong>nuevas</strong> (desde ahora) <strong>SÍ</strong> generarán notificaciones
        </Typography>
      </Box>
    </Alert>
  );
}
