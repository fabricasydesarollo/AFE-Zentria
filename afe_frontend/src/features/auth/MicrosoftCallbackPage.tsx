import { useEffect, useState, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, Microsoft } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { setCredentials } from './authSlice';
import { zentriaColors } from '../../theme/colors';
import { microsoftAuthService } from '../../services/microsoftAuth.service';

/**
 * Microsoft OAuth Callback Page
 * Maneja el callback de Microsoft y completa la autenticación
 *
 * PROTECCIONES IMPLEMENTADAS:
 * 1. Previene doble ejecución por React StrictMode
 * 2. Limpia URL después de procesar para evitar re-procesamiento
 * 3. Usa navigate replace para prevenir volver atrás
 * 4. Detecta sesión activa y redirige automáticamente
 */

function MicrosoftCallbackPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');

  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  // Verificar si ya hay una sesión activa
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);

  // Ref para prevenir doble ejecución en React StrictMode
  const hasProcessedCallback = useRef(false);

  useEffect(() => {
    // PROTECCIÓN 1: Si ya hay sesión activa, redirigir inmediatamente
    // Esto previene intentar procesar el callback después de un "atrás"
    if (isAuthenticated) {
      console.log('✅ Sesión activa detectada, redirigiendo...');
      navigate('/dashboard', { replace: true });
      return;
    }

    // PROTECCIÓN 2: Prevenir ejecución múltiple del mismo código OAuth
    // React 18 StrictMode monta componentes 2 veces en desarrollo
    // Los códigos OAuth son de un solo uso
    if (hasProcessedCallback.current) {
      console.log('⚠️ Callback ya procesado, ignorando llamada duplicada');
      return;
    }

    const handleCallback = async () => {
      try {
        // Obtener parámetros del callback
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        // Si hay error en la URL
        if (error) {
          throw new Error(`Error de Microsoft: ${error}`);
        }

        // Validar parámetros
        if (!code || !state) {
          throw new Error('Parámetros de autenticación inválidos');
        }

        // MARCAR como procesado ANTES de la llamada async
        // Esto previene race conditions en StrictMode
        hasProcessedCallback.current = true;

        console.log('🔐 Procesando callback de Microsoft OAuth...');

        // PROTECCIÓN 3: Limpiar URL inmediatamente para prevenir re-procesamiento
        // Si el usuario presiona "atrás", no verá el código en la URL
        window.history.replaceState(
          {},
          document.title,
          window.location.pathname
        );

        // Procesar callback
        const authResponse = await microsoftAuthService.handleCallback(code, state);

        console.log('✅ Autenticación exitosa');

        // Guardar credenciales en Redux (con auth_provider para logout)
        dispatch(
          setCredentials({
            user: authResponse.user,
            token: authResponse.access_token,
            authProvider: 'microsoft',  // Marcar que es OAuth de Microsoft
          })
        );

        setStatus('success');

        // PROTECCIÓN 4: Usar replace para evitar que "atrás" vuelva al callback
        setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 1500);
      } catch (error: any) {
        console.error('❌ Error en callback de Microsoft:', error);
        setStatus('error');
        setErrorMessage(
          error.message || 'Error al procesar la autenticación con Microsoft'
        );
      }
    };

    handleCallback();
  }, [searchParams, dispatch, navigate, isAuthenticated]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `
          linear-gradient(135deg, #F5F5F5 0%, #FFFFFF 50%, #F0F0F0 100%),
          radial-gradient(circle at 20% 80%, rgba(128, 0, 106, 0.02) 0%, transparent 50%),
          radial-gradient(circle at 80% 20%, rgba(128, 0, 106, 0.01) 0%, transparent 50%)
        `,
        backgroundAttachment: 'fixed',
        px: 2,
      }}
    >
      <Card
        elevation={24}
        sx={{
          borderRadius: 5,
          maxWidth: 500,
          width: '100%',
          backdropFilter: 'blur(20px)',
          background: 'rgba(255, 255, 255, 0.98)',
          border: `2px solid ${zentriaColors.violeta.main}15`,
          boxShadow: `0 20px 60px ${zentriaColors.violeta.main}40`,
        }}
      >
        <CardContent sx={{ p: 6, textAlign: 'center' }}>
          {/* Estado: Cargando */}
          {status === 'loading' && (
            <>
              <Box
                sx={{
                  width: 80,
                  height: 80,
                  margin: '0 auto',
                  mb: 3,
                  background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                  borderRadius: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <CircularProgress size={40} sx={{ color: 'white' }} />
              </Box>
              <Typography variant="h5" fontWeight={700} color="text.primary" gutterBottom>
                Completando autenticación...
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Por favor, espere mientras procesamos su información de Microsoft.
              </Typography>
            </>
          )}

          {/* Estado: Éxito */}
          {status === 'success' && (
            <>
              <Box
                sx={{
                  width: 80,
                  height: 80,
                  margin: '0 auto',
                  mb: 3,
                  background: `linear-gradient(135deg, ${zentriaColors.verde.main}, ${zentriaColors.verde.dark})`,
                  borderRadius: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  animation: 'scaleIn 0.4s ease',
                  '@keyframes scaleIn': {
                    '0%': { transform: 'scale(0)' },
                    '100%': { transform: 'scale(1)' },
                  },
                }}
              >
                <CheckCircle sx={{ fontSize: 48, color: 'white' }} />
              </Box>
              <Typography variant="h5" fontWeight={700} color="text.primary" gutterBottom>
                ¡Autenticación exitosa!
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Redirigiendo al sistema...
              </Typography>
            </>
          )}

          {/* Estado: Error */}
          {status === 'error' && (
            <>
              <Box
                sx={{
                  width: 80,
                  height: 80,
                  margin: '0 auto',
                  mb: 3,
                  background: '#F44336',
                  borderRadius: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <ErrorIcon sx={{ fontSize: 48, color: 'white' }} />
              </Box>
              <Typography variant="h5" fontWeight={700} color="error" gutterBottom>
                Error de autenticación
              </Typography>
              <Alert severity="error" sx={{ mt: 3, textAlign: 'left', borderRadius: 2.5 }}>
                {errorMessage}
              </Alert>
              <Button
                fullWidth
                variant="contained"
                size="large"
                onClick={() => navigate('/login')}
                sx={{
                  mt: 3,
                  py: 1.8,
                  borderRadius: 3,
                  fontWeight: 700,
                  textTransform: 'none',
                  background: `linear-gradient(135deg, ${zentriaColors.violeta.main}, ${zentriaColors.naranja.main})`,
                  boxShadow: `0 8px 24px ${zentriaColors.violeta.main}40`,
                  '&:hover': {
                    background: `linear-gradient(135deg, ${zentriaColors.violeta.dark}, ${zentriaColors.naranja.dark})`,
                  },
                }}
              >
                Volver al Login
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}

export default MicrosoftCallbackPage;
