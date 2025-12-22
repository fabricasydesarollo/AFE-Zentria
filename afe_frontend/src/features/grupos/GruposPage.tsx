import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  People as PeopleIcon,
  AccountTree as TreeIcon,
} from '@mui/icons-material';
import gruposService from '../../services/grupos.api';
import { Grupo } from '../../types/grupo.types';
import { zentriaColors } from '../../theme/colors';
import GrupoFormModal from './components/GrupoFormModal';
import GrupoUsuariosModal from './components/GrupoUsuariosModal';

/**
 * Página principal de gestión de Grupos (SuperAdmin)
 * Permite CRUD completo de grupos y asignación de usuarios
 */
export default function GruposPage() {
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modales
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [usuariosModalOpen, setUsuariosModalOpen] = useState(false);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<Grupo | null>(null);

  // Cargar grupos al montar componente
  useEffect(() => {
    cargarGrupos();
  }, []);

  const cargarGrupos = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await gruposService.listarGrupos();
      setGrupos(response.grupos);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar grupos');
    } finally {
      setLoading(false);
    }
  };

  const handleCrear = () => {
    setGrupoSeleccionado(null);
    setFormModalOpen(true);
  };

  const handleEditar = (grupo: Grupo) => {
    setGrupoSeleccionado(grupo);
    setFormModalOpen(true);
  };

  const handleEliminar = async (id: number) => {
    if (!confirm('¿Está seguro de eliminar este grupo? Esta acción no se puede deshacer.')) {
      return;
    }

    try {
      await gruposService.eliminarGrupo(id);
      await cargarGrupos();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al eliminar grupo');
    }
  };

  const handleAsignarUsuarios = (grupo: Grupo) => {
    setGrupoSeleccionado(grupo);
    setUsuariosModalOpen(true);
  };

  const handleFormSuccess = () => {
    setFormModalOpen(false);
    cargarGrupos();
  };

  const handleUsuariosSuccess = () => {
    setUsuariosModalOpen(false);
    cargarGrupos();
  };

  const getNivelColor = (nivel: number) => {
    // Usar gradaciones de violeta (color corporativo primario)
    switch (nivel) {
      case 0: return zentriaColors.violeta.dark;      // Corporativo - más oscuro
      case 1: return zentriaColors.violeta.main;      // Sede - principal
      case 2: return zentriaColors.violeta.light;     // Sub-sede - más claro
      default: return zentriaColors.violeta.main;
    }
  };

  const getNivelLabel = (nivel: number) => {
    switch (nivel) {
      case 0: return 'Corporativo';
      case 1: return 'Sede';
      case 2: return 'Sub-sede';
      default: return `Nivel ${nivel}`;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, color: zentriaColors.violeta.main, mb: 0.5 }}>
            Gestión de Grupos y Sedes
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Administración completa de la estructura organizacional multi-tenant
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCrear}
          sx={{
            background: `linear-gradient(135deg, ${zentriaColors.violeta.main} 0%, ${zentriaColors.naranja.main} 100%)`,
            '&:hover': {
              background: `linear-gradient(135deg, ${zentriaColors.violeta.dark} 0%, ${zentriaColors.naranja.dark} 100%)`,
            },
          }}
        >
          Crear Grupo
        </Button>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Tabla de Grupos */}
      <TableContainer component={Paper} sx={{ boxShadow: 3 }}>
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: zentriaColors.violeta.main }}>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Código</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Nombre</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Nivel</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Grupo Padre</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }} align="center">Equipo</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }}>Estado</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 700 }} align="center">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {grupos.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 8 }}>
                  <TreeIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No hay grupos creados
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Comienza creando tu primer grupo corporativo
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              grupos.map((grupo) => (
                <TableRow
                  key={grupo.id}
                  sx={{
                    '&:hover': { bgcolor: `${zentriaColors.violeta.main}10` },
                    transition: 'background-color 0.2s',
                  }}
                >
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                      {grupo.codigo_corto}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {grupo.nombre}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getNivelLabel(grupo.nivel)}
                      size="small"
                      sx={{
                        bgcolor: `${getNivelColor(grupo.nivel)}20`,
                        color: getNivelColor(grupo.nivel),
                        fontWeight: 600,
                        height: 28,
                        minWidth: 100,
                        '& .MuiChip-label': {
                          px: 2,
                        },
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {grupo.parent?.nombre || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<PeopleIcon />}
                      onClick={() => handleAsignarUsuarios(grupo)}
                      sx={{
                        borderColor: zentriaColors.violeta.main,
                        color: zentriaColors.violeta.main,
                        fontWeight: 600,
                        borderRadius: 2,
                        px: 2,
                        '&:hover': {
                          borderColor: zentriaColors.violeta.dark,
                          bgcolor: `${zentriaColors.violeta.main}10`,
                        },
                      }}
                    >
                      Gestionar Equipo
                    </Button>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={grupo.activo ? 'Activo' : 'Inactivo'}
                      size="small"
                      color={grupo.activo ? 'success' : 'default'}
                      sx={{
                        fontWeight: 600,
                        height: 28,
                        minWidth: 100,
                        '& .MuiChip-label': {
                          px: 2,
                        },
                      }}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                      <Tooltip title="Editar grupo">
                        <IconButton
                          size="small"
                          onClick={() => handleEditar(grupo)}
                          sx={{ color: zentriaColors.naranja.main }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Eliminar grupo">
                        <IconButton
                          size="small"
                          onClick={() => handleEliminar(grupo.id)}
                          sx={{ color: zentriaColors.naranja.dark }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Modales */}
      <GrupoFormModal
        open={formModalOpen}
        onClose={() => setFormModalOpen(false)}
        onSuccess={handleFormSuccess}
        grupo={grupoSeleccionado}
      />

      <GrupoUsuariosModal
        open={usuariosModalOpen}
        onClose={() => setUsuariosModalOpen(false)}
        onSuccess={handleUsuariosSuccess}
        grupo={grupoSeleccionado}
      />
    </Box>
  );
}
