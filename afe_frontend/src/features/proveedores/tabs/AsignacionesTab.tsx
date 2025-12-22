/**
 * Tab de Asignaciones - CRUD completo con filtro por Grupo/Sede
 *
 * @version 3.0 - Con filtro de grupo obligatorio
 * @date 2025-12-18
 */
import React, { useState, useEffect, useCallback } from 'react';
import nitValidationService from '../../../services/nitValidation.service';
import {
  Box,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Autocomplete,
  Alert,
  CircularProgress,
  Chip,
  Checkbox,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon, DeleteSweep as DeleteSweepIcon, Warning as WarningIcon, Close, Business as BusinessIcon } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../../../app/hooks';
import {
  fetchAsignaciones,
  createAsignacionThunk,
  deleteAsignacionThunk,
  fetchProveedores,
  selectAsignacionesList,
  selectAsignacionesLoading,
  selectProveedoresList,
} from '../proveedoresSlice';
import {
  getResponsables,
  createAsignacionesNitBulkFromConfig,
  Responsable,
} from '../../../services/asignacionNit.api';
import gruposService from '../../../services/grupos.api';
import { Grupo } from '../../../types/grupo.types';
import { zentriaColors } from '../../../theme/colors';

interface AsignacionFormData {
  responsable_id: number | null;
  proveedor_id: number | null;
  // grupo_id removido - arquitectura transitiva (asignaciones aparecen en todos los grupos del responsable)
}

function AsignacionesTab() {
  const dispatch = useAppDispatch();
  const asignaciones = useAppSelector(selectAsignacionesList);
  const loading = useAppSelector(selectAsignacionesLoading);
  const proveedores = useAppSelector(selectProveedoresList);

  // ========== NUEVO: Estados para filtro de grupo ==========
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<number | null>(null);
  const [loadingGrupos, setLoadingGrupos] = useState(false);
  // =========================================================

  const [openDialog, setOpenDialog] = useState(false);
  const [openBulkDialog, setOpenBulkDialog] = useState(false);
  const [openWarningDialog, setOpenWarningDialog] = useState(false); // Modal de advertencia
  const [warningMessage, setWarningMessage] = useState<string>(''); // Mensaje de advertencia
  const [duplicateNit, setDuplicateNit] = useState<string | null>(null); // NIT duplicado para mostrar
  const [bulkResponseData, setBulkResponseData] = useState<any>(null); // Datos de respuesta bulk para mostrar en modal
  const [responsables, setResponsables] = useState<Responsable[]>([]);
  const [formData, setFormData] = useState<AsignacionFormData>({
    responsable_id: null,
    proveedor_id: null,
    grupo_id: null,  // ← NUEVO
  });
  const [bulkResponsableId, setBulkResponsableId] = useState<number | null>(null);
  const [bulkProveedores, setBulkProveedores] = useState<string[]>([]);
  const [bulkNitsRechazados, setBulkNitsRechazados] = useState<string[]>([]); // NITs que no están registrados
  const [hasPendingInput, setHasPendingInput] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [bulkDialogError, setBulkDialogError] = useState<string | null>(null); // Error específico del modal bulk
  const [submitting, setSubmitting] = useState(false);
  const [selectedAsignaciones, setSelectedAsignaciones] = useState<number[]>([]);
  const listboxRef = React.useRef<HTMLUListElement | null>(null);
  const scrollPositionRef = React.useRef<number>(0);

  // ========== NUEVO: Cargar grupos del usuario al montar ==========
  useEffect(() => {
    const cargarGruposDelUsuario = async () => {
      try {
        setLoadingGrupos(true);

        // Cargar grupos directamente desde el backend
        // El backend ya filtra automáticamente por los grupos del usuario logueado
        const response = await gruposService.listarGrupos();

        console.log('[DEBUG] Grupos cargados desde backend:', response.grupos);

        setGrupos(response.grupos || []);
      } catch (error) {
        console.error('Error cargando grupos:', error);
        setError('Error al cargar grupos');
      } finally {
        setLoadingGrupos(false);
      }
    };
    cargarGruposDelUsuario();
  }, []);
  // ====================================================

  useEffect(() => {
    // Cargar TODAS las asignaciones (activas e inactivas) para ver asignaciones huérfanas
    dispatch(fetchAsignaciones({ skip: 0, limit: 1000 }));
    dispatch(fetchProveedores({ skip: 0, limit: 1000 }));
  }, [dispatch]);


  // ========== NUEVO: Cargar responsables cuando cambie el grupo seleccionado ==========
  useEffect(() => {
    if (grupoSeleccionado) {
      loadResponsables(grupoSeleccionado);
    } else {
      loadResponsables();  // Cargar todos si no hay grupo seleccionado
    }
  }, [grupoSeleccionado]);
  // ===================================================================================

  /**
   * Valida y normaliza un array de NITs
   * Memorizada con useCallback para evitar re-creación innecesaria
   * Reutilizable en todos los caminos de entrada (onChange, onKeyDown, handleBulkSubmit)
   * @param nitsInput - Array de NITs a normalizar (con o sin DV)
   * @returns Array con NITs normalizados (solo los válidos)
   */
  const normalizarNits = useCallback(
    async (nitsInput: string[]): Promise<string[]> => {
      const nitsNormalizados: string[] = [];

      console.log('[normalizarNits] Iniciando normalización de', nitsInput.length, 'NITs');
      console.log('[normalizarNits] bulkResponsableId:', bulkResponsableId);

      for (const nitInput of nitsInput) {
        try {
          // Validación básica rápida antes de llamada al backend
          if (!nitValidationService.isValidBasicFormat(nitInput)) {
            console.log(`[normalizarNits] SKIP - Basic format failed: ${nitInput}`);
            continue;
          }

          // Validar y normalizar a través del backend (calcula DV DIAN)
          const validationResult = await nitValidationService.validateNit(nitInput);
          console.log(`[normalizarNits] validateNit(${nitInput}) =`, validationResult);

          if (!validationResult.isValid || !validationResult.normalizedNit) {
            console.log(`[normalizarNits] SKIP - Backend validation failed: ${nitInput}`);
            continue;
          }

          const nitNormalizado = validationResult.normalizedNit;

          // Verificar si el NIT ya está asignado a este responsable
          if (bulkResponsableId) {
            const yaAsignado = asignaciones.some(
              (a) => a.nit === nitNormalizado && a.responsable_id === bulkResponsableId && a.activo
            );
            if (yaAsignado) {
              console.log(`[normalizarNits] SKIP - Already assigned: ${nitNormalizado}`);
              continue;
            }
          }

          console.log(`[normalizarNits] ACCEPTED: ${nitNormalizado}`);
          nitsNormalizados.push(nitNormalizado);
        } catch (error) {
          console.error(`[normalizarNits] Exception validating NIT ${nitInput}:`, error);
          continue;
        }
      }

      console.log('[normalizarNits] Resultado final:', nitsNormalizados.length, 'NITs válidos');
      return nitsNormalizados;
    },
    [bulkResponsableId, asignaciones]
  );

  // ========== MODIFICADO: Cargar responsables filtrados por grupo ==========
  const loadResponsables = async (grupoId?: number | null) => {
    try {
      if (grupoId) {
        // Cargar solo responsables del grupo seleccionado
        const grupoData = await gruposService.obtenerUsuariosGrupo(grupoId);
        const responsablesDelGrupo = grupoData.map((asignacion: any) => ({
          id: asignacion.responsable_id,
          nombre: asignacion.responsable_nombre,
          email: asignacion.responsable_email,
          usuario: asignacion.responsable_usuario,
          rol: asignacion.responsable_rol,
          area: asignacion.responsable_area,
        }));
        setResponsables(responsablesDelGrupo);
      } else {
        // Cargar todos los responsables (comportamiento original)
        const data = await getResponsables({ limit: 1000 });
        console.log('Responsables cargados:', data);
        setResponsables(data);
      }
    } catch (err) {
      console.error('Error cargando responsables:', err);
      setError(`Error al cargar responsables: ${err instanceof Error ? err.message : String(err)}`);
    }
  };
  // ========================================================================

  const handleOpenDialog = () => {
    if (!grupoSeleccionado) {
      setError('Debe seleccionar un grupo/sede primero');
      return;
    }
    setFormData({
      responsable_id: null,
      proveedor_id: null,
      // grupo_id removido - arquitectura transitiva
    });
    setError(null);
    setSuccess(null);
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setBulkResponseData(null);
  };

  const handleOpenBulkDialog = () => {
    if (!grupoSeleccionado) {
      setError('Debe seleccionar un grupo/sede primero');
      return;
    }
    // Limpiar todos los estados al abrir el modal
    setBulkResponsableId(null);
    setBulkProveedores([]);
    setBulkNitsRechazados([]);
    setHasPendingInput(false);
    setBulkDialogError(null); // Limpiar error del modal
    setOpenBulkDialog(true);
  };

  const handleCloseBulkDialog = () => {
    setOpenBulkDialog(false);
    // Limpiar estados al cerrar el modal
    setBulkResponsableId(null);
    setBulkProveedores([]);
    setBulkNitsRechazados([]);
    setHasPendingInput(false);
    setBulkDialogError(null);
  };

  const handleSubmit = async () => {
    if (!formData.responsable_id || !formData.proveedor_id) {
      setError('Debe seleccionar un responsable y un proveedor');
      return;
    }

    // Validación de grupo_id removida - arquitectura transitiva
    // La asignación se crea sin grupo_id y aparece en todos los grupos del responsable

    setSubmitting(true);
    setError(null);

    try {
      // Obtener datos del proveedor seleccionado
      const proveedor = proveedores.find((p) => p.id === formData.proveedor_id);

      if (!proveedor) {
        setError('Proveedor no encontrado');
        return;
      }

      // Crear asignación con arquitectura transitiva (sin grupo_id)
      // La asignación aparecerá en todos los grupos del responsable automáticamente
      await dispatch(
        createAsignacionThunk({
          nit: proveedor.nit,
          nombre_proveedor: proveedor.razon_social || '',
          responsable_id: formData.responsable_id,
          // grupo_id removido - arquitectura transitiva
          area: proveedor.area,
          permitir_aprobacion_automatica: true,
          requiere_revision_siempre: false,
        })
      ).unwrap();

      setSuccess('Asignación creada exitosamente');
      setTimeout(() => {
        handleCloseDialog();
        setSuccess(null);
      }, 1500);
    } catch (err: any) {
      // Manejar errores específicos del backend de manera empresarial
      // Con .unwrap(), el error lanzado puede ser un string (del rejectWithValue) o un Error object
      const detail = typeof err === 'string' ? err : (err.message || JSON.stringify(err));

      // Detectar si el error es por NIT duplicado/ya asignado
      // Patrones de error que indican duplicado:
      // - "ya tiene asignado el NIT"
      // - "ya existe"
      // - "activa"
      const isDuplicateError =
        detail.toLowerCase().includes('ya') &&
        (detail.toLowerCase().includes('asignado') ||
         detail.toLowerCase().includes('existe') ||
         detail.toLowerCase().includes('activa'));

      if (isDuplicateError) {
        // Mostrar advertencia elegante para duplicados
        // Intentar extraer NIT del patrón "NIT_DUPLICADO: XXXXXXXXX-D"
        let nitDisplay = '';
        const nitDuplicadoMatch = detail.match(/NIT_DUPLICADO:\s*(\d{1,11}-\d)/);
        if (nitDuplicadoMatch) {
          nitDisplay = nitDuplicadoMatch[1];
        } else {
          // Fallback: buscar cualquier patrón de NIT (XXXXXXXXX-D con hasta 11 dígitos)
          const nitMatch = detail.match(/(\d{1,11}-\d)/);
          nitDisplay = nitMatch ? nitMatch[1] : '';
        }

        setDuplicateNit(nitDisplay);
        setWarningMessage(`NIT ya registrado: ${nitDisplay}`);
        setOpenWarningDialog(true);
      } else {
        // Otros errores se muestran como error
        setError(detail || 'Error al crear la asignación');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleBulkSubmit = async () => {
    // PRIMERO: Procesar cualquier input pendiente en el campo de texto
    let nitsAEnviar = bulkProveedores;

    if (hasPendingInput) {
      const autocompleteInput = document.querySelector<HTMLInputElement>(
        'input[placeholder*="NITs separados por coma"]'
      );

      if (autocompleteInput && autocompleteInput.value.trim()) {
        const inputValue = autocompleteInput.value.trim();

        // Separar NITs por coma
        const nits = inputValue
          .split(',')
          .map((nit) => nit.trim())
          .filter((nit) => nit.length > 0);

        // Usar función centralizada de normalización
        const nitsValidos = await normalizarNits(nits);

        // Agregar a los NITs existentes (sin duplicados)
        const nitsUnicos = [...new Set([...bulkProveedores, ...nitsValidos])];

        // Si no hay NITs válidos después de procesar, mostrar error
        if (nitsUnicos.length === 0) {
          setBulkDialogError('Los NITs ingresados no tienen un formato válido.');
          return;
        }

        // Usar los NITs procesados para enviar
        nitsAEnviar = nitsUnicos;

        // Limpiar el input
        autocompleteInput.value = '';
      }
    }

    // VALIDACIONES
    if (!bulkResponsableId) {
      setBulkDialogError('Debe seleccionar un responsable');
      return;
    }

    if (nitsAEnviar.length === 0) {
      setBulkDialogError('Debe seleccionar o ingresar al menos un NIT válido');
      return;
    }

    setSubmitting(true);
    setBulkDialogError(null);

    try {
      // nitsAEnviar contiene solo los NITs VÁLIDOS (incluyendo los del input pendiente si existe)
      // Convertir NITs a string separado por comas para el endpoint bulk-nit-config
      const nitsString = nitsAEnviar.join(',');

      console.log('==== DEBUG ASIGNACIÓN MASIVA ====');
      console.log('NITs a asignar:', nitsString);
      console.log('Responsable ID:', bulkResponsableId);

      const requestData = {
        responsable_id: bulkResponsableId,
        nits: nitsString,
        permitir_aprobacion_automatica: true,
      };
      console.log('Datos completos a enviar:', requestData);

      const response = await createAsignacionesNitBulkFromConfig(requestData);

      console.log('Respuesta del backend:', response);
      console.log('Errores del backend:', response.errores);
      console.log('Mensaje del backend:', response.mensaje);
      console.log('==== FIN DEBUG ====');

      // Recargar asignaciones inmediatamente (todas, incluyendo inactivas)
      await dispatch(fetchAsignaciones({}));

      // Construir mensaje según resultado
      let mensajeCompleto = '';

      if (response.creadas > 0) {
        const nitsCreados = response.nits_creados && response.nits_creados.length > 0
          ? response.nits_creados.join(', ')
          : 'N/A';
        mensajeCompleto += `[NEW] Se crearon ${response.creadas} NIT(s) nuevos:\n${nitsCreados}\n\n`;
      }

      if (response.reactivadas && response.reactivadas > 0) {
        const nitsReactivados = response.nits_reactivados && response.nits_reactivados.length > 0
          ? response.nits_reactivados.join(', ')
          : 'N/A';
        mensajeCompleto += `[REACTIVATED] Se reactivaron ${response.reactivadas} asignación(es) previamente eliminada(s):\n${nitsReactivados}\n\n`;
      }

      if (response.omitidas > 0) {
        const nitsOmitidosStr = response.nits_omitidos && response.nits_omitidos.length > 0
          ? response.nits_omitidos.join(', ')
          : 'N/A';
        mensajeCompleto += `[SKIPPED] ${response.omitidas} NIT(s) ya estaban asignados activos a este responsable y fueron omitidos:\n${nitsOmitidosStr}\n\n`;
      }

      if (response.errores && response.errores.length > 0) {
        const nitsConError = response.errores.map((e: any) => e.nit || e).join(', ');
        mensajeCompleto += `✗ Los siguientes NITs NO fueron asignados:\n\n${nitsConError}\n\nVerifique que estén registrados en nit_configuracion.`;
      }

      // Cerrar el modal de asignación ANTES de mostrar mensajes
      handleCloseBulkDialog();

      // Si hay mensajes de advertencia o errores, mostrar modal
      if (response.omitidas > 0 || (response.errores && response.errores.length > 0) || (response.reactivadas && response.reactivadas > 0)) {
        // Guardar datos de la respuesta para mostrar en modal
        setBulkResponseData(response);
        setWarningMessage(mensajeCompleto.trim());
        setOpenWarningDialog(true);
      } else if (response.creadas > 0) {
        // Solo éxito total
        setSuccess(`${response.creadas} asignación(es) creada(s) exitosamente`);
        setTimeout(() => setSuccess(null), 3000);
      } else {
        // No se creó ni actualizó nada
        setError('No se pudo realizar ninguna asignación. Verifique los datos.');
      }
    } catch (err: any) {
      // Manejar errores específicos del backend de manera empresarial
      // El error puede venir como string (del rejectWithValue) o como Error object
      const detail = typeof err === 'string' ? err : (err.message || JSON.stringify(err));

      // Detectar si el error es por NITs duplicados/ya asignados
      const isDuplicateError =
        detail.toLowerCase().includes('ya') &&
        (detail.toLowerCase().includes('asignado') ||
         detail.toLowerCase().includes('existe') ||
         detail.toLowerCase().includes('activa'));

      if (isDuplicateError) {
        // Extraer NITs del mensaje si es posible
        const nitsMatch = detail.match(/(\d{1,9}-\d)/g);
        const nitsDisplay = nitsMatch ? nitsMatch.join(', ') : '';

        setDuplicateNit(nitsDisplay);
        setWarningMessage('NITs ya registrados');
        setOpenWarningDialog(true);
      } else {
        setError(detail || 'Error al crear asignaciones masivas');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('¿Está seguro de eliminar esta asignación?')) {
      try {
        await dispatch(deleteAsignacionThunk(id)).unwrap();
      } catch (err: any) {
        setError(err.message || 'Error al eliminar la asignación');
      }
    }
  };

  // ========== ARQUITECTURA TRANSITIVA: Backend ya filtra correctamente ==========
  // El backend devuelve asignaciones usando lógica transitiva:
  // 1. Asignaciones específicas del grupo (grupo_id = X)
  // 2. Asignaciones globales (grupo_id = NULL)
  // 3. Asignaciones de responsables que pertenecen al grupo (transitivas)
  // Por lo tanto, NO necesitamos filtrar localmente
  const asignacionesFiltradas = asignaciones;
  // ========================================================================

  const handleSelectAll = () => {
    if (selectedAsignaciones.length === asignacionesFiltradas.length) {
      setSelectedAsignaciones([]);
    } else {
      setSelectedAsignaciones(asignacionesFiltradas.map((a) => a.id));
    }
  };

  const handleSelectOne = (id: number) => {
    if (selectedAsignaciones.includes(id)) {
      setSelectedAsignaciones(selectedAsignaciones.filter((selId) => selId !== id));
    } else {
      setSelectedAsignaciones([...selectedAsignaciones, id]);
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedAsignaciones.length === 0) return;

    const confirmMessage =
      selectedAsignaciones.length === 1
        ? '¿Está seguro de eliminar esta asignación?'
        : `¿Está seguro de eliminar ${selectedAsignaciones.length} asignaciones?`;

    if (window.confirm(confirmMessage)) {
      setSubmitting(true);
      setError(null);
      setSuccess(null);
      let errores = 0;
      let eliminadas = 0;

      for (const id of selectedAsignaciones) {
        try {
          await dispatch(deleteAsignacionThunk(id)).unwrap();
          eliminadas++;
        } catch (err: any) {
          errores++;
        }
      }

      // Recargar asignaciones desde el backend para sincronizar (todas)
      await dispatch(fetchAsignaciones({}));

      if (eliminadas > 0) {
        setSuccess(`${eliminadas} asignacion(es) eliminada(s) exitosamente`);
      }
      if (errores > 0) {
        setError(`Error al eliminar ${errores} asignacion(es)`);
      }

      setSelectedAsignaciones([]);
      setSubmitting(false);
    }
  };

  return (
    <Box>
      {/* ========== NUEVO: Selector de Grupo/Sede ========== */}
      <Box sx={{ mb: 4 }}>
        <FormControl fullWidth sx={{ maxWidth: 500 }}>
          <InputLabel id="grupo-selector-label">Sede / Subsede</InputLabel>
          <Select
            labelId="grupo-selector-label"
            value={grupoSeleccionado || ''}
            onChange={(e) => setGrupoSeleccionado(Number(e.target.value))}
            label="Sede / Subsede"
            startAdornment={<BusinessIcon sx={{ mr: 1, color: 'text.secondary' }} />}
            disabled={loadingGrupos}
          >
            {grupos.map((grupo) => (
              <MenuItem key={grupo.id} value={grupo.id}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={grupo.codigo_corto}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                  <Typography>{grupo.nombre}</Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
          <FormHelperText>
            Seleccione la sede/subsede para gestionar sus asignaciones de proveedores
          </FormHelperText>
        </FormControl>
      </Box>
      {/* =================================================== */}

      {/* Mostrar contenido solo si hay grupo seleccionado */}
      {!grupoSeleccionado ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Seleccione una sede/subsede para ver y gestionar sus asignaciones de proveedores
          </Typography>
        </Alert>
      ) : (
        <>
          {/* Header */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6" fontWeight={600}>
                Gestión de Asignaciones
              </Typography>
          {selectedAsignaciones.length > 0 && (
            <Chip
              label={`${selectedAsignaciones.length} seleccionada(s)`}
              color="primary"
              size="small"
              onDelete={() => setSelectedAsignaciones([])}
            />
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {selectedAsignaciones.length > 0 && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteSweepIcon />}
              onClick={handleDeleteSelected}
              disabled={submitting}
            >
              Eliminar {selectedAsignaciones.length}
            </Button>
          )}
          <Button variant="outlined" startIcon={<AddIcon />} onClick={handleOpenBulkDialog}>
            Asignación Masiva
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenDialog}>
            Nueva Asignación
          </Button>
        </Box>
      </Box>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={asignacionesFiltradas.length > 0 && selectedAsignaciones.length === asignacionesFiltradas.length}
                  indeterminate={selectedAsignaciones.length > 0 && selectedAsignaciones.length < asignacionesFiltradas.length}
                  onChange={handleSelectAll}
                  disabled={asignacionesFiltradas.length === 0}
                />
              </TableCell>
              <TableCell>ID</TableCell>
              <TableCell>Responsable</TableCell>
              <TableCell>Razón Social</TableCell>
              <TableCell>NIT</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <CircularProgress size={24} />
                </TableCell>
              </TableRow>
            ) : asignacionesFiltradas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">
                    No hay asignaciones registradas para esta sede
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              asignacionesFiltradas.map((asignacion) => (
                <TableRow
                  key={asignacion.id}
                  hover
                  selected={selectedAsignaciones.includes(asignacion.id)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedAsignaciones.includes(asignacion.id)}
                      onChange={() => handleSelectOne(asignacion.id)}
                    />
                  </TableCell>
                  <TableCell>{asignacion.id}</TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {asignacion.responsable?.nombre || `ID: ${asignacion.responsable_id}`}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {asignacion.responsable?.email || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {asignacion.nombre_proveedor}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={asignacion.nit} size="small" />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" color="error" onClick={() => handleDelete(asignacion.id)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Dialog para crear asignación individual */}
      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
        aria-modal="true"
        disableEnforceFocus
      >
        <DialogTitle>
          Nueva Asignación
          {grupoSeleccionado && (
            <Typography variant="caption" display="block" color="text.secondary">
              Grupo: {grupos.find(g => g.id === grupoSeleccionado)?.nombre || grupoSeleccionado}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            {/* Mostrar grupo seleccionado como chip */}
            {grupoSeleccionado && (
              <Alert severity="info" sx={{ mb: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <BusinessIcon fontSize="small" />
                  <Typography variant="body2">
                    Asignando a: <strong>{grupos.find(g => g.id === grupoSeleccionado)?.codigo_corto}</strong> - {grupos.find(g => g.id === grupoSeleccionado)?.nombre}
                  </Typography>
                </Stack>
              </Alert>
            )}
            <Autocomplete
              options={responsables}
              getOptionLabel={(option) => `${option.nombre} (${option.usuario})`}
              value={responsables.find((r) => r.id === formData.responsable_id) || null}
              onChange={(_, newValue) =>
                setFormData({ ...formData, responsable_id: newValue?.id || null })
              }
              renderInput={(params) => <TextField {...params} label="Responsable del Equipo" required helperText="Solo responsables del grupo seleccionado" />}
            />
            <Autocomplete
              options={proveedores}
              getOptionLabel={(option) => `${option.razon_social} - ${option.nit}`}
              value={proveedores.find((p) => p.id === formData.proveedor_id) || null}
              onChange={(_, newValue) =>
                setFormData({ ...formData, proveedor_id: newValue?.id || null })
              }
              renderInput={(params) => <TextField {...params} label="Proveedor" required />}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={submitting}>
            {submitting ? <CircularProgress size={24} /> : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog para asignación masiva */}
      <Dialog
        open={openBulkDialog}
        onClose={handleCloseBulkDialog}
        maxWidth="md"
        fullWidth
        aria-modal="true"
        disableEnforceFocus
      >
        <DialogTitle>
          Asignación Masiva de Proveedores
          {grupoSeleccionado && (
            <Typography variant="caption" display="block" color="text.secondary">
              Grupo: {grupos.find(g => g.id === grupoSeleccionado)?.nombre || grupoSeleccionado}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          {bulkDialogError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setBulkDialogError(null)}>
              {bulkDialogError}
            </Alert>
          )}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            {/* Mostrar grupo seleccionado como chip */}
            {grupoSeleccionado && (
              <Alert severity="info" sx={{ mb: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <BusinessIcon fontSize="small" />
                  <Typography variant="body2">
                    Asignando a: <strong>{grupos.find(g => g.id === grupoSeleccionado)?.codigo_corto}</strong> - {grupos.find(g => g.id === grupoSeleccionado)?.nombre}
                  </Typography>
                </Stack>
              </Alert>
            )}
            <Autocomplete
              options={responsables}
              getOptionLabel={(option) => `${option.nombre} (${option.usuario})`}
              value={responsables.find((r) => r.id === bulkResponsableId) || null}
              onChange={(_, newValue) => setBulkResponsableId(newValue?.id || null)}
              renderInput={(params) => <TextField {...params} label="Responsable del Equipo" required helperText="Solo responsables del grupo seleccionado" />}
            />
            {/* Autocomplete de NITs - Validación simplificada, backend valida contra nit_configuracion */}
            <Autocomplete
              multiple
              freeSolo
              disableCloseOnSelect
              disableListWrap
              options={proveedores.map((p) => p.nit)}
              getOptionLabel={(option) => option}
              value={bulkProveedores}
              onChange={async (_, newValue) => {
                // Procesar NITs (pueden venir pegados con comas o seleccionados)
                const nitsToProcess = newValue.flatMap((nit) => {
                  // Si contiene comas, separar múltiples NITs
                  if (nit.includes(',')) {
                    return nit
                      .split(',')
                      .map((n) => n.trim())
                      .filter((n) => n.length > 0);
                  }
                  return [nit.trim()];
                });

                // Eliminar duplicados
                const nitsUnicos = [...new Set(nitsToProcess)];

                // Usar función centralizada de normalización
                const nitsNormalizados = await normalizarNits(nitsUnicos);

                // Limpiar errores cuando el usuario ingresa NITs válidos
                if (nitsNormalizados.length > 0) {
                  setBulkDialogError(null);
                }

                setBulkProveedores(nitsNormalizados);
                setBulkNitsRechazados([]);
              }}
              ListboxProps={{
                style: { maxHeight: '300px' },
              }}
              renderTags={(value, getTagProps) =>
                value.map((nitNormalizado, index) => {
                  // Buscar proveedor por NIT normalizado (que ya incluye DV)
                  // Si no encuentra, intentar buscar sin DV (compatibilidad)
                  let proveedor = proveedores.find((p) => p.nit === nitNormalizado);

                  if (!proveedor && nitNormalizado.includes('-')) {
                    // Intentar buscar sin DV
                    const nitSinDv = nitNormalizado.split('-')[0];
                    proveedor = proveedores.find((p) => p.nit?.includes(nitSinDv));
                  }

                  return (
                    <Chip
                      {...getTagProps({ index })}
                      key={nitNormalizado}
                      label={`${nitNormalizado} - ${proveedor?.razon_social || 'No registrado'}`}
                      color="primary"
                      variant="outlined"
                    />
                  );
                })
              }
              renderOption={(props, option, { selected }) => {
                // option es siempre un string (NIT)
                const nit = option;
                const proveedor = proveedores.find((p) => p.nit === nit);
                const { onClick, ...otherProps } = props;

                return (
                  <li
                    {...otherProps}
                    key={nit}
                    onClick={(e) => {
                      // Prevenir el scroll automático al inicio
                      e.preventDefault();
                      if (onClick) {
                        onClick(e);
                      }
                    }}
                  >
                    <Checkbox
                      icon={<span style={{ width: 17, height: 17, border: '2px solid #ccc', borderRadius: 3 }} />}
                      checkedIcon={<span style={{ width: 17, height: 17, backgroundColor: '#9c27b0', border: '2px solid #9c27b0', borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 12 }}>✓</span>}
                      checked={selected}
                      sx={{ marginRight: 1 }}
                    />
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="body2" fontWeight={500}>
                        {nit}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {proveedor?.razon_social || 'Sin razón social'}
                      </Typography>
                    </Box>
                  </li>
                );
              }}
              componentsProps={{
                paper: {
                  sx: {
                    '& .MuiAutocomplete-listbox': {
                      maxHeight: '300px',
                      paddingBottom: '48px', // Espacio para el botón
                    },
                  },
                },
                popper: {
                  placement: 'bottom-start',
                  modifiers: [
                    {
                      name: 'flip',
                      enabled: false,
                    },
                  ],
                },
              }}
              ListboxComponent={(props) => {
                const handleScroll = (e: React.UIEvent<HTMLUListElement>) => {
                  scrollPositionRef.current = e.currentTarget.scrollTop;
                };

                return (
                  <Box>
                    <ul
                      {...props}
                      ref={(node) => {
                        listboxRef.current = node;
                        if (node && scrollPositionRef.current > 0) {
                          // Restaurar posición del scroll
                          node.scrollTop = scrollPositionRef.current;
                        }
                      }}
                      onScroll={handleScroll}
                      style={{ ...props.style, paddingBottom: 0 }}
                    />
                    <Box
                      sx={{
                        position: 'sticky',
                        bottom: 0,
                        backgroundColor: 'background.paper',
                        borderTop: '1px solid',
                        borderColor: 'divider',
                        padding: 1,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        zIndex: 1,
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {bulkProveedores.length} NIT{bulkProveedores.length !== 1 ? 's' : ''} seleccionado
                        {bulkProveedores.length !== 1 ? 's' : ''}
                      </Typography>
                      <Button
                        size="small"
                        variant="contained"
                        onClick={(e) => {
                          e.stopPropagation();
                          // Cerrar el dropdown
                          (document.activeElement as HTMLElement)?.blur();
                        }}
                      >
                        Listo
                      </Button>
                    </Box>
                  </Box>
                );
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Seleccionar NITs"
                  placeholder="Busque o digite NITs separados por coma"
                  helperText="Puede seleccionar de la lista o digitar múltiples NITs separados por comas (Ej: 900123456, 800111222, 900333444)"
                  InputProps={{
                    ...params.InputProps,
                  }}
                  onChange={(e) => {
                    // Detectar si hay texto con comas en el input
                    const inputValue = (e.target as HTMLInputElement).value;
                    setHasPendingInput(inputValue.includes(','));
                  }}
                  onKeyDown={async (e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      const inputValue = (e.target as HTMLInputElement).value;

                      if (inputValue && inputValue.includes(',')) {
                        // Separar NITs por coma
                        const nits = inputValue
                          .split(',')
                          .map((nit) => nit.trim())
                          .filter((nit) => nit.length > 0);

                        // Usar función centralizada de normalización
                        const nitsValidos = await normalizarNits(nits);

                        // Agregar a los NITs existentes (sin duplicados)
                        const nitsUnicos = [...new Set([...bulkProveedores, ...nitsValidos])];
                        setBulkProveedores(nitsUnicos);

                        // Limpiar errores cuando hay NITs válidos
                        if (nitsUnicos.length > 0) {
                          setBulkDialogError(null);
                        }

                        setBulkNitsRechazados([]);

                        // Limpiar el input y el estado
                        (e.target as HTMLInputElement).value = '';
                        setHasPendingInput(false);
                      }
                    }
                  }}
                />
              )}
            />

            {bulkProveedores.length > 0 && (
              <Alert severity="info" sx={{ mt: 1 }}>
                <Typography variant="body2" fontWeight={500}>
                  {bulkProveedores.length} NIT{bulkProveedores.length !== 1 ? 's' : ''} seleccionado
                  {bulkProveedores.length !== 1 ? 's' : ''} para asignar
                </Typography>
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseBulkDialog} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={handleBulkSubmit} variant="contained" disabled={submitting || (!bulkResponsableId)}>
            {submitting ? (
              <CircularProgress size={24} />
            ) : hasPendingInput ? (
              'Asignar NITs'
            ) : bulkProveedores.length === 0 ? (
              'Asignar NITs'
            ) : (
              `Asignar ${bulkProveedores.length} NIT${bulkProveedores.length !== 1 ? 's' : ''}`
            )}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal de Advertencia para NITs no registrados */}
      <Dialog
        open={openWarningDialog}
        onClose={() => setOpenWarningDialog(false)}
        maxWidth="sm"
        fullWidth
        aria-modal="true"
        disableEnforceFocus
        PaperProps={{
          sx: {
            borderRadius: 3,
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
            overflow: 'hidden',
          }
        }}
      >
        {/* Header con Gradiente Corporativo Naranja - Mejor contraste */}
        <Box
          sx={{
            background: `linear-gradient(135deg, ${zentriaColors.naranja.main} 0%, ${zentriaColors.naranja.dark} 100%)`,
            color: 'white',
            p: 3,
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Stack direction="row" spacing={2} alignItems="center" flex={1}>
            <Box
              sx={{
                width: 50,
                height: 50,
                borderRadius: '50%',
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backdropFilter: 'blur(10px)',
              }}
            >
              <WarningIcon sx={{ fontSize: 28, color: 'white' }} />
            </Box>
            <Box>
              <Typography variant="h5" fontWeight={700} color="white">
                {warningMessage.includes('NITs') ? 'NITs Ya Registrados' : 'NIT Ya Registrado'}
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                Esta asignación ya existe
              </Typography>
            </Box>
          </Stack>
          <IconButton
            onClick={() => {
              setOpenWarningDialog(false);
              setDuplicateNit(null);
              setWarningMessage('');
            }}
            aria-label="Cerrar advertencia"
            sx={{
              color: 'white',
              backgroundColor: 'rgba(255, 255, 255, 0.15)',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.25)',
              },
            }}
          >
            <Close />
          </IconButton>
        </Box>

        <DialogContent sx={{ p: 4, backgroundColor: '#fafafa', textAlign: 'left', maxHeight: '60vh', overflowY: 'auto' }}>
          {/* Mostrar datos de respuesta bulk si existen */}
          {bulkResponseData ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              {/* CREADOS */}
              {bulkResponseData.creadas > 0 && bulkResponseData.nits_creados && (
                <Box sx={{ p: 2.5, backgroundColor: '#e8f5e9', border: '2px solid #4caf50', borderRadius: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#2e7d32', mb: 1.5 }}>
                    ✓ {bulkResponseData.creadas} NIT(s) CREADO(S):
                  </Typography>
                  <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: 1,
                  }}>
                    {bulkResponseData.nits_creados.map((nit: string, idx: number) => (
                      <Box
                        key={idx}
                        sx={{
                          backgroundColor: 'white',
                          border: '1px solid #4caf50',
                          borderRadius: 1,
                          p: 1.2,
                          textAlign: 'center',
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          color: '#2e7d32',
                        }}
                      >
                        {nit}
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}

              {/* REACTIVADOS */}
              {bulkResponseData.reactivadas > 0 && bulkResponseData.nits_reactivados && (
                <Box sx={{ p: 2.5, backgroundColor: '#fff3e0', border: '2px solid #ff9800', borderRadius: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#e65100', mb: 1.5 }}>
                    ↻ {bulkResponseData.reactivadas} NIT(s) REACTIVADO(S):
                  </Typography>
                  <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: 1,
                  }}>
                    {bulkResponseData.nits_reactivados.map((nit: string, idx: number) => (
                      <Box
                        key={idx}
                        sx={{
                          backgroundColor: 'white',
                          border: '1px solid #ff9800',
                          borderRadius: 1,
                          p: 1.2,
                          textAlign: 'center',
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          color: '#e65100',
                        }}
                      >
                        {nit}
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}

              {/* OMITIDOS */}
              {bulkResponseData.omitidas > 0 && bulkResponseData.nits_omitidos && (
                <Box sx={{ p: 2.5, backgroundColor: '#f3e5f5', border: '2px solid #9c27b0', borderRadius: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#6a1b9a', mb: 1.5 }}>
                    ⊘ {bulkResponseData.omitidas} NIT(s) OMITIDO(S) (ya asignados):
                  </Typography>
                  <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: 1,
                  }}>
                    {bulkResponseData.nits_omitidos.map((nit: string, idx: number) => (
                      <Box
                        key={idx}
                        sx={{
                          backgroundColor: 'white',
                          border: '1px solid #9c27b0',
                          borderRadius: 1,
                          p: 1.2,
                          textAlign: 'center',
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          color: '#6a1b9a',
                        }}
                      >
                        {nit}
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}

              {/* ERRORES */}
              {bulkResponseData.errores && bulkResponseData.errores.length > 0 && (
                <Box sx={{ p: 2.5, backgroundColor: '#ffebee', border: '2px solid #f44336', borderRadius: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#c62828', mb: 1.5 }}>
                    ✗ {bulkResponseData.errores.length} NIT(s) CON ERROR:
                  </Typography>
                  <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                    gap: 1,
                  }}>
                    {bulkResponseData.errores.map((err: any, idx: number) => (
                      <Box
                        key={idx}
                        sx={{
                          backgroundColor: 'white',
                          border: '1px solid #f44336',
                          borderRadius: 1,
                          p: 1.2,
                          textAlign: 'center',
                          fontFamily: 'monospace',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: '#c62828',
                        }}
                      >
                        {err.nit || err}
                      </Box>
                    ))}
                  </Box>
                  <Typography variant="caption" sx={{ color: '#c62828', mt: 1.5, display: 'block' }}>
                    Verificar que estén registrados en nit_configuracion
                  </Typography>
                </Box>
              )}
            </Box>
          ) : (
            <>
              {/* NIT Duplicado - Para errores de asignación simple */}
              {duplicateNit && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" sx={{ color: '#666', mb: 1 }}>
                    NIT ya registrado:
                  </Typography>
                  <Box
                    sx={{
                      backgroundColor: 'white',
                      border: `2px solid ${zentriaColors.naranja.main}`,
                      borderRadius: 2,
                      p: 2.5,
                      display: 'inline-block',
                      minWidth: 200,
                    }}
                  >
                    <Typography
                      variant="h5"
                      sx={{
                        fontWeight: 700,
                        color: zentriaColors.naranja.main,
                        fontFamily: 'monospace',
                        letterSpacing: 1,
                      }}
                    >
                      {duplicateNit}
                    </Typography>
                  </Box>
                </Box>
              )}

              {/* Mensaje descriptivo genérico */}
              <Alert
                severity="info"
                sx={{
                  backgroundColor: `${zentriaColors.verde.light}15`,
                  border: `1.5px solid ${zentriaColors.verde.light}`,
                  borderRadius: 2,
                  textAlign: 'left',
                  '& .MuiAlert-message': {
                    color: '#222',
                  },
                }}
              >
                <Typography variant="body2" color="#222">
                  {warningMessage.includes('NITs')
                    ? 'Estos NITs ya están asignados a este responsable. Selecciona otros NITs para continuar.'
                    : 'Este NIT ya está asignado a este responsable. Selecciona otro NIT para continuar.'}
                </Typography>
              </Alert>
            </>
          )}
        </DialogContent>

        {/* Footer de Acciones */}
        <Box
          sx={{
            backgroundColor: '#f5f5f5',
            p: 3,
            borderTop: `1px solid ${zentriaColors.cinza}`,
            display: 'flex',
            gap: 2,
            justifyContent: 'flex-end',
          }}
        >
          <Button
            onClick={() => {
              setOpenWarningDialog(false);
              setDuplicateNit(null);
              setWarningMessage('');
              setBulkResponseData(null);
            }}
            variant="contained"
            size="large"
            sx={{
              minWidth: 160,
              background: `linear-gradient(135deg, ${zentriaColors.naranja.main} 0%, ${zentriaColors.naranja.dark} 100%)`,
              color: 'white',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              boxShadow: `0 4px 15px ${zentriaColors.naranja.main}40`,
              '&:hover': {
                boxShadow: `0 6px 20px ${zentriaColors.naranja.main}60`,
              },
            }}
          >
            Entendido
          </Button>
        </Box>
      </Dialog>
        </>
      )}
      {/* Fin del condicional de grupo seleccionado */}
    </Box>
  );
}

export default AsignacionesTab;
