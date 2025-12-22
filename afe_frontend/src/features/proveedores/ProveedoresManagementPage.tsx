/**
 * PÁGINA CONSOLIDADA DE GESTIÓN DE PROVEEDORES
 *
 * Componente empresarial único que maneja:
 * - Tab 1: CRUD completo de Proveedores
 * - Tab 2: Gestión de Asignaciones Responsable-Proveedor
 * - Tab 3: Vista por Responsable
 * - Tab 4: Vista por Proveedor
 *
 * @author Equipo de Desarrollo 
 * @version 2.0 - Versión consolidada
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  Tabs,
  Tab,
  Paper,
  Divider,
  Chip,
} from '@mui/material';
import {
  Business,
  Link as LinkIcon,
  Person,
  Store,
  Refresh,
} from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  fetchProveedores,
  fetchAsignaciones,
  selectProveedoresLoading,
  selectAsignacionesLoading,
  selectLastSync,
} from './proveedoresSlice';
import { hasPermission } from '../../constants/roles';
import ReadOnlyWrapper from '../../components/Auth/ReadOnlyWrapper';

// Importar tabs individuales
import ProveedoresTab from './tabs/ProveedoresTab';
import AsignacionesTab from './tabs/AsignacionesTab';
import PorResponsableTab from './tabs/PorResponsableTab';
import PorProveedorTab from './tabs/PorProveedorTab';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

/**
 * Página principal consolidada de gestión
 */
function ProveedoresManagementPage() {
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);
  const canManage = hasPermission(user?.rol || '', 'canManageProviders');

  const [tabValue, setTabValue] = useState(0);
  const proveedoresLoading = useAppSelector(selectProveedoresLoading);
  const asignacionesLoading = useAppSelector(selectAsignacionesLoading);
  const lastSync = useAppSelector(selectLastSync);

  // Cargar datos al montar
  useEffect(() => {
    handleRefreshAll();
  }, []);

  const handleRefreshAll = async () => {
    try {
      await Promise.all([
        dispatch(fetchProveedores({ skip: 0, limit: 1000 })).unwrap(),
        dispatch(fetchAsignaciones({ skip: 0, limit: 1000 })).unwrap(),
      ]);
    } catch (error: any) {
      // Error al actualizar datos
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const formatLastSync = (timestamp: string | null) => {
    if (!timestamp) return 'Nunca';
    const date = new Date(timestamp);
    return date.toLocaleString('es-CO', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const isLoading = proveedoresLoading || asignacionesLoading;

  return (
    <Box>
      {/* Header Principal */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            Gestión Integral de Proveedores
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Administración centralizada de proveedores y asignaciones
          </Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={2}>
          {lastSync && (
            <Chip
              label={`Última sync: ${formatLastSync(lastSync)}`}
              size="small"
              variant="outlined"
            />
          )}
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefreshAll}
            disabled={isLoading}
          >
            Actualizar Todo
          </Button>
        </Box>
      </Box>

      {/* Sistema de Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{
            '& .MuiTab-root': {
              minHeight: 64,
              fontSize: '0.95rem',
              fontWeight: 500,
            },
          }}
        >
          <Tab
            icon={<Store />}
            iconPosition="start"
            label="Proveedores"
            sx={{ textTransform: 'none' }}
          />
          <Tab
            icon={<LinkIcon />}
            iconPosition="start"
            label="Asignaciones"
            sx={{ textTransform: 'none' }}
          />
          <Tab
            icon={<Person />}
            iconPosition="start"
            label="Por Responsable"
            sx={{ textTransform: 'none' }}
          />
          <Tab
            icon={<Business />}
            iconPosition="start"
            label="Por Proveedor"
            sx={{ textTransform: 'none' }}
          />
        </Tabs>
      </Paper>

      {/* Contenido de los Tabs */}
      <ReadOnlyWrapper requiredPermission="canManageProviders">
        <TabPanel value={tabValue} index={0}>
          <ProveedoresTab />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <AsignacionesTab />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <PorResponsableTab />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <PorProveedorTab />
        </TabPanel>
      </ReadOnlyWrapper>
    </Box>
  );
}

export default ProveedoresManagementPage;
