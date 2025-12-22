import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Alert,
  Box,
  Typography,
} from '@mui/material';
import gruposService from '../../../services/grupos.api';
import { Grupo, GrupoCreate, GrupoUpdate } from '../../../types/grupo.types';
import { zentriaColors } from '../../../theme/colors';

interface GrupoFormModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  grupo?: Grupo | null;
}

/**
 * Modal para crear o editar un grupo
 */
export default function GrupoFormModal({ open, onClose, onSuccess, grupo }: GrupoFormModalProps) {
  const isEdit = !!grupo;

  const [formData, setFormData] = useState({
    nombre: '',
    codigo_corto: '',
    nivel: 0,
    grupo_padre_id: undefined as number | undefined,
    activo: true,
  });

  const [gruposDisponibles, setGruposDisponibles] = useState<Grupo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cargar datos del grupo si estamos editando
  useEffect(() => {
    if (grupo) {
      setFormData({
        nombre: grupo.nombre,
        codigo_corto: grupo.codigo_corto,
        nivel: grupo.nivel,
        grupo_padre_id: grupo.grupo_padre_id || undefined,
        activo: grupo.activo,
      });
    } else {
      // Reset al crear nuevo
      setFormData({
        nombre: '',
        codigo_corto: '',
        nivel: 0,
        grupo_padre_id: undefined,
        activo: true,
      });
    }
  }, [grupo]);

  // Cargar grupos disponibles para seleccionar como padre
  useEffect(() => {
    if (open) {
      cargarGruposDisponibles();
    }
  }, [open]);

  const cargarGruposDisponibles = async () => {
    try {
      const response = await gruposService.listarGrupos({ activo: true });
      // Filtrar el grupo actual si estamos editando
      const gruposFiltrados = grupo
        ? response.grupos.filter((g) => g.id !== grupo.id)
        : response.grupos;
      setGruposDisponibles(gruposFiltrados);
    } catch (err: any) {
      console.error('Error al cargar grupos:', err);
    }
  };

  const handleChange = (field: string, value: any) => {
    setFormData({ ...formData, [field]: value });

    // Auto-ajustar nivel cuando se selecciona un padre
    if (field === 'grupo_padre_id' && value) {
      const padreSeleccionado = gruposDisponibles.find((g) => g.id === value);
      if (padreSeleccionado) {
        setFormData((prev) => ({ ...prev, nivel: padreSeleccionado.nivel + 1 }));
      }
    }

    // Si se cambia a nivel 0, limpiar grupo_padre_id
    if (field === 'nivel' && value === 0) {
      setFormData((prev) => ({ ...prev, grupo_padre_id: undefined }));
    }
  };

  const handleSubmit = async () => {
    setError(null);

    // Validaciones
    if (!formData.nombre.trim()) {
      setError('El nombre es obligatorio');
      return;
    }
    if (!formData.codigo_corto.trim()) {
      setError('El código es obligatorio');
      return;
    }
    if (formData.nivel > 0 && !formData.grupo_padre_id) {
      setError('Debe seleccionar un grupo padre para niveles mayores a 0');
      return;
    }

    try {
      setLoading(true);

      if (isEdit) {
        // Actualizar grupo existente
        const updateData: GrupoUpdate = {
          nombre: formData.nombre,
          codigo_corto: formData.codigo_corto,
          grupo_padre_id: formData.grupo_padre_id || null,
          activo: formData.activo,
          actualizado_por: 'superadmin',
        };
        await gruposService.actualizarGrupo(grupo.id, updateData);
      } else {
        // Crear nuevo grupo
        const createData: GrupoCreate = {
          nombre: formData.nombre,
          codigo_corto: formData.codigo_corto,
          grupo_padre_id: formData.grupo_padre_id || null,
          activo: formData.activo,
          creado_por: 'superadmin',
        };
        await gruposService.crearGrupo(createData);
      }

      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al guardar el grupo');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle
        sx={{
          background: `linear-gradient(135deg, ${zentriaColors.violeta.main} 0%, ${zentriaColors.naranja.main} 100%)`,
          color: 'white',
          fontWeight: 700,
        }}
      >
        {isEdit ? 'Editar Grupo' : 'Crear Nuevo Grupo'}
      </DialogTitle>

      <DialogContent sx={{ mt: 2 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Nombre */}
          <TextField
            label="Nombre del Grupo"
            value={formData.nombre}
            onChange={(e) => handleChange('nombre', e.target.value)}
            fullWidth
            required
            placeholder="Ej: Zentria Bogotá"
          />

          {/* Código */}
          <TextField
            label="Código"
            value={formData.codigo_corto}
            onChange={(e) => handleChange('codigo_corto', e.target.value.toUpperCase())}
            fullWidth
            required
            placeholder="Ej: ZEN-BOG"
            inputProps={{ maxLength: 20 }}
            helperText="Código único para identificar el grupo"
          />

          {/* Nivel (solo al crear) */}
          {!isEdit && (
            <FormControl fullWidth>
              <InputLabel>Nivel Jerárquico</InputLabel>
              <Select
                value={formData.nivel}
                onChange={(e) => handleChange('nivel', e.target.value as number)}
                label="Nivel Jerárquico"
              >
                <MenuItem value={0}>0 - Corporativo (Raíz)</MenuItem>
                <MenuItem value={1}>1 - Sede</MenuItem>
                <MenuItem value={2}>2 - Sub-sede</MenuItem>
                <MenuItem value={3}>3 - Nivel 3</MenuItem>
              </Select>
            </FormControl>
          )}

          {/* Grupo Padre */}
          {(formData.nivel > 0 || isEdit) && (
            <FormControl fullWidth>
              <InputLabel>Grupo Padre {formData.nivel > 0 && '*'}</InputLabel>
              <Select
                value={formData.grupo_padre_id || ''}
                onChange={(e) => handleChange('grupo_padre_id', e.target.value as number)}
                label={`Grupo Padre ${formData.nivel > 0 ? '*' : ''}`}
              >
                <MenuItem value="">
                  <em>Sin grupo padre (raíz)</em>
                </MenuItem>
                {gruposDisponibles
                  .filter((g) => g.nivel < formData.nivel || isEdit)
                  .map((g) => (
                    <MenuItem key={g.id} value={g.id}>
                      {g.nombre} ({g.codigo_corto}) - Nivel {g.nivel}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
          )}

          {/* Estado */}
          <FormControlLabel
            control={
              <Switch
                checked={formData.activo}
                onChange={(e) => handleChange('activo', e.target.checked)}
                color="success"
              />
            }
            label={
              <Typography variant="body2">
                {formData.activo ? 'Grupo activo' : 'Grupo inactivo'}
              </Typography>
            }
          />
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading}
          sx={{
            background: `linear-gradient(135deg, ${zentriaColors.verde.main} 0%, ${zentriaColors.info} 100%)`,
            '&:hover': {
              background: `linear-gradient(135deg, ${zentriaColors.verde.dark} 0%, #00B094 100%)`,
            },
          }}
        >
          {loading ? 'Guardando...' : isEdit ? 'Actualizar' : 'Crear Grupo'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
