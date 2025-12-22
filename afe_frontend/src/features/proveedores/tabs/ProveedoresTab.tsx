/**
 * Tab de Gestión de Proveedores
 * CRUD completo con búsqueda y paginación
 */
import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Tooltip,
  Chip,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Switch,
  FormControlLabel,
  CircularProgress,
  Alert,
  Typography,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  CheckCircle,
  Cancel,
} from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../../../app/hooks';
import {
  fetchProveedores,
  createProveedorThunk,
  updateProveedorThunk,
  deleteProveedorThunk,
  fetchAsignaciones,
  selectProveedoresList,
  selectProveedoresLoading,
} from '../proveedoresSlice';
import type { Proveedor, ProveedorCreate } from '../../../services/proveedores.api';

function ProveedoresTab() {
  const dispatch = useAppDispatch();

  const proveedores = useAppSelector(selectProveedoresList);
  const loading = useAppSelector(selectProveedoresLoading);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [selectedProveedor, setSelectedProveedor] = useState<Proveedor | null>(null);

  const [formData, setFormData] = useState<ProveedorCreate>({
    nit: '',
    razon_social: '',
    area: '',
    contacto_email: '',
    telefono: '',
    direccion: '',
    activo: true,
  });

  // Filtrado
  const filteredProveedores = proveedores.filter((p) =>
    p.nit.toLowerCase().includes(searchText.toLowerCase()) ||
    p.razon_social.toLowerCase().includes(searchText.toLowerCase()) ||
    p.area?.toLowerCase().includes(searchText.toLowerCase())
  );

  const paginatedProveedores = filteredProveedores.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleOpenDialog = (proveedor?: Proveedor) => {
    if (proveedor) {
      setEditMode(true);
      setSelectedProveedor(proveedor);
      setFormData({
        nit: proveedor.nit,
        razon_social: proveedor.razon_social,
        area: proveedor.area || '',
        contacto_email: proveedor.contacto_email || '',
        telefono: proveedor.telefono || '',
        direccion: proveedor.direccion || '',
        activo: proveedor.activo,
      });
    } else {
      setEditMode(false);
      setSelectedProveedor(null);
      setFormData({
        nit: '',
        razon_social: '',
        area: '',
        contacto_email: '',
        telefono: '',
        direccion: '',
        activo: true,
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (editMode && selectedProveedor) {
        await dispatch(
          updateProveedorThunk({ id: selectedProveedor.id, data: formData })
        ).unwrap();
        
        // ✅ SINCRONIZACIÓN: Recargar asignaciones después de editar proveedor
        // Si cambió razon_social, nombre_proveedor en AsignacionNit debe estar sincronizado
        dispatch(fetchAsignaciones({ skip: 0, limit: 1000 }));
      } else {
        await dispatch(createProveedorThunk(formData)).unwrap();
      }
      setDialogOpen(false);
      dispatch(fetchProveedores({ skip: 0, limit: 1000 }));
    } catch (error: any) {
      // Error al guardar proveedor
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedProveedor) return;

    try {
      await dispatch(deleteProveedorThunk(selectedProveedor.id)).unwrap();
      setDeleteDialogOpen(false);
      setSelectedProveedor(null);
    } catch (error: any) {
      // Error al eliminar proveedor
    }
  };

  return (
    <Box>
      {/* Búsqueda y acciones */}
      <Box display="flex" gap={2} mb={3}>
        <TextField
          fullWidth
          placeholder="Buscar por NIT, razón social o área..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
          sx={{ minWidth: 200 }}
        >
          Nuevo Proveedor
        </Button>
      </Box>

      {/* Tabla */}
      <Card>
        {loading ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>NIT</strong></TableCell>
                    <TableCell><strong>Razón Social</strong></TableCell>
                    <TableCell><strong>Área</strong></TableCell>
                    <TableCell><strong>Email</strong></TableCell>
                    <TableCell><strong>Teléfono</strong></TableCell>
                    <TableCell><strong>Estado</strong></TableCell>
                    <TableCell align="right"><strong>Acciones</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedProveedores.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Alert severity="info">No se encontraron proveedores</Alert>
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedProveedores.map((proveedor) => (
                      <TableRow key={proveedor.id} hover>
                        <TableCell>
                          <Typography fontWeight="bold">{proveedor.nit}</Typography>
                        </TableCell>
                        <TableCell>{proveedor.razon_social}</TableCell>
                        <TableCell>{proveedor.area || '-'}</TableCell>
                        <TableCell>{proveedor.contacto_email || '-'}</TableCell>
                        <TableCell>{proveedor.telefono || '-'}</TableCell>
                        <TableCell>
                          {proveedor.activo ? (
                            <Chip
                              label="Activo"
                              color="success"
                              size="small"
                              icon={<CheckCircle />}
                            />
                          ) : (
                            <Chip
                              label="Inactivo"
                              color="error"
                              size="small"
                              icon={<Cancel />}
                            />
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="Editar">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => handleOpenDialog(proveedor)}
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Eliminar">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => {
                                setSelectedProveedor(proveedor);
                                setDeleteDialogOpen(true);
                              }}
                            >
                              <Delete />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              rowsPerPageOptions={[5, 10, 25, 50]}
              component="div"
              count={filteredProveedores.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
              labelRowsPerPage="Filas por página:"
            />
          </>
        )}
      </Card>

      {/* Dialog Crear/Editar */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editMode ? 'Editar Proveedor' : 'Nuevo Proveedor'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                required
                label="NIT"
                value={formData.nit}
                onChange={(e) => setFormData({ ...formData, nit: e.target.value })}
                disabled={editMode}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                required
                label="Razón Social"
                value={formData.razon_social}
                onChange={(e) =>
                  setFormData({ ...formData, razon_social: e.target.value })
                }
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Área"
                value={formData.area}
                onChange={(e) => setFormData({ ...formData, area: e.target.value })}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={formData.contacto_email}
                onChange={(e) =>
                  setFormData({ ...formData, contacto_email: e.target.value })
                }
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Teléfono"
                value={formData.telefono}
                onChange={(e) =>
                  setFormData({ ...formData, telefono: e.target.value })
                }
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Dirección"
                value={formData.direccion}
                onChange={(e) =>
                  setFormData({ ...formData, direccion: e.target.value })
                }
              />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.activo}
                    onChange={(e) =>
                      setFormData({ ...formData, activo: e.target.checked })
                    }
                  />
                }
                label="Proveedor Activo"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!formData.nit || !formData.razon_social}
          >
            {editMode ? 'Actualizar' : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog Eliminar */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirmar Eliminación</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Esta acción no se puede deshacer
          </Alert>
          <Typography>
            ¿Está seguro de que desea eliminar el proveedor{' '}
            <strong>{selectedProveedor?.razon_social}</strong> (NIT:{' '}
            {selectedProveedor?.nit})?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancelar</Button>
          <Button variant="contained" color="error" onClick={handleDeleteConfirm}>
            Eliminar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ProveedoresTab;
