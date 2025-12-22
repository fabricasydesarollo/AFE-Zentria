/**
 * Tab de Vista por Responsable
 * Muestra proveedores (NITs) asignados a un responsable seleccionado
 *
 * @version 2.0 - Migrado a asignacion-nit
 * @date 2025-10-19
 */
import React, { useState } from 'react';
import {
  Box,
  Card,
  Grid,
  Button,
  Autocomplete,
  TextField,
  Typography,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
} from '@mui/material';
import { getAsignacionesPorResponsable, getResponsables } from '../../../services/asignacionNit.api';

interface Responsable {
  id: number;
  usuario: string;
  nombre: string;
}

function PorResponsableTab() {
  const [responsables, setResponsables] = useState<Responsable[]>([]);
  const [selectedResponsableId, setSelectedResponsableId] = useState<number | null>(null);
  const [viewData, setViewData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    loadResponsables();
  }, []);

  const loadResponsables = async () => {
    try {
      const data = await getResponsables({ activo: true });
      setResponsables(data);
    } catch (error) {
      // Error al cargar responsables
    }
  };

  const handleLoadData = async () => {
    if (!selectedResponsableId) return;

    setLoading(true);
    try {
      const data = await getAsignacionesPorResponsable(selectedResponsableId, true);

      // Validar que data y asignaciones existan
      if (!data || !data.asignaciones) {
        setViewData(null);
        setLoading(false);
        return;
      }

      // Transformar asignaciones a formato compatible con la vista
      const transformedData = {
        responsable_id: data.responsable_id,
        responsable: data.responsable,
        proveedores: data.asignaciones.map((asig) => ({
          asignacion_id: asig.id,
          nit: asig.nit,
          razon_social: asig.nombre_proveedor,
          area: asig.area,
          activo: asig.activo,
        })),
        total: data.total,
      };
      setViewData(transformedData);
    } catch (error: any) {
      // Error al cargar datos
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      <Card
        elevation={3}
        sx={{
          p: 4,
          borderRadius: 3,
          background: 'linear-gradient(to bottom, #ffffff 0%, #f8f9fa 100%)',
        }}
      >
        <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: 'primary.main' }}>
          Consultar por Responsable
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', maxWidth: 1400 }}>
          <Autocomplete
            options={responsables}
            getOptionLabel={(option) => `${option.nombre} (${option.usuario})`}
            value={responsables.find((r) => r.id === selectedResponsableId) || null}
            onChange={(_, newValue) => {
              setSelectedResponsableId(newValue?.id || null);
              setViewData(null);
            }}
            sx={{ flex: 1 }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Seleccionar Responsable"
                variant="outlined"
                fullWidth
                sx={{
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: 'white',
                    fontSize: '1.1rem',
                    '&:hover': {
                      backgroundColor: '#fafafa',
                    },
                  },
                  '& .MuiInputBase-input': {
                    fontSize: '1.1rem',
                    py: 2.5,
                  },
                  '& .MuiInputLabel-root': {
                    fontSize: '1.05rem',
                  },
                }}
              />
            )}
            componentsProps={{
              paper: {
                sx: {
                  mt: 1,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  '& .MuiAutocomplete-listbox': {
                    maxHeight: '450px',
                    '& .MuiAutocomplete-option': {
                      py: 3,
                      px: 4,
                      fontSize: '1.05rem',
                      minHeight: '70px',
                      '&:hover': {
                        backgroundColor: '#f5f5f5',
                      },
                      '&[aria-selected="true"]': {
                        backgroundColor: '#e8eaf6',
                        fontWeight: 500,
                        '&:hover': {
                          backgroundColor: '#d5d8ec',
                        },
                      },
                    },
                  },
                },
              },
            }}
          />
          <Button
            variant="contained"
            size="large"
            onClick={handleLoadData}
            disabled={!selectedResponsableId || loading}
            sx={{
              px: 4,
              py: 2.5,
              fontWeight: 600,
              textTransform: 'none',
              fontSize: '1.05rem',
              boxShadow: 2,
              minWidth: 220,
              height: '56px',
              flexShrink: 0,
              '&:hover': {
                boxShadow: 4,
              },
            }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Consultar Proveedores'}
          </Button>
        </Box>

        {viewData && (
          <Box mt={5}>
            <Divider sx={{ my: 3 }} />

            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Proveedores asignados a: {viewData.responsable.nombre}
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
                Total: <strong>{viewData.total}</strong> {viewData.total === 1 ? 'proveedor' : 'proveedores'}
              </Typography>
            </Box>

            <TableContainer
              sx={{
                mt: 3,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                backgroundColor: 'white',
                boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
              }}
            >
              <Table>
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem' }}>NIT</TableCell>
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem' }}>Razón Social</TableCell>
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem' }}>Área</TableCell>
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem', textAlign: 'center' }}>Estado</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {viewData.proveedores.map((prov: any) => (
                    <TableRow
                      key={prov.asignacion_id}
                      hover
                      sx={{
                        '&:hover': {
                          backgroundColor: '#f9fafb',
                        },
                      }}
                    >
                      <TableCell sx={{ py: 2.5, fontSize: '0.9rem', fontWeight: 500 }}>{prov.nit}</TableCell>
                      <TableCell sx={{ py: 2.5, fontSize: '0.9rem' }}>{prov.razon_social}</TableCell>
                      <TableCell sx={{ py: 2.5, fontSize: '0.9rem', color: 'text.secondary' }}>{prov.area || '-'}</TableCell>
                      <TableCell sx={{ py: 2.5, textAlign: 'center' }}>
                        <Chip
                          label={prov.activo ? 'Activo' : 'Inactivo'}
                          color={prov.activo ? 'success' : 'default'}
                          size="medium"
                          sx={{
                            fontWeight: 600,
                            minWidth: 90,
                          }}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </Card>
    </Box>
  );
}

export default PorResponsableTab;
