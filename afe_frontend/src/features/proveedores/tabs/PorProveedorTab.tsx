/**
 * Tab de Vista por Proveedor
 * Muestra responsables asignados a un proveedor seleccionado (busca por NIT)
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
import { useAppSelector } from '../../../app/hooks';
import { selectProveedoresList } from '../proveedoresSlice';
import { getAsignacionesNit } from '../../../services/asignacionNit.api';

function PorProveedorTab() {
  const proveedores = useAppSelector(selectProveedoresList);
  const [selectedProveedorId, setSelectedProveedorId] = useState<number | null>(null);
  const [viewData, setViewData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleLoadData = async () => {
    if (!selectedProveedorId) return;

    setLoading(true);
    try {
      // Buscar proveedor seleccionado para obtener su NIT
      const proveedor = proveedores.find((p) => p.id === selectedProveedorId);
      if (!proveedor) {
        setLoading(false);
        return;
      }

      // Buscar asignaciones por NIT
      const asignaciones = await getAsignacionesNit({
        nit: proveedor.nit,
        activo: true,
      });

      // Transformar respuesta al formato esperado por la vista
      const transformedData = {
        proveedor_id: proveedor.id,
        proveedor: {
          nit: proveedor.nit,
          razon_social: proveedor.razon_social,
        },
        responsables: asignaciones.map((asig) => ({
          asignacion_id: asig.id,
          responsable_id: asig.responsable_id,
          usuario: asig.responsable?.usuario || '',
          nombre: asig.responsable?.nombre || '',
          email: asig.responsable?.email || '',
          activo: asig.activo,
        })),
        total: asignaciones.length,
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
          Consultar por Proveedor
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', maxWidth: 1400 }}>
          <Autocomplete
            options={proveedores}
            getOptionLabel={(option) => `${option.razon_social} (${option.nit})`}
            value={proveedores.find((p) => p.id === selectedProveedorId) || null}
            onChange={(_, newValue) => {
              setSelectedProveedorId(newValue?.id || null);
              setViewData(null);
            }}
            sx={{ flex: 1 }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Seleccionar Proveedor"
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
            disabled={!selectedProveedorId || loading}
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
            {loading ? <CircularProgress size={24} color="inherit" /> : 'Consultar Responsables'}
          </Button>
        </Box>

        {viewData && (
          <Box mt={5}>
            <Divider sx={{ my: 3 }} />

            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Responsables asignados a: {viewData.proveedor.razon_social}
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
                NIT: <strong>{viewData.proveedor.nit}</strong> | Total: <strong>{viewData.total}</strong> {viewData.total === 1 ? 'responsable' : 'responsables'}
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
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem' }}>Usuario</TableCell>
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem' }}>Nombre</TableCell>
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem' }}>Email</TableCell>
                    <TableCell sx={{ fontWeight: 700, py: 2, fontSize: '0.95rem', textAlign: 'center' }}>Estado</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {viewData.responsables.map((resp: any) => (
                    <TableRow
                      key={resp.asignacion_id}
                      hover
                      sx={{
                        '&:hover': {
                          backgroundColor: '#f9fafb',
                        },
                      }}
                    >
                      <TableCell sx={{ py: 2.5, fontSize: '0.9rem', fontWeight: 500 }}>{resp.usuario}</TableCell>
                      <TableCell sx={{ py: 2.5, fontSize: '0.9rem' }}>{resp.nombre}</TableCell>
                      <TableCell sx={{ py: 2.5, fontSize: '0.9rem', color: 'text.secondary' }}>{resp.email}</TableCell>
                      <TableCell sx={{ py: 2.5, textAlign: 'center' }}>
                        <Chip
                          label={resp.activo ? 'Activo' : 'Inactivo'}
                          color={resp.activo ? 'success' : 'default'}
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

export default PorProveedorTab;
