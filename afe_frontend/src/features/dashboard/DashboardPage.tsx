/**
 * DashboardPage - Main dashboard container
 * Refactored to use modular components, custom hooks, and services
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Select,
  MenuItem,
  FormControl,
  Stack,
} from '@mui/material';
import { Refresh, Add, ChevronLeft, ChevronRight, Warning as WarningIcon } from '@mui/icons-material';
import { useAppSelector } from '../../app/hooks';
import { zentriaColors } from '../../theme/colors';
import apiClient from '../../services/api';

// Feature imports
import {
  StatsCards,
  FilterBar,
  FacturasTable,
  FacturaFormModal,
  FacturaActionsMenu,
  ChartsSection,
  AlertaMes,
} from './components';
import { useDashboardData, useFacturaDialog } from './hooks';
import { facturasService } from './services/facturas.service';
import type { Factura, EstadoFactura, VistaFacturas, FacturaFormData } from './types';
import { DEFAULT_ROWS_PER_PAGE } from './constants';

// Import the professional modals from Facturas feature
import FacturaDetailModal from '../../components/Facturas/FacturaDetailModal';
import ApprovalDialog from '../../components/Facturas/ApprovalDialog';
import RejectionDialog from '../../components/Facturas/RejectionDialog';
import { ConfirmDeleteDialog } from '../../components/Dialogs/ConfirmDeleteDialog';
import { GrupoSelector } from '../../components/Grupos/GrupoSelector';

function DashboardPage() {
  const user = useAppSelector((state) => state.auth.user);

  // Período state - Selector de mes/año
  const hoy = new Date();
  const mesActual = hoy.getMonth() + 1;
  const anioActual = hoy.getFullYear();

  const [mesSeleccionado, setMesSeleccionado] = useState<number>(mesActual);
  const [anioSeleccionado, setAnioSeleccionado] = useState<number>(anioActual);

  // Detectar si estamos viendo un período histórico (mes pasado)
  const isHistorico = mesSeleccionado !== mesActual || anioSeleccionado !== anioActual;

  // Filter and pagination state
  const [searchTerm, setSearchTerm] = useState('');
  const [filterEstado, setFilterEstado] = useState<EstadoFactura | 'todos'>('todos');
  const [vistaFacturas, setVistaFacturas] = useState<VistaFacturas>('todas');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(DEFAULT_ROWS_PER_PAGE);

  // Menu state
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [menuFactura, setMenuFactura] = useState<Factura | null>(null);
  const [actionError, setActionError] = useState('');

  // Approval/Rejection dialogs state
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [rejectionDialogOpen, setRejectionDialogOpen] = useState(false);
  const [selectedFacturaForAction, setSelectedFacturaForAction] = useState<Factura | null>(null);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [rejectionLoading, setRejectionLoading] = useState(false);

  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [facturaToDelete, setFacturaToDelete] = useState<Factura | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Cuarentena state (MULTI-TENANT 2025-12-14)
  const [facturasCuarentena, setFacturasCuarentena] = useState<number>(0);

  // Custom hooks
  const {
    facturas,
    stats,
    totalTodasFacturas,
    totalAsignadas,
    loading,
    error,
    loadData,
    clearError,
  } = useDashboardData({
    userRole: user?.rol,
    filterEstado,
    vistaFacturas,
    mesSeleccionado,
    anioSeleccionado,
  });

  const {
    openDialog,
    dialogMode,
    selectedFactura,
    formData,
    setFormData,
    openDialogWith,
    closeDialog,
  } = useFacturaDialog();

  // Search filter
  const filteredFacturas = facturas.filter(
    (factura) =>
      factura?.numero_factura?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      factura?.nombre_emisor?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      factura?.nit_emisor?.includes(searchTerm)
  );

  // Constantes de meses
  const MESES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  const nombreMesActual = MESES[mesActual - 1];
  const nombreMesSeleccionado = MESES[mesSeleccionado - 1];

  // Cargar contador de facturas en cuarentena (solo SuperAdmin)
  useEffect(() => {
    const cargarCuarentena = async () => {
      if (user?.rol === 'superadmin') {
        try {
          const response = await apiClient.get('/facturas/all');
          // Filtrar facturas con estado en_cuarentena
          const facturasCuarentena = Array.isArray(response.data)
            ? response.data.filter((f: any) => f.estado === 'en_cuarentena')
            : [];
          setFacturasCuarentena(facturasCuarentena.length);
        } catch (error) {
          console.error('Error cargando facturas en cuarentena:', error);
        }
      }
    };

    cargarCuarentena();
  }, [user?.rol]);

  // Handlers
  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setPage(0);
  };

  const handleRowsPerPageChange = (newRowsPerPage: number) => {
    setRowsPerPage(newRowsPerPage);
    setPage(0);
  };

  // Handlers para selector de período
  const handleMesAnterior = () => {
    if (mesSeleccionado === 1) {
      setMesSeleccionado(12);
      setAnioSeleccionado(anioSeleccionado - 1);
    } else {
      setMesSeleccionado(mesSeleccionado - 1);
    }
    setPage(0);
  };

  const handleMesSiguiente = () => {
    if (mesSeleccionado === 12) {
      setMesSeleccionado(1);
      setAnioSeleccionado(anioSeleccionado + 1);
    } else {
      setMesSeleccionado(mesSeleccionado + 1);
    }
    setPage(0);
  };

  const handleVolverAlMesActual = () => {
    setMesSeleccionado(mesActual);
    setAnioSeleccionado(anioActual);
    setPage(0);
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, factura: Factura) => {
    setAnchorEl(event.currentTarget);
    setMenuFactura(factura);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setMenuFactura(null);
  };

  const handleFormChange = (field: keyof FacturaFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    try {
      if (dialogMode === 'create') {
        await facturasService.createFactura(formData);
      } else if (dialogMode === 'edit' && selectedFactura) {
        await facturasService.updateFactura(selectedFactura.id, formData);
      }
      closeDialog();
      await loadData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al guardar factura');
    }
  };

  const handleDelete = (factura: Factura) => {
    setFacturaToDelete(factura);
    setDeleteDialogOpen(true);
    handleMenuClose();
  };

  const handleConfirmDelete = async () => {
    if (!facturaToDelete) return;

    setDeleteLoading(true);
    try {
      await facturasService.deleteFactura(facturaToDelete.id);
      await loadData();
      setDeleteDialogOpen(false);
      setFacturaToDelete(null);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al eliminar factura');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false);
    setFacturaToDelete(null);
  };

  const handleApprove = (factura: Factura) => {
    setSelectedFacturaForAction(factura);
    setApprovalDialogOpen(true);
    handleMenuClose();
  };

  const handleReject = (factura: Factura) => {
    setSelectedFacturaForAction(factura);
    setRejectionDialogOpen(true);
    handleMenuClose();
  };

  const handleConfirmApproval = async (observaciones?: string) => {
    if (!selectedFacturaForAction) return;

    setApprovalLoading(true);
    try {
      // IMPORTANTE: Enviar el nombre completo del usuario, no el username
      const approverName = typeof user?.nombre === 'string' && user.nombre.trim() ? user.nombre : user?.usuario || '';
      await facturasService.approveFactura(selectedFacturaForAction.id, approverName, observaciones);
      setApprovalDialogOpen(false);
      setSelectedFacturaForAction(null);

      // Esperar a que el backend complete la transacción
      await new Promise(resolve => setTimeout(resolve, 500));

      // Mantener el filtro actual - solo recargar datos
      // La factura desaparecerá automáticamente si ya no cumple el filtro
      await loadData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al aprobar factura');
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleConfirmRejection = async (motivo: string, detalle?: string) => {
    if (!selectedFacturaForAction) return;

    setRejectionLoading(true);
    try {
      // IMPORTANTE: Enviar el nombre completo del usuario, no el username
      const rejectorName = typeof user?.nombre === 'string' && user.nombre.trim() ? user.nombre : user?.usuario || '';
      await facturasService.rejectFactura(selectedFacturaForAction.id, rejectorName, motivo, detalle);
      setRejectionDialogOpen(false);
      setSelectedFacturaForAction(null);

      // Esperar a que el backend complete la transacción
      await new Promise(resolve => setTimeout(resolve, 500));

      // Mantener el filtro actual - solo recargar datos
      // La factura desaparecerá automáticamente si ya no cumple el filtro
      await loadData();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Error al rechazar factura');
    } finally {
      setRejectionLoading(false);
    }
  };

  const handleExport = () => {
    const url = facturasService.getExportUrl(
      filterEstado,
      user?.rol === 'admin' && vistaFacturas === 'asignadas'
    );
    window.location.href = apiClient.defaults.baseURL + url;
  };

  // Transform dashboard Factura to format expected by FacturaDetailModal
  const transformFacturaForModal = (factura: Factura | null) => {
    if (!factura) return null;

    return {
      id: 0,
      factura_id: factura.id,
      estado: factura.estado as any,
      responsable_id: 0,
      es_identica_mes_anterior: false,
      porcentaje_similitud: undefined,
      diferencias_detectadas: [],
      factura_referencia: undefined,
      factura: {
        id: factura.id,
        numero_factura: factura.numero_factura,
        cufe: factura.cufe || '',
        fecha_emision: factura.fecha_emision,
        fecha_vencimiento: factura.fecha_vencimiento,
        proveedor_id: null,
        proveedor: {
          id: 0,
          nit: factura.nit_emisor,
          razon_social: factura.nombre_emisor,
        },
        proveedor_nombre: factura.nombre_emisor,
        nit: factura.nit_emisor,
        subtotal: factura.monto_total * 0.84, // Aproximación: 84% del total (sin IVA 19%)
        iva: factura.monto_total * 0.16, // Aproximación: 16% del total (IVA 19%)
        total: factura.monto_total,
        total_a_pagar: factura.monto_total,
        moneda: 'COP',
        estado: factura.estado as any,
        observaciones: factura.observaciones,
      },
    } as any;
  };

  // Initial loading state (only on first load)
  const isInitialLoad = loading && facturas.length === 0;

  if (isInitialLoad) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress size={60} sx={{ color: zentriaColors.violeta.main }} />
      </Box>
    );
  }

  // Detectar si SuperAdmin está en vista global o grupo específico
  const grupoIdStorage = localStorage.getItem('grupo_id');
  const esVistaGlobal = !grupoIdStorage;

  return (
    <Box>
      {/* Indicador de modo solo lectura para SuperAdmin */}
      {user?.rol === 'superadmin' && (
        <Alert
          severity="info"
          sx={{
            mb: 3,
            borderLeft: `4px solid ${zentriaColors.violeta.main}`,
            backgroundColor: 'rgba(128, 0, 106, 0.05)',
            '& .MuiAlert-icon': {
              color: zentriaColors.violeta.main,
            },
          }}
        >
          <Typography variant="body2" fontWeight={600} component="div">
            <strong>Vista Operacional - Modo Solo Lectura</strong>
            {esVistaGlobal && (
              <Chip
                label="Vista Global"
                size="small"
                sx={{
                  ml: 1,
                  background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                  color: 'white',
                  fontWeight: 700,
                }}
              />
            )}
          </Typography>
          <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
            {esVistaGlobal ? (
              <>
                Viendo facturas de <strong>todos los grupos</strong>. Puedes seleccionar un grupo específico para análisis detallado.
                Como SuperAdmin, no puedes realizar acciones operacionales (aprobar/rechazar).
              </>
            ) : (
              <>
                Como SuperAdmin, puedes visualizar todas las facturas pero no realizar acciones operacionales (aprobar/rechazar).
                Para administración del sistema, usa el Dashboard Admin.
              </>
            )}
          </Typography>
        </Alert>
      )}

      {/* MULTI-TENANT 2025-12-14: Facturas en Cuarentena */}
      {user?.rol === 'superadmin' && facturasCuarentena > 0 && (
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
          action={
            <Button
              color="inherit"
              size="small"
              href="/email-config?tab=cuarentena"
              sx={{
                fontWeight: 600,
                textTransform: 'none',
                '&:hover': {
                  backgroundColor: 'rgba(255, 152, 0, 0.1)',
                },
              }}
            >
              Ver Facturas
            </Button>
          }
        >
          <Typography variant="body1" fontWeight="bold" component="div">
            {facturasCuarentena} factura{facturasCuarentena !== 1 ? 's' : ''} en cuarentena
          </Typography>
          <Typography variant="body2" component="div">
            Estas facturas no tienen grupo asignado porque sus NITs no están configurados.
            Configure los NITs en "Configuración de Correos" para procesarlas automáticamente.
          </Typography>
        </Alert>
      )}

      {/* Campana de alerta de fin de mes - Siempre visible en la parte superior */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <AlertaMes />
      </Box>

      {/* Header - Responsive: Vertical on mobile, Horizontal on desktop */}
      <Box
        display="flex"
        flexDirection={{ xs: 'column', md: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'flex-start', md: 'center' }}
        gap={{ xs: 3, md: 2 }}
        mb={{ xs: 3, md: 4 }}
      >
        <Box flex={1}>
          <Typography
            variant="h3"
            fontWeight={800}
            sx={{
              fontSize: '2rem',  // 24px - Explícito para sobrescribir el tema compacto
              background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={1} fontWeight={600}>
            • Vista operacional de facturas
          </Typography>

          {/* Selector de grupos multi-tenant - SOLO en Dashboard */}
          <Box sx={{ mt: 2 }}>
            <GrupoSelector />
          </Box>
        </Box>
        <Box
          display="flex"
          flexDirection={{ xs: 'column', sm: 'row' }}
          gap={2}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          width={{ xs: '100%', sm: 'auto' }}
        >
          <Button
            variant="outlined"
            startIcon={loading ? <CircularProgress size={18} /> : <Refresh />}
            onClick={loadData}
            disabled={loading}
            sx={{
              borderColor: zentriaColors.violeta.main + (loading ? '40' : ''),
              color: zentriaColors.violeta.main,
              fontWeight: 600,
              minWidth: { xs: 'auto', sm: 120 },
              width: { xs: '100%', sm: 'auto' },
              transition: 'all 0.2s ease',
              py: { xs: 1.2, sm: 1 },
              '&:hover': {
                borderColor: zentriaColors.violeta.main,
                bgcolor: zentriaColors.violeta.main + '08',
              },
              '&.Mui-disabled': {
                borderColor: zentriaColors.violeta.main + '40',
                color: zentriaColors.violeta.main + '60',
              }
            }}
          >
            {loading ? 'Actualizando...' : 'Actualizar'}
          </Button>

          {/* Selector de Período Premium */}
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            alignItems="center"
            sx={{
              p: { xs: 1.5, sm: 1 },
              backgroundColor: 'rgba(128, 0, 106, 0.04)',
              borderRadius: '8px',
              border: `1px solid rgba(128, 0, 106, 0.1)`,
              minWidth: { xs: '100%', sm: 'auto' },
            }}
          >
            <Button
              size="small"
              variant="text"
              startIcon={<ChevronLeft />}
              onClick={handleMesAnterior}
              sx={{
                color: zentriaColors.violeta.main,
                fontWeight: 600,
                '&:hover': { bgcolor: zentriaColors.violeta.main + '10' },
              }}
            >
              Ant.
            </Button>

            <Chip
              label={`${nombreMesSeleccionado} ${anioSeleccionado}`}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                color: 'white',
                fontWeight: 700,
                height: 32,
                minWidth: 160,
              }}
            />

            <Button
              size="small"
              variant="text"
              endIcon={<ChevronRight />}
              onClick={handleMesSiguiente}
              sx={{
                color: zentriaColors.violeta.main,
                fontWeight: 600,
                '&:hover': { bgcolor: zentriaColors.violeta.main + '10' },
              }}
            >
              Sig.
            </Button>

            {isHistorico && (
              <Button
                size="small"
                variant="outlined"
                onClick={handleVolverAlMesActual}
                sx={{
                  borderColor: zentriaColors.naranja.main,
                  color: zentriaColors.naranja.main,
                  fontWeight: 600,
                  fontSize: '0.75rem',
                  py: 0.5,
                  '&:hover': {
                    borderColor: zentriaColors.naranja.main,
                    bgcolor: zentriaColors.naranja.main + '10',
                  },
                }}
              >
                Hoy
              </Button>
            )}
          </Stack>
          {user?.rol === 'admin' && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => openDialogWith('create')}
              sx={{
                background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                boxShadow: '0 4px 14px rgba(128, 0, 106, 0.25)',
                fontWeight: 700,
                textTransform: 'none',
                width: { xs: '100%', sm: 'auto' },
                px: { xs: 2, sm: 3 },
                py: { xs: 1.2, sm: 1 },
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: '0 8px 20px rgba(128, 0, 106, 0.35)',
                },
                '&:active': {
                  transform: 'translateY(0)',
                }
              }}
            >
              Nueva Factura
            </Button>
          )}
        </Box>
      </Box>

      {/* Statistics Cards */}
      <StatsCards
        stats={stats}
        onCardClick={(filter) => {
          setFilterEstado(filter as EstadoFactura | 'todos');
          setPage(0);
        }}
      />

      {/* Charts Section - NEW! */}
      <ChartsSection stats={stats} />

      {/* Filters and Search */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={handleSearch}
        filterEstado={filterEstado}
        onFilterEstadoChange={setFilterEstado}
        vistaFacturas={vistaFacturas}
        onVistaFacturasChange={setVistaFacturas}
        totalTodasFacturas={totalTodasFacturas}
        totalAsignadas={totalAsignadas}
        onExport={handleExport}
        isAdmin={user?.rol === 'admin'}
      />

      {/* Error Messages */}
      {error && (
        <Alert severity="error" onClose={clearError} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {actionError && (
        <Alert severity="error" onClose={() => setActionError('')} sx={{ mb: 2 }}>
          {actionError}
        </Alert>
      )}

      {/* Facturas Table */}
      <FacturasTable
        facturas={filteredFacturas}
        page={page}
        rowsPerPage={rowsPerPage}
        onPageChange={setPage}
        onRowsPerPageChange={handleRowsPerPageChange}
        onOpenDialog={openDialogWith}
        onMenuClick={handleMenuClick}
        isAdmin={(user?.rol === 'admin' || user?.rol === 'responsable') && user?.rol !== 'superadmin'}
        isHistorico={isHistorico}
      />

      {/* Actions Menu */}
      <FacturaActionsMenu
        anchorEl={anchorEl}
        factura={menuFactura}
        userRole={user?.rol}
        onClose={handleMenuClose}
        onApprove={handleApprove}
        onReject={handleReject}
        onDelete={handleDelete}
        isHistorico={isHistorico}
      />

      {/* Professional Modals */}
      {dialogMode === 'view' ? (
        <FacturaDetailModal
          open={openDialog}
          onClose={closeDialog}
          workflow={transformFacturaForModal(selectedFactura)}
        />
      ) : (
        <FacturaFormModal
          open={openDialog}
          mode={dialogMode}
          formData={formData}
          onFormChange={handleFormChange}
          onClose={closeDialog}
          onSave={handleSave}
          error={actionError}
        />
      )}

      {/* Approval Dialog */}
      <ApprovalDialog
        open={approvalDialogOpen}
        onClose={() => setApprovalDialogOpen(false)}
        facturaNumero={selectedFacturaForAction?.numero_factura || ''}
        onConfirm={handleConfirmApproval}
        loading={approvalLoading}
      />

      {/* Rejection Dialog */}
      <RejectionDialog
        open={rejectionDialogOpen}
        onClose={() => setRejectionDialogOpen(false)}
        facturaNumero={selectedFacturaForAction?.numero_factura || ''}
        onConfirm={handleConfirmRejection}
        loading={rejectionLoading}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDeleteDialog
        open={deleteDialogOpen}
        title="Eliminar Factura"
        itemName={facturaToDelete?.numero_factura || ''}
        itemDetails={facturaToDelete ? [
          { label: 'Emisor', value: facturaToDelete.nombre_emisor },
          { label: 'NIT', value: facturaToDelete.nit_emisor },
          { label: 'Monto', value: new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(facturaToDelete.monto_total) },
          { label: 'Estado', value: facturaToDelete.estado },
        ] : []}
        warningMessage="Se eliminarán todos los registros asociados a esta factura (workflow, aprobaciones, etc.)"
        onClose={handleCancelDelete}
        onConfirm={handleConfirmDelete}
        loading={deleteLoading}
      />

    </Box>
  );
}

export default DashboardPage;
