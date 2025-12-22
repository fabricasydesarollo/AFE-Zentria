/**
 * Professional confirmation dialog for delete actions
 * Shows a warning before deleting items with detailed information
 * Diseño profesional con colores corporativos Zentria
 */

import {
  Dialog,
  DialogContent,
  Button,
  Box,
  Typography,
  Alert,
  Stack,
  IconButton,
  Card,
  CardContent,
  Divider,
  CircularProgress,
} from '@mui/material';
import { Close, Warning, Delete, WarningAmber, Receipt } from '@mui/icons-material';
import { zentriaColors } from '../../theme/colors';

interface ConfirmDeleteDialogProps {
  open: boolean;
  title: string;
  itemName: string;
  itemDetails?: { label: string; value: string }[];
  warningMessage?: string;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
}

export const ConfirmDeleteDialog: React.FC<ConfirmDeleteDialogProps> = ({
  open,
  title,
  itemName,
  itemDetails = [],
  warningMessage,
  onClose,
  onConfirm,
  loading = false,
}) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
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
      {/* Header con Gradiente Corporativo Rojo/Naranja */}
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
            <WarningAmber sx={{ fontSize: 28 }} />
          </Box>
          <Box>
            <Typography variant="h5" fontWeight={700}>
              {title}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              Esta acción no se puede deshacer
            </Typography>
          </Box>
        </Stack>
        <IconButton
          onClick={onClose}
          disabled={loading}
          aria-label="Cerrar diálogo"
          sx={{
            color: 'white',
            backgroundColor: 'rgba(255, 255, 255, 0.15)',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.25)',
            },
            '&:disabled': {
              color: 'rgba(255, 255, 255, 0.5)',
            },
          }}
        >
          <Close />
        </IconButton>
      </Box>

      <DialogContent sx={{ p: 3, backgroundColor: '#fafafa' }}>
        {/* Alert de Confirmación Principal */}
        <Alert
          severity="error"
          icon={<WarningAmber sx={{ color: zentriaColors.naranja.main }} />}
          sx={{
            mb: 3,
            backgroundColor: `${zentriaColors.naranja.light}15`,
            border: `1px solid ${zentriaColors.naranja.light}`,
            borderRadius: 2,
            '& .MuiAlert-message': {
              color: '#333',
            },
          }}
        >
          <Typography variant="subtitle2" fontWeight={700} color="#333" gutterBottom>
            ¿Estás seguro que deseas eliminar este elemento?
          </Typography>
          {warningMessage && (
            <Typography variant="body2" color="#555" sx={{ mt: 1 }}>
              {warningMessage}
            </Typography>
          )}
        </Alert>

        {/* Tarjeta de Detalles del Item */}
        <Card
          elevation={0}
          sx={{
            mb: 3,
            backgroundColor: 'white',
            border: `1px solid ${zentriaColors.cinza}`,
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              background: `linear-gradient(135deg, ${zentriaColors.naranja.main}10 0%, ${zentriaColors.naranja.light}15 100%)`,
              p: 2,
              borderBottom: `1px solid ${zentriaColors.cinza}`,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <Receipt sx={{ color: zentriaColors.naranja.main, fontSize: 24 }} />
            <Typography variant="subtitle2" fontWeight={700} color={zentriaColors.naranja.main}>
              ELEMENTO A ELIMINAR
            </Typography>
          </Box>
          <CardContent sx={{ p: 2 }}>
            <Typography variant="h6" fontWeight={700} gutterBottom color="#333" sx={{ mb: 2 }}>
              {itemName}
            </Typography>

            {itemDetails.length > 0 && (
              <Stack spacing={2}>
                {itemDetails.map((detail, index) => (
                  <Box key={index}>
                    <Typography variant="caption" fontWeight={600} color="text.secondary">
                      {detail.label.toUpperCase()}
                    </Typography>
                    <Typography variant="body2" fontWeight={600} color="#333">
                      {detail.value}
                    </Typography>
                    {index < itemDetails.length - 1 && <Divider sx={{ mt: 1 }} />}
                  </Box>
                ))}
              </Stack>
            )}
          </CardContent>
        </Card>

        {/* Alert de Advertencia sobre Pérdida Permanente */}
        <Alert
          severity="warning"
          icon={<Warning sx={{ color: zentriaColors.amarillo.dark }} />}
          sx={{
            backgroundColor: `${zentriaColors.amarillo.light}15`,
            border: `1px solid ${zentriaColors.amarillo.light}`,
            borderRadius: 2,
            '& .MuiAlert-message': {
              color: '#333',
            },
          }}
        >
          <Typography variant="body2" fontWeight={600} color="#333">
            <strong>Nota:</strong> Esta acción eliminará permanentemente el registro de la base de datos.
            Todos los datos asociados se perderán.
          </Typography>
        </Alert>
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
          onClick={onClose}
          disabled={loading}
          variant="outlined"
          sx={{
            minWidth: 120,
            borderColor: zentriaColors.cinza,
            color: '#555',
            fontWeight: 600,
            '&:hover': {
              backgroundColor: '#f0f0f0',
              borderColor: zentriaColors.naranja.light,
            },
            '&:disabled': {
              color: '#999',
              borderColor: '#ddd',
            },
          }}
        >
          Cancelar
        </Button>
        <Button
          onClick={onConfirm}
          disabled={loading}
          variant="contained"
          sx={{
            minWidth: 160,
            background: `linear-gradient(135deg, ${zentriaColors.naranja.main} 0%, ${zentriaColors.naranja.dark} 100%)`,
            color: 'white',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            boxShadow: `0 4px 15px ${zentriaColors.naranja.main}40`,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              boxShadow: `0 6px 20px ${zentriaColors.naranja.main}60`,
              transform: 'translateY(-2px)',
            },
            '&:active': {
              transform: 'translateY(0)',
            },
            '&:disabled': {
              background: '#ccc',
              boxShadow: 'none',
              color: 'rgba(255, 255, 255, 0.7)',
            },
          }}
          startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <Delete />}
        >
          {loading ? 'Eliminando...' : 'Eliminar'}
        </Button>
      </Box>
    </Dialog>
  );
};
