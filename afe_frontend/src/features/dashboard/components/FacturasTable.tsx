/**
 * Facturas table component with pagination
 * FASE 2: Integración de sistema de pagos con control por rol
 */

import {
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  Box,
  Button,
} from '@mui/material';
import { Visibility, Edit, MoreVert, Description, Add } from '@mui/icons-material';
import { zentriaColors } from '../../../theme/colors';
import { actionButtonStyles, tooltipProps } from '../../../theme/buttonStyles';
import type { Factura, DialogMode } from '../types';
import { formatCurrency, formatDate, getEstadoColor, getEstadoLabel, getEstadoChipStyles } from '../utils';

interface FacturasTableProps {
  facturas: Factura[];
  page: number;
  rowsPerPage: number;
  onPageChange: (newPage: number) => void;
  onRowsPerPageChange: (newRowsPerPage: number) => void;
  onOpenDialog: (mode: DialogMode, factura: Factura) => void;
  onMenuClick: (event: React.MouseEvent<HTMLElement>, factura: Factura) => void;
  isAdmin?: boolean;
  isHistorico?: boolean;
}

export const FacturasTable: React.FC<FacturasTableProps> = ({
  facturas,
  page,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
  onOpenDialog,
  onMenuClick,
  isAdmin = false,
  isHistorico = false,
}) => {
  const paginatedFacturas = facturas.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
  const totalColumns = 9; // Fixed column count

  return (
    <Card>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow
              sx={{
                bgcolor: 'background.default',
                borderBottom: '2px solid',
                borderColor: zentriaColors.violeta.main,
              }}
            >
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Número
              </TableCell>
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Emisor
              </TableCell>
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                NIT
              </TableCell>
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Total a Pagar
              </TableCell>
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Fecha Emisión
              </TableCell>
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Estado
              </TableCell>
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Responsable
              </TableCell>
              <TableCell
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Acción Por
              </TableCell>

              <TableCell
                align="center"
                sx={{
                  color: 'text.primary',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  py: 2,
                }}
              >
                Acciones
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedFacturas.length > 0 ? (
              paginatedFacturas.map((factura) => (
                <TableRow key={factura.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {factura.numero_factura || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>{factura.nombre_emisor || '-'}</TableCell>
                  <TableCell>{factura.nit_emisor || '-'}</TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight={700} color="#1a1a1a">
                      {formatCurrency(factura.monto_total || 0)}
                    </Typography>
                  </TableCell>
                  <TableCell>{formatDate(factura.fecha_emision)}</TableCell>
                  <TableCell>
                    <Chip
                      label={getEstadoLabel(factura.estado)}
                      color={getEstadoColor(factura.estado)}
                      size="small"
                      sx={getEstadoChipStyles(factura.estado)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {factura.nombre_responsable || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {factura.accion_por ? (
                      <Box>
                        <Typography variant="body2" fontWeight={600}>
                          {factura.accion_por}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {factura.fecha_accion ? formatDate(factura.fecha_accion) : ''}
                        </Typography>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.disabled">
                        -
                      </Typography>
                    )}
                  </TableCell>

                  <TableCell align="center">
                    <Tooltip title={`Ver detalles de la factura ${factura.numero_factura}`} {...tooltipProps}>
                      <IconButton
                        size="small"
                        onClick={() => onOpenDialog('view', factura)}
                        aria-label={`Ver detalles de la factura ${factura.numero_factura}`}
                        sx={actionButtonStyles.view}
                      >
                        <Visibility fontSize="small" />
                      </IconButton>
                    </Tooltip>

                    {isAdmin && !isHistorico && (
                      <>
                        <Tooltip title={`Editar factura ${factura.numero_factura}`} {...tooltipProps}>
                          <IconButton
                            size="small"
                            onClick={() => onOpenDialog('edit', factura)}
                            aria-label={`Editar factura ${factura.numero_factura}`}
                            sx={actionButtonStyles.edit}
                          >
                            <Edit fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Más acciones (aprobar, rechazar, eliminar)" {...tooltipProps}>
                          <IconButton
                            size="small"
                            onClick={(e) => onMenuClick(e, factura)}
                            aria-label={`Más acciones para factura ${factura.numero_factura}`}
                            sx={actionButtonStyles.more}
                          >
                            <MoreVert fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={totalColumns} align="center">
                  <Box
                    sx={{
                      py: 8,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 2,
                    }}
                  >
                    {/* Icono ilustrativo */}
                    <Box
                      sx={{
                        width: 80,
                        height: 80,
                        borderRadius: '50%',
                        bgcolor: 'background.default',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: '2px solid',
                        borderColor: 'divider',
                      }}
                    >
                      <Description sx={{ fontSize: 40, color: 'text.disabled' }} />
                    </Box>

                    {/* Mensaje principal */}
                    <Typography variant="h6" color="text.secondary" fontWeight={600}>
                      No se encontraron facturas
                    </Typography>

                    {/* Mensaje secundario */}
                    <Typography variant="body2" color="text.secondary" maxWidth={400} textAlign="center">
                      No hay facturas que coincidan con los filtros actuales. Intenta ajustar los criterios de búsqueda.
                    </Typography>

                    {/* Acción sugerida para admin */}
                    {isAdmin && (
                      <Button
                        variant="contained"
                        startIcon={<Add />}
                        onClick={() => onOpenDialog('create', {} as Factura)}
                        sx={{
                          mt: 2,
                          background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                          textTransform: 'none',
                          fontWeight: 600,
                          px: 3,
                        }}
                      >
                        Crear Primera Factura
                      </Button>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={facturas.length}
        page={page}
        onPageChange={(_, newPage) => onPageChange(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => onRowsPerPageChange(parseInt(e.target.value, 10))}
        labelRowsPerPage="Filas por página:"
      />
    </Card>
  );
};
