/**
 * Filter and search bar component for Dashboard
 */

import {
  Card,
  CardContent,
  Grid,
  TextField,
  InputAdornment,
  FormControl,
  Select,
  MenuItem,
  Button,
  Divider,
} from '@mui/material';
import { Search, Download } from '@mui/icons-material';
import { zentriaColors } from '../../../theme/colors';
import type { EstadoFactura, VistaFacturas } from '../types';
import { ESTADO_LABELS } from '../constants';

interface FilterBarProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  filterEstado: EstadoFactura | 'todos';
  onFilterEstadoChange: (value: EstadoFactura | 'todos') => void;
  vistaFacturas?: VistaFacturas;
  onVistaFacturasChange?: (value: VistaFacturas) => void;
  totalTodasFacturas?: number;
  totalAsignadas?: number;
  onExport: () => void;
  isAdmin?: boolean;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchTerm,
  onSearchChange,
  filterEstado,
  onFilterEstadoChange,
  vistaFacturas,
  onVistaFacturasChange,
  totalTodasFacturas,
  totalAsignadas,
  onExport,
  isAdmin = false,
}) => {
  return (
    <Card sx={{ mb: 3, boxShadow: '0 2px 12px rgba(0,0,0,0.08)', borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Grid container spacing={3}>
          {/* Search Field */}
          <Grid size={{ xs: 12, md: 7 }}>
            <TextField
              fullWidth
              placeholder="Buscar factura..."
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              sx={{
                '& .MuiOutlinedInput-root': {
                  height: 56,
                  backgroundColor: '#ffffff',
                  border: '2px solid #e9ecef',
                  borderRadius: '12px',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    border: `2px solid ${zentriaColors.violeta.main}40`,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                  },
                  '&.Mui-focused': {
                    border: `2px solid ${zentriaColors.violeta.main}`,
                    boxShadow: `0 0 0 3px ${zentriaColors.violeta.main}20`,
                  },
                  '& fieldset': {
                    border: 'none',
                  },
                },
                '& .MuiInputBase-input': {
                  fontWeight: 500,
                  color: '#2d3748',
                  '&::placeholder': {
                    color: '#a0aec0',
                    opacity: 1,
                  },
                },
              }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search sx={{ color: zentriaColors.violeta.main, fontSize: 24 }} />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>

          {/* Estado Filter */}
          <Grid size={{ xs: 12, md: 5 }}>
            <FormControl fullWidth>
              <Select
                value={filterEstado}
                onChange={(e) => onFilterEstadoChange(e.target.value as EstadoFactura | 'todos')}
                displayEmpty
                sx={{
                  height: 56,
                  backgroundColor: '#ffffff',
                  border: '2px solid #e9ecef',
                  borderRadius: '12px',
                  fontWeight: 600,
                  transition: 'all 0.3s ease',
                  '& fieldset': {
                    border: 'none',
                  },
                  '&:hover': {
                    border: `2px solid ${zentriaColors.violeta.main}40`,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                  },
                  '&.Mui-focused': {
                    border: `2px solid ${zentriaColors.violeta.main}`,
                    boxShadow: `0 0 0 3px ${zentriaColors.violeta.main}20`,
                  },
                }}
              >
                <MenuItem value="todos" sx={{ fontWeight: 600 }}>
                  {ESTADO_LABELS.todos}
                </MenuItem>
                <MenuItem value="en_revision" sx={{ fontWeight: 600 }}>
                  {ESTADO_LABELS.en_revision}
                </MenuItem>
                <MenuItem value="aprobada" sx={{ fontWeight: 600 }}>
                  {ESTADO_LABELS.aprobada}
                </MenuItem>
                <MenuItem value="aprobada_auto" sx={{ fontWeight: 600 }}>
                  {ESTADO_LABELS.aprobada_auto}
                </MenuItem>
                <MenuItem value="rechazada" sx={{ fontWeight: 600 }}>
                  {ESTADO_LABELS.rechazada}
                </MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {/* Admin Vista Buttons */}
          {isAdmin && onVistaFacturasChange && vistaFacturas && (
            <>
              <Grid size={{ xs: 12 }}>
                <Divider sx={{ my: 1 }} />
              </Grid>

              <Grid size={{ xs: 12, md: 5 }}>
                <Button
                  fullWidth
                  variant={vistaFacturas === 'todas' ? 'contained' : 'outlined'}
                  onClick={() => onVistaFacturasChange('todas')}
                  sx={{
                    height: 56,
                    textTransform: 'none',
                    fontWeight: 700,
                    borderRadius: '12px',
                    border: `2px solid ${zentriaColors.violeta.main}`,
                    backgroundColor: vistaFacturas === 'todas' ? zentriaColors.violeta.main : 'transparent',
                    color: vistaFacturas === 'todas' ? 'white' : zentriaColors.violeta.main,
                    boxShadow: vistaFacturas === 'todas' ? '0 4px 12px rgba(138, 43, 226, 0.3)' : 'none',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      backgroundColor: vistaFacturas === 'todas'
                        ? zentriaColors.violeta.dark
                        : `${zentriaColors.violeta.main}15`,
                      border: `2px solid ${zentriaColors.violeta.dark}`,
                      boxShadow: '0 4px 12px rgba(138, 43, 226, 0.3)',
                      transform: 'translateY(-2px)',
                    },
                  }}
                >
                  Todas las Facturas ({totalTodasFacturas})
                </Button>
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <Button
                  fullWidth
                  variant={vistaFacturas === 'asignadas' ? 'contained' : 'outlined'}
                  onClick={() => onVistaFacturasChange('asignadas')}
                  sx={{
                    height: 56,
                    textTransform: 'none',
                    fontWeight: 700,
                    borderRadius: '12px',
                    border: `2px solid ${zentriaColors.violeta.main}`,
                    backgroundColor: vistaFacturas === 'asignadas' ? zentriaColors.violeta.main : 'transparent',
                    color: vistaFacturas === 'asignadas' ? 'white' : zentriaColors.violeta.main,
                    boxShadow: vistaFacturas === 'asignadas' ? '0 4px 12px rgba(138, 43, 226, 0.3)' : 'none',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      backgroundColor: vistaFacturas === 'asignadas'
                        ? zentriaColors.violeta.dark
                        : `${zentriaColors.violeta.main}15`,
                      border: `2px solid ${zentriaColors.violeta.dark}`,
                      boxShadow: '0 4px 12px rgba(138, 43, 226, 0.3)',
                      transform: 'translateY(-2px)',
                    },
                  }}
                >
                  Facturas Asignadas ({totalAsignadas})
                </Button>
              </Grid>

              <Grid size={{ xs: 12, md: 3 }}>
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<Download />}
                  onClick={onExport}
                  sx={{
                    height: 56,
                    borderRadius: '12px',
                    border: `2px solid ${zentriaColors.verde.main}`,
                    color: zentriaColors.verde.main,
                    fontWeight: 700,
                    textTransform: 'none',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      border: `2px solid ${zentriaColors.verde.dark}`,
                      backgroundColor: `${zentriaColors.verde.main}15`,
                      boxShadow: '0 4px 12px rgba(34, 197, 94, 0.3)',
                      transform: 'translateY(-2px)',
                    },
                  }}
                >
                  Exportar
                </Button>
              </Grid>
            </>
          )}

          {/* Responsable Export Button */}
          {!isAdmin && (
            <Grid size={{ xs: 12 }}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<Download />}
                onClick={onExport}
                sx={{
                  height: 56,
                  borderRadius: '12px',
                  border: `2px solid ${zentriaColors.verde.main}`,
                  color: zentriaColors.verde.main,
                  fontWeight: 700,
                  textTransform: 'none',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    border: `2px solid ${zentriaColors.verde.dark}`,
                    backgroundColor: `${zentriaColors.verde.main}15`,
                    boxShadow: '0 4px 12px rgba(34, 197, 94, 0.3)',
                    transform: 'translateY(-2px)',
                  },
                }}
              >
                Exportar Datos
              </Button>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );
};
