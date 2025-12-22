import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  IconButton,
  CircularProgress,
  Fade,
  Slide,
  Snackbar,
  Link,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Collapse,
  Stack,
  Chip,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Lock,
  Person,
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  Info,
  Email,
  Business,
  Shield,
  Security,
  VerifiedUser,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../../app/hooks';
import { setCredentials } from './authSlice';
import { zentriaColors } from '../../theme/colors';
import apiClient from '../../services/api';
import { microsoftAuthService } from '../../services/microsoftAuth.service';

/**
 * ZENTRIA AFE -  Login Page
 * Diseño corporativo Fortune 500 ULTRA MEJORADO
 *
 * Features:
 * - Microsoft OAuth con diseño premium
 * - Glassmorphism y efectos neumórficos
 * - Animación de partículas de fondo
 * - Jerarquía visual espectacular
 * - Smart alerts y rate limiting
 * - Password recovery
 */

interface Notification {
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
}

// Icono oficial de Microsoft
const MicrosoftIcon = () => (
  <svg width="21" height="21" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="10" height="10" fill="#F25022" />
    <rect x="11" width="10" height="10" fill="#7FBA00" />
    <rect y="11" width="10" height="10" fill="#00A4EF" />
    <rect x="11" y="11" width="10" height="10" fill="#FFB900" />
  </svg>
);

function LoginPage() {
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [microsoftLoading, setMicrosoftLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loginAttempts, setLoginAttempts] = useState(0);
  const [isLocked, setIsLocked] = useState(false);
  const [lockTimeRemaining, setLockTimeRemaining] = useState(0);
  const [openForgotPassword, setOpenForgotPassword] = useState(false);
  const [recoveryEmail, setRecoveryEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [usuarioError, setUsuarioError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [loginError, setLoginError] = useState('');

  const [notification, setNotification] = useState<Notification>({
    open: false,
    message: '',
    severity: 'info',
  });

  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  // Manejo del temporizador de bloqueo
  useEffect(() => {
    if (lockTimeRemaining > 0) {
      const timer = setTimeout(() => {
        setLockTimeRemaining(lockTimeRemaining - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (lockTimeRemaining === 0 && isLocked) {
      setIsLocked(false);
      setLoginAttempts(0);
      showNotification('Su cuenta ha sido desbloqueada. Puede intentar nuevamente.', 'info');
    }
  }, [lockTimeRemaining, isLocked]);

  const showNotification = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setNotification({ open: true, message, severity });
  };

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  const validateForm = (): boolean => {
    let isValid = true;
    setUsuarioError('');
    setPasswordError('');

    if (!usuario.trim()) {
      setUsuarioError('El usuario es requerido');
      isValid = false;
    } else if (usuario.length < 3) {
      setUsuarioError('El usuario debe tener al menos 3 caracteres');
      isValid = false;
    }

    if (!password) {
      setPasswordError('La contraseña es requerida');
      isValid = false;
    } else if (password.length < 6) {
      setPasswordError('La contraseña debe tener al menos 6 caracteres');
      isValid = false;
    }

    return isValid;
  };

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }

    setLoginError('');

    if (isLocked) {
      const errorMsg = `Cuenta bloqueada temporalmente. Intente nuevamente en ${lockTimeRemaining} segundos.`;
      showNotification(errorMsg, 'warning');
      setLoginError(errorMsg);
      return;
    }

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const response = await apiClient.post('/auth/login', {
        usuario,
        password,
      });

      dispatch(
        setCredentials({
          user: response.data.user,
          token: response.data.access_token,
        })
      );

      showNotification('¡Inicio de sesión exitoso! Redirigiendo...', 'success');
      setLoginAttempts(0);
      setLoginError('');

      setTimeout(() => {
        navigate('/dashboard');
      }, 800);
    } catch (err: any) {
      setLoading(false);

      const newAttempts = loginAttempts + 1;
      setLoginAttempts(newAttempts);

      let errorMessage = 'Error al iniciar sesión';
      let severity: 'error' | 'warning' = 'error';

      if (err.response?.status === 401) {
        errorMessage = 'Usuario o contraseña incorrectos';

        const remainingAttempts = 5 - newAttempts;
        if (remainingAttempts > 0 && remainingAttempts <= 2) {
          errorMessage += `. Le quedan ${remainingAttempts} intento${remainingAttempts > 1 ? 's' : ''}`;
          severity = 'warning';
        }

        if (newAttempts >= 5) {
          setIsLocked(true);
          setLockTimeRemaining(300);
          errorMessage =
            'Demasiados intentos fallidos. Su cuenta ha sido bloqueada temporalmente por 5 minutos.';
          severity = 'error';
        }
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }

      setLoginError(errorMessage);
      showNotification(errorMessage, severity);
    }
  };

  const handleMicrosoftLogin = async () => {
    try {
      setMicrosoftLoading(true);
      await microsoftAuthService.loginWithMicrosoft();
    } catch (error: any) {
      setMicrosoftLoading(false);
      const message = error.message || 'Error al iniciar sesión con Microsoft';
      showNotification(message, 'error');
    }
  };

  const handleForgotPassword = async () => {
    setEmailError('');

    if (!recoveryEmail.trim()) {
      setEmailError('El correo electrónico es requerido');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(recoveryEmail)) {
      setEmailError('Por favor ingrese un correo electrónico válido');
      return;
    }

    try {
      await apiClient.post('/auth/recuperar', { email: recoveryEmail });
      showNotification(
        'Se ha enviado un enlace de recuperación a su correo electrónico. Por favor revise su bandeja de entrada.',
        'success'
      );
      setOpenForgotPassword(false);
      setRecoveryEmail('');
    } catch (err: any) {
      let errorMessage = 'Error al enviar el enlace de recuperación';
      if (err.response?.status === 404) {
        errorMessage = 'No se encontró ninguna cuenta asociada a este correo electrónico';
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      setEmailError(errorMessage);
      showNotification(errorMessage, 'error');
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'auto',
        // Fondo premium con patrón sutil
        background: `
          linear-gradient(135deg, #FAFBFC 0%, #FFFFFF 50%, #F8F9FA 100%),
          radial-gradient(circle at 20% 80%, rgba(128, 0, 106, 0.03) 0%, transparent 50%),
          radial-gradient(circle at 80% 20%, rgba(128, 0, 106, 0.02) 0%, transparent 50%)
        `,
        backgroundAttachment: 'fixed',
        px: 2,
        py: { xs: 3, md: 2 },
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: `
            linear-gradient(0deg, transparent 24%, rgba(128, 0, 106, 0.015) 25%, rgba(128, 0, 106, 0.015) 26%, transparent 27%, transparent 74%, rgba(128, 0, 106, 0.015) 75%, rgba(128, 0, 106, 0.015) 76%, transparent 77%, transparent),
            linear-gradient(90deg, transparent 24%, rgba(128, 0, 106, 0.015) 25%, rgba(128, 0, 106, 0.015) 26%, transparent 27%, transparent 74%, rgba(128, 0, 106, 0.015) 75%, rgba(128, 0, 106, 0.015) 76%, transparent 77%, transparent)
          `,
          backgroundSize: '50px 50px',
          pointerEvents: 'none',
        },
      }}
    >
      {/* Patrón de fondo sutil - versión corporativa ZENTRIA */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          opacity: 0.06,
          backgroundImage: `
            radial-gradient(ellipse at 20% 30%, #80006A20 0%, transparent 50%),
            radial-gradient(ellipse at 80% 70%, #A65C9918 0%, transparent 50%)
          `,
          backdropFilter: 'blur(80px)',
        }}
      />

      {/* Partículas flotantes sutiles - colores ZENTRIA */}
      <Box
        sx={{
          position: 'absolute',
          top: '15%',
          left: '10%',
          width: 140,
          height: 140,
          borderRadius: '50%',
          background: 'radial-gradient(circle, #80006A12, transparent 70%)',
          filter: 'blur(50px)',
          opacity: 0.35,
          animation: 'float1 12s ease-in-out infinite',
          '@keyframes float1': {
            '0%, 100%': { transform: 'translate(0, 0)' },
            '50%': { transform: 'translate(20px, -20px)' },
          },
        }}
      />

      <Box
        sx={{
          position: 'absolute',
          bottom: '15%',
          right: '10%',
          width: 160,
          height: 160,
          borderRadius: '50%',
          background: 'radial-gradient(circle, #FFB5A615, transparent 70%)',
          filter: 'blur(55px)',
          opacity: 0.3,
          animation: 'float2 14s ease-in-out infinite',
          '@keyframes float2': {
            '0%, 100%': { transform: 'translate(0, 0)' },
            '50%': { transform: 'translate(-25px, 15px)' },
          },
        }}
      />

      {/* Card principal con glassmorphism premium - Tamaño empresarial compacto */}
      <Box
        sx={{
          zIndex: 1,
          width: '100%',
          maxWidth: { xs: '95%', sm: 380, md: 580, lg: 620, xl: 680 },
          my: { xs: 1, md: 0 },
        }}
      >
        <Slide direction="down" in={true} timeout={1000}>
          <Card
            elevation={0}
            sx={{
              borderRadius: '24px',
              width: '100%',
              backdropFilter: 'blur(40px) saturate(200%)',
              background: '#FFFFFF',
              border: '1px solid rgba(128, 0, 106, 0.1)',
              boxShadow: `
                0 40px 100px rgba(0, 0, 0, 0.18),
                0 20px 50px rgba(128, 0, 106, 0.15),
                0 8px 24px rgba(0, 0, 0, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.8)
              `,
              position: 'relative',
              overflow: 'hidden',
              transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
              '&:hover': {
                boxShadow: `
                  0 50px 120px rgba(0, 0, 0, 0.25),
                  0 25px 65px rgba(128, 0, 106, 0.2),
                  0 12px 30px rgba(0, 0, 0, 0.15),
                  inset 0 1px 0 rgba(255, 255, 255, 0.8)
                `,
              },
              '&::after': {
                content: '""',
                position: 'absolute',
                top: -2,
                left: -2,
                right: -2,
                bottom: -2,
                borderRadius: '26px',
                background: 'linear-gradient(135deg, rgba(128, 0, 106, 0.12), rgba(166, 92, 153, 0.12))',
                zIndex: -1,
                filter: 'blur(20px)',
                opacity: 0.8,
              },
            }}
          >
            <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
              {/* LAYOUT RESPONSIVO: Vertical hasta tablet, Horizontal en laptop+ */}
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: { xs: 'column', md: 'row' },
                  minHeight: { md: 380, lg: 400, xl: 420 },
                }}
              >
                {/* PANEL IZQUIERDO - BRANDING (más estrecho) - PREMIUM */}
                <Box
                  sx={{
                    flex: { xs: 'none', md: '0 0 44%', lg: '0 0 44%' },
                    // Degradado premium refinado
                    background: {
                      xs: 'linear-gradient(135deg, #7B1FA2 0%, #80006A 100%)',
                      md: 'linear-gradient(135deg, #6B0A8E 0%, #7B1FA2 35%, #80006A 70%, #7B1FA2 100%)',
                    },
                    borderRadius: { xs: '24px 24px 0 0', md: '24px 0 0 0' },
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    p: { xs: 2, sm: 2, md: 1.5, lg: 2, xl: 2.25 },
                    position: 'relative',
                    overflow: 'hidden',
                    boxShadow: 'inset 0 -20px 40px rgba(0, 0, 0, 0.15)',
                  }}
                >
                  <Fade in={true} timeout={1200}>
                    <Box textAlign="center" sx={{ position: 'relative', zIndex: 1 }}>
                      {/* Logo corporativo - diseño sólido y fuerte con pulso de seguridad */}
                      <Box
                        sx={{
                          width: { xs: 60, sm: 65, md: 55, lg: 60 },
                          height: { xs: 60, sm: 65, md: 55, lg: 60 },
                          margin: '0 auto',
                          mb: { xs: 1, sm: 1.5, md: 0.75, lg: 1 },
                          background: '#FFFFFF',  // Blanco sólido - corporativo fuerte
                          borderRadius: '24px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
                          transition: 'all 0.3s ease',
                          position: 'relative',
                          // Pulso sutil de seguridad activa
                          '&::before': {
                            content: '""',
                            position: 'absolute',
                            top: -4,
                            left: -4,
                            right: -4,
                            bottom: -4,
                            borderRadius: '26px',
                            border: '2px solid rgba(255, 255, 255, 0.6)',
                            animation: 'securityPulse 3s ease-in-out infinite',
                          },
                          '@keyframes securityPulse': {
                            '0%, 100%': {
                              opacity: 0,
                              transform: 'scale(1)',
                            },
                            '50%': {
                              opacity: 1,
                              transform: 'scale(1.05)',
                            },
                          },
                          '&:hover': {
                            transform: 'translateY(-3px)',
                            boxShadow: '0 14px 40px rgba(0, 0, 0, 0.35)',
                          },
                        }}
                      >
                        <Shield
                          sx={{
                            fontSize: { xs: 32, sm: 36, md: 30, lg: 34 },
                            color: '#80006A',  // Violeta ZENTRIA sobre blanco
                            filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.15))',
                          }}
                        />
                      </Box>

                      {/* Título con efecto de resplandor premium - MEJORADO */}
                      <Typography
                        variant="h1"
                        sx={{
                          fontWeight: 950,
                          fontFamily: '"Poppins", "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
                          color: 'white',
                          mb: { xs: 0.6, sm: 0.8, md: 0.5, lg: 0.6 },
                          fontSize: { xs: '1.5rem', sm: '1.65rem', md: '1.45rem', lg: '1.65rem' },
                          letterSpacing: '-0.05em',
                          textShadow: '0 6px 25px rgba(0, 0, 0, 0.4), 0 3px 12px rgba(0, 0, 0, 0.25)',
                          lineHeight: 1.05,
                          position: 'relative',
                          overflow: 'hidden',
                          fontVariantLigatures: 'common-ligatures',
                          // Efecto de resplandor que recorre el texto una vez
                          '&::after': {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: '-100%',
                            width: '50%',
                            height: '100%',
                            background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8), transparent)',
                            animation: 'glareEffect 3s ease-out 1s 1',
                            transform: 'skewX(-20deg)',
                          },
                          '@keyframes glareEffect': {
                            '0%': {
                              left: '-100%',
                            },
                            '100%': {
                              left: '200%',
                            },
                          },
                        }}
                      >
                        ZENTRIA AFE
                      </Typography>

                      {/* Subtítulo corporativo elegante - PREMIUM */}
                      <Typography
                        variant="h6"
                        sx={{
                          color: 'rgba(255, 255, 255, 0.97)',
                          fontFamily: '"Poppins", "Inter", "Segoe UI", sans-serif',
                          fontWeight: 700,
                          mb: { xs: 1.5, sm: 1.75, md: 0.85, lg: 1.1 },
                          fontSize: { xs: '0.8rem', sm: '0.85rem', md: '0.75rem', lg: '0.8rem' },
                          letterSpacing: '-0.01em',
                          textShadow: '0 3px 12px rgba(0, 0, 0, 0.25)',
                        }}
                      >
                        Sistema de Aprobación de Facturas
                      </Typography>

                      {/* Badges corporativos con Violeta opaco ZENTRIA */}
                      <Stack
                        direction="row"
                        spacing={2}
                        justifyContent="center"
                        alignItems="center"
                      >
                        <Chip
                          icon={<Business sx={{ fontSize: 17, color: 'white' }} />}
                          label=""
                          size="small"
                          sx={{
                            background: '#A65C99',  // Violeta opaco ZENTRIA
                            border: '1.5px solid rgba(255, 255, 255, 0.3)',
                            fontFamily: '"Inter", "Segoe UI", sans-serif',
                            fontWeight: 700,
                            fontSize: '0.8rem',
                            px: 1.5,
                            py: 0.3,
                            height: 32,
                            color: 'white',
                            boxShadow: '0 3px 10px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
                            transition: 'all 0.3s ease',
                            '&:hover': {
                              background: '#8F4E7D',
                              boxShadow: '0 4px 14px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.25)',
                              transform: 'translateY(-2px)',
                            },
                          }}
                        />
                        <Chip
                          icon={<VerifiedUser sx={{ fontSize: 17, color: 'white' }} />}
                          label="Secure"
                          size="small"
                          sx={{
                            background: '#A65C99',  // Violeta opaco ZENTRIA
                            border: '1.5px solid rgba(255, 255, 255, 0.3)',
                            fontFamily: '"Inter", "Segoe UI", sans-serif',
                            fontWeight: 700,
                            fontSize: '0.8rem',
                            px: 1.5,
                            py: 0.3,
                            height: 32,
                            color: 'white',
                            boxShadow: '0 3px 10px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
                            transition: 'all 0.3s ease',
                            '&:hover': {
                              background: '#8F4E7D',
                              boxShadow: '0 4px 14px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.25)',
                              transform: 'translateY(-2px)',
                            },
                          }}
                        />
                      </Stack>
                    </Box>
                  </Fade>
                </Box>

                {/* PANEL DERECHO - FORMULARIO (más estrecho) */}
                <Box
                  sx={{
                    flex: { xs: 'none', md: '0 0 56%', lg: '0 0 56%' },
                    background: '#FFFFFF',
                    borderRadius: { xs: '0', md: '0 24px 0 0' },
                    px: { xs: 1.75, sm: 1.75, md: 3.5, lg: 4, xl: 4.5 },
                    py: { xs: 1.75, sm: 1.75, md: 3, lg: 3.5, xl: 4 },
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                  }}
                >
                  {/* BOTÓN MICROSOFT SSO - CTA PRIMARIO ( First) */}
                  <Fade in={true} timeout={1400}>
                    <Box sx={{ mb: { xs: 1.25, sm: 1.5, md: 0.5, lg: 0.65 }, position: 'relative', zIndex: 1 }}>
                      {/* Etiqueta descriptiva corporativa - ANTES del botón */}
                      <Typography
                        variant="caption"
                        sx={{
                          display: 'block',
                          textAlign: 'center',
                          mb: 0.5,
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontWeight: 700,
                          color: 'text.primary',
                          fontSize: { xs: '0.85rem', md: '0.68rem', lg: '0.72rem' },
                          opacity: 0.9,
                          letterSpacing: '0.01em',
                        }}
                      >
                        Acceso rápido con tu cuenta corporativa
                      </Typography>

                      {/* Mensaje de recomendación */}
                      <Typography
                        variant="caption"
                        sx={{
                          display: 'block',
                          textAlign: 'center',
                          mb: 0.85,
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontWeight: 500,
                          color: '#80006A',
                          fontSize: { xs: '0.75rem', md: '0.58rem', lg: '0.62rem' },
                          letterSpacing: '0.01em',
                        }}
                      >
                        Recomendado para cuentas corporativas Zentria
                      </Typography>

                      {/* BOTÓN PRIMARIO - Microsoft SSO con Violeta ZENTRIA */}
                      <Button
                        fullWidth
                        variant="contained"
                        size="large"
                        onClick={handleMicrosoftLogin}
                        disabled={microsoftLoading || isLocked}
                        startIcon={microsoftLoading ? <CircularProgress size={18} sx={{ color: 'white' }} /> : <MicrosoftIcon />}
                        sx={{
                          py: { xs: 1.75, sm: 1.85, md: 1.15, lg: 1.25 },
                          borderRadius: 3,
                          fontFamily: '"Poppins", "Inter", "Segoe UI", sans-serif',
                          fontWeight: 800,
                          fontSize: { xs: '0.98rem', sm: '1.05rem', md: '0.82rem', lg: '0.88rem' },
                          textTransform: 'none',
                          letterSpacing: '-0.02em',
                          background: 'linear-gradient(135deg, #80006A 0%, #7B1FA2 100%)',
                          color: 'white',
                          border: '2px solid rgba(255, 255, 255, 0.2)',
                          boxShadow: `
                            0 12px 40px rgba(128, 0, 106, 0.35),
                            0 6px 16px rgba(0, 0, 0, 0.15),
                            inset 0 1px 0 rgba(255, 255, 255, 0.25),
                            inset 0 -2px 4px rgba(0, 0, 0, 0.1)
                          `,
                          transition: 'all 0.45s cubic-bezier(0.25, 0, 0.15, 1)',
                          position: 'relative',
                          overflow: 'hidden',
                          '&::before': {
                            content: '""',
                            position: 'absolute',
                            top: '50%',
                            left: '50%',
                            width: '0',
                            height: '0',
                            borderRadius: '50%',
                            background: 'rgba(255, 255, 255, 0.2)',
                            transform: 'translate(-50%, -50%)',
                            transition: 'width 0.65s ease, height 0.65s ease',
                          },
                          '&::after': {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, transparent 50%, rgba(0,0,0,0.1) 100%)',
                            opacity: 0,
                            transition: 'opacity 0.4s ease',
                          },
                          '&:hover': {
                            background: 'linear-gradient(135deg, #6B0A8E 0%, #80006A 100%)',
                            transform: 'translateY(-4px)',
                            border: '2px solid rgba(255, 255, 255, 0.4)',
                            boxShadow: `
                              0 16px 48px rgba(128, 0, 106, 0.45),
                              0 8px 20px rgba(0, 0, 0, 0.2),
                              0 0 24px rgba(128, 0, 106, 0.35),
                              inset 0 1px 0 rgba(255, 255, 255, 0.3),
                              inset 0 -2px 4px rgba(0, 0, 0, 0.15)
                            `,
                            '&::before': {
                              width: '320px',
                              height: '320px',
                            },
                            '&::after': {
                              opacity: 1,
                            },
                          },
                          '&:active': {
                            transform: 'translateY(-2px) scale(0.98)',
                            boxShadow: `
                              0 8px 24px rgba(128, 0, 106, 0.3),
                              inset 0 2px 6px rgba(0, 0, 0, 0.15)
                            `,
                          },
                          '&:disabled': {
                            background: 'linear-gradient(135deg, #E0E0E0 0%, #D0D0D0 100%)',
                            color: '#A0A0A0',
                            boxShadow: 'none',
                            border: '2px solid rgba(0, 0, 0, 0.08)',
                            cursor: 'not-allowed',
                          },
                        }}
                      >
                        {microsoftLoading ? 'Conectando...' : 'Continuar con Microsoft'}
                      </Button>
                    </Box>
                  </Fade>

                  {/* Divider secundario - Login tradicional como alternativa */}
                  <Box sx={{ display: 'flex', alignItems: 'center', my: { xs: 1.5, sm: 2, md: 0.6, lg: 0.75 }, position: 'relative', zIndex: 1 }}>
                    <Divider
                      sx={{
                        flex: 1,
                        height: '1px',
                        background: `linear-gradient(to left, #B0B0B0, transparent)`,
                        border: 'none',
                      }}
                    />
                    <Typography
                      variant="body2"
                      sx={{
                        px: { xs: 3, md: 1.25 },
                        color: '#6B6B6B',
                        fontFamily: '"Inter", "Segoe UI", sans-serif',
                        fontWeight: 600,
                        fontSize: { xs: '0.75rem', md: '0.58rem', lg: '0.62rem' },
                        textTransform: 'none',
                        letterSpacing: '0.01em',
                      }}
                    >
                      O inicia sesión con credenciales
                    </Typography>
                    <Divider
                      sx={{
                        flex: 1,
                        height: '1px',
                        background: `linear-gradient(to right, #B0B0B0, transparent)`,
                        border: 'none',
                      }}
                    />
                  </Box>

                  {/* Alerta de bloqueo */}
                  <Collapse in={isLocked}>
                    <Alert
                      severity="error"
                      icon={<Warning sx={{ fontSize: { xs: 20, md: 18 } }} />}
                      sx={{
                        mb: { xs: 3, md: 2 },
                        borderRadius: 2.5,
                        border: '1.5px solid',
                        borderColor: 'error.light',
                        fontSize: { xs: '0.9rem', md: '0.82rem' },
                        '& .MuiAlert-message': { fontWeight: 600 },
                      }}
                    >
                      Cuenta bloqueada temporalmente. Tiempo restante: {Math.floor(lockTimeRemaining / 60)}:
                      {(lockTimeRemaining % 60).toString().padStart(2, '0')}
                    </Alert>
                  </Collapse>

                  {/* Alerta de error de login con animación shake */}
                  <Collapse in={!!loginError && !isLocked}>
                    <Alert
                      severity="error"
                      icon={<ErrorIcon sx={{ fontSize: { xs: 20, md: 18 } }} />}
                      onClose={() => setLoginError('')}
                      sx={{
                        mb: { xs: 3, md: 2 },
                        borderRadius: 2.5,
                        border: '1.5px solid',
                        borderColor: 'error.light',
                        fontSize: { xs: '0.9rem', md: '0.82rem' },
                        '& .MuiAlert-message': { fontWeight: 500 },
                        animation: loginError ? 'shake 0.5s cubic-bezier(.36,.07,.19,.97) both' : 'none',
                        '@keyframes shake': {
                          '10%, 90%': { transform: 'translateX(-2px)' },
                          '20%, 80%': { transform: 'translateX(4px)' },
                          '30%, 50%, 70%': { transform: 'translateX(-6px)' },
                          '40%, 60%': { transform: 'translateX(6px)' },
                        },
                      }}
                    >
                      {loginError}
                    </Alert>
                  </Collapse>

                  {/* Formulario de credenciales con Floating Labels */}
                  <Box component="form" onSubmit={(e) => { e.preventDefault(); handleLogin(); }} sx={{ position: 'relative', zIndex: 1 }}>
                    {/* Campo de usuario con Floating Label Premium */}
                    <TextField
                      fullWidth
                      label="Usuario"
                      value={usuario}
                      onChange={(e) => {
                        setUsuario(e.target.value);
                        if (usuarioError) setUsuarioError('');
                        if (loginError) setLoginError('');
                      }}
                      margin="normal"
                      required
                      autoFocus
                      disabled={loading || isLocked}
                      error={!!usuarioError}
                      helperText={usuarioError}
                      InputLabelProps={{
                        shrink: usuario.length > 0 || undefined,
                      }}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <Person sx={{ color: usuarioError ? 'error.main' : '#80006A', fontSize: 22 }} />
                          </InputAdornment>
                        ),
                      }}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: 2.5,
                          background: `
                        linear-gradient(to bottom,
                          rgba(255, 255, 255, 0.95),
                          rgba(253, 253, 253, 0.92))
                      `,
                          backdropFilter: 'blur(8px) saturate(150%)',
                          transition: 'all 0.4s cubic-bezier(0.3, 0, 0.2, 1)',
                          height: { xs: '52px', sm: '54px', md: '46px', lg: '48px' },
                          '& fieldset': {
                            borderWidth: '1.5px',
                            borderColor: 'rgba(128, 0, 106, 0.15)',
                            transition: 'all 0.4s cubic-bezier(0.3, 0, 0.2, 1)',
                          },
                          '&:hover': {
                            background: `
                          linear-gradient(to bottom,
                            rgba(255, 255, 255, 0.99),
                            rgba(255, 255, 255, 0.96))
                        `,
                            '& fieldset': {
                              borderColor: '#80006A',  // Violeta principal ZENTRIA
                              borderWidth: '2px',
                              boxShadow: '0 0 0 3px rgba(128, 0, 106, 0.08)',
                            },
                          },
                          '&.Mui-focused': {
                            background: 'rgba(255, 255, 255, 1)',
                            boxShadow: `
                          0 0 0 6px rgba(128, 0, 106, 0.15),
                          0 8px 24px rgba(128, 0, 106, 0.12),
                          inset 0 1px 2px rgba(255, 255, 255, 1)
                        `,
                            '& fieldset': {
                              borderWidth: '2px',
                              borderColor: '#80006A',  // Violeta principal para focus
                            },
                          },
                        },
                        '& .MuiInputLabel-root': {
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontWeight: 600,
                          fontSize: { xs: '0.95rem', md: '0.88rem' },
                          color: '#6B6B6B',  // Medium Gray para labels
                          '&.Mui-focused': {
                            color: '#2196F3',  // Azul corporativo cuando está enfocado
                            fontWeight: 700,
                          },
                          '&.MuiInputLabel-shrink': {
                            transform: 'translate(14px, -9px) scale(0.85)',
                            background: 'linear-gradient(to bottom, white, rgba(255,255,255,0.95))',
                            padding: '0 6px',
                          },
                        },
                        '& .MuiInputBase-input': {
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontSize: { xs: '1rem', md: '0.92rem' },
                          fontWeight: 500,
                          color: '#333333',  // Dark Charcoal para el texto ingresado
                        },
                      }}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !loading && !isLocked) {
                          handleLogin();
                        }
                      }}
                    />

                    {/* Campo de contraseña con Floating Label Premium */}
                    <TextField
                      fullWidth
                      label="Contraseña"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (passwordError) setPasswordError('');
                        if (loginError) setLoginError('');
                      }}
                      margin="normal"
                      required
                      disabled={loading || isLocked}
                      error={!!passwordError}
                      helperText={passwordError}
                      InputLabelProps={{
                        shrink: password.length > 0 || undefined,
                      }}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <Lock sx={{ color: passwordError ? 'error.main' : '#80006A', fontSize: 22 }} />
                          </InputAdornment>
                        ),
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton
                              onClick={() => setShowPassword(!showPassword)}
                              edge="end"
                              disabled={loading || isLocked}
                              sx={{
                                color: showPassword ? '#2196F3' : '#80006A',  // Azul cuando activo, Violeta cuando inactivo
                                transition: 'all 0.2s',
                                '&:hover': {
                                  background: showPassword ? 'rgba(33, 150, 243, 0.1)' : 'rgba(128, 0, 106, 0.1)',
                                  transform: 'scale(1.08)',
                                  color: showPassword ? '#1976D2' : '#A65C99',
                                },
                              }}
                            >
                              {showPassword ? <VisibilityOff /> : <Visibility />}
                            </IconButton>
                          </InputAdornment>
                        ),
                      }}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: 2.5,
                          background: `
                        linear-gradient(to bottom,
                          rgba(255, 255, 255, 0.95),
                          rgba(253, 253, 253, 0.92))
                      `,
                          backdropFilter: 'blur(8px) saturate(150%)',
                          transition: 'all 0.4s cubic-bezier(0.3, 0, 0.2, 1)',
                          height: { xs: '52px', sm: '54px', md: '46px', lg: '48px' },
                          '& fieldset': {
                            borderWidth: '1.5px',
                            borderColor: 'rgba(128, 0, 106, 0.15)',
                            transition: 'all 0.4s cubic-bezier(0.3, 0, 0.2, 1)',
                          },
                          '&:hover': {
                            background: `
                          linear-gradient(to bottom,
                            rgba(255, 255, 255, 0.99),
                            rgba(255, 255, 255, 0.96))
                        `,
                            '& fieldset': {
                              borderColor: '#80006A',  // Violeta principal ZENTRIA
                              borderWidth: '2px',
                              boxShadow: '0 0 0 3px rgba(128, 0, 106, 0.08)',
                            },
                          },
                          '&.Mui-focused': {
                            background: 'rgba(255, 255, 255, 1)',
                            boxShadow: `
                          0 0 0 6px rgba(128, 0, 106, 0.15),
                          0 8px 24px rgba(128, 0, 106, 0.12),
                          inset 0 1px 2px rgba(255, 255, 255, 1)
                        `,
                            '& fieldset': {
                              borderWidth: '2px',
                              borderColor: '#80006A',  // Violeta principal para focus
                            },
                          },
                        },
                        '& .MuiInputLabel-root': {
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontWeight: 600,
                          fontSize: { xs: '0.95rem', md: '0.88rem' },
                          color: '#6B6B6B',  // Medium Gray para labels
                          '&.Mui-focused': {
                            color: '#2196F3',  // Azul corporativo cuando está enfocado
                            fontWeight: 700,
                          },
                          '&.MuiInputLabel-shrink': {
                            transform: 'translate(14px, -9px) scale(0.85)',
                            background: 'linear-gradient(to bottom, white, rgba(255,255,255,0.95))',
                            padding: '0 6px',
                          },
                        },
                        '& .MuiInputBase-input': {
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontSize: { xs: '1rem', md: '0.92rem' },
                          fontWeight: 500,
                          color: '#333333',  // Dark Charcoal para el texto ingresado
                        },
                      }}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !loading && !isLocked) {
                          handleLogin();
                        }
                      }}
                    />

                    {/* Link de recuperación con mejor contraste WCAG AA */}
                    <Box sx={{ textAlign: 'right', mt: { xs: 1.5, md: 0.4 }, mb: { xs: 2, md: 0.85 } }}>
                      <Link
                        component="button"
                        type="button"
                        variant="body2"
                        onClick={() => setOpenForgotPassword(true)}
                        disabled={loading || isLocked}
                        sx={{
                          color: '#80006A',  // Violeta ZENTRIA
                          textDecoration: 'none',
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontWeight: 700,
                          fontSize: { xs: '0.9rem', md: '0.72rem', lg: '0.76rem' },
                          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                          position: 'relative',
                          letterSpacing: '0.01em',
                          '&::after': {
                            content: '""',
                            position: 'absolute',
                            bottom: -3,
                            left: 0,
                            width: '0%',
                            height: '2.5px',
                            background: '#80006A',
                            borderRadius: '2px',
                            transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                          },
                          '&:hover': {
                            color: '#A65C99',
                            transform: 'translateX(2px)',
                            '&::after': {
                              width: '100%',
                            },
                          },
                          '&:disabled': {
                            color: 'text.disabled',
                            transform: 'none',
                          },
                        }}
                      >
                        ¿Olvidó su contraseña?
                      </Link>
                    </Box>

                    {/* Botón de inicio de sesión - PRIMARIO PREMIUM con Violeta ZENTRIA */}
                    <Button
                      fullWidth
                      variant="contained"
                      size="large"
                      type="submit"
                      disabled={loading || isLocked}
                      sx={{
                        mt: 0.75,
                        py: { xs: 1.75, sm: 1.85, md: 1.15, lg: 1.25 },
                        borderRadius: 3,
                        fontFamily: '"Poppins", "Inter", "Segoe UI", sans-serif',
                        fontWeight: 800,
                        fontSize: { xs: '0.98rem', sm: '1.05rem', md: '0.82rem', lg: '0.88rem' },
                        textTransform: 'none',
                        letterSpacing: '-0.02em',
                        border: '2px solid rgba(255, 255, 255, 0.15)',
                        // Violeta principal ZENTRIA (#80006A) - SIEMPRE acción primaria
                        background: 'linear-gradient(135deg, #80006A 0%, #7B1FA2 100%)',
                        color: '#FFFFFF',
                        opacity: 1,
                        // Sombras dinámicas - feedback visual premium
                        boxShadow: usuario && password
                          ? '0 12px 40px rgba(128, 0, 106, 0.35), 0 6px 16px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.25)'
                          : (usuario || password)
                            ? '0 8px 28px rgba(128, 0, 106, 0.25), 0 4px 12px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.15)'
                            : '0 6px 20px rgba(128, 0, 106, 0.2), 0 2px 8px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.12)',
                        transition: 'all 0.45s cubic-bezier(0.25, 0, 0.15, 1)',
                        position: 'relative',
                        overflow: 'hidden',
                        cursor: 'pointer',
                        // Efecto de brillo progresivo premium
                        '&::before': {
                          content: '""',
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          right: 0,
                          bottom: 0,
                          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, transparent 50%, rgba(0,0,0,0.05) 100%)',
                          opacity: usuario && password ? 1 : (usuario || password) ? 0.75 : 0.5,
                          transition: 'opacity 0.45s ease',
                        },
                        // Animación de pulso sutil cuando está listo
                        animation: usuario && password
                          ? 'readyPulse 2.8s ease-in-out infinite'
                          : 'none',
                        '@keyframes readyPulse': {
                          '0%, 100%': {
                            boxShadow: '0 12px 40px rgba(128, 0, 106, 0.35), 0 6px 16px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.25)',
                          },
                          '50%': {
                            boxShadow: '0 14px 48px rgba(128, 0, 106, 0.45), 0 8px 20px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.3)',
                          },
                        },
                        '&:hover': {
                          background: 'linear-gradient(135deg, #6B0A8E 0%, #80006A 100%)',
                          transform: 'translateY(-4px)',
                          border: '2px solid rgba(255, 255, 255, 0.3)',
                          boxShadow: '0 16px 48px rgba(128, 0, 106, 0.45), 0 8px 20px rgba(0, 0, 0, 0.2), 0 0 24px rgba(128, 0, 106, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.3)',
                          '&::before': {
                            opacity: 1,
                          },
                        },
                        '&:active': {
                          transform: 'translateY(-2px) scale(0.98)',
                          boxShadow: '0 8px 24px rgba(128, 0, 106, 0.3), inset 0 2px 6px rgba(0, 0, 0, 0.15)',
                        },
                        '&:disabled': {
                          background: 'linear-gradient(135deg, #E0E0E0 0%, #D0D0D0 100%)',
                          color: '#A0A0A0',
                          opacity: 0.7,
                          boxShadow: 'none',
                          border: '2px solid rgba(0, 0, 0, 0.08)',
                          cursor: 'not-allowed',
                          animation: 'none',
                        },
                      }}
                      onClick={handleLogin}
                    >
                      {loading ? (
                        <Box display="flex" alignItems="center" gap={1.5}>
                          <CircularProgress size={20} sx={{ color: 'white' }} />
                          <span>Verificando credenciales...</span>
                        </Box>
                      ) : isLocked ? (
                        'Cuenta Bloqueada'
                      ) : (
                        'Iniciar Sesión'
                      )}
                    </Button>

                    {/* Mensaje de seguridad */}
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: { xs: 0.75, md: 0.35 },
                        mt: { xs: 1.5, md: 0.5 },
                        px: { xs: 1.5, md: 0.75 },
                        py: { xs: 1.25, md: 0.6 },
                        background: 'rgba(33, 150, 243, 0.05)',
                        borderRadius: 2,
                        border: '1px solid rgba(33, 150, 243, 0.15)',
                      }}
                    >
                      <Security sx={{ fontSize: { xs: 18, md: 13 }, color: '#2196F3' }} />
                      <Typography
                        variant="caption"
                        sx={{
                          fontFamily: '"Inter", "Segoe UI", sans-serif',
                          fontWeight: 600,
                          fontSize: { xs: '0.75rem', md: '0.58rem', lg: '0.6rem' },
                          color: '#2196F3',
                          letterSpacing: '0.01em',
                        }}
                      >
                        Conexión cifrada mediante Microsoft Azure AD
                      </Typography>
                    </Box>
                  </Box>
                </Box>
                {/* Fin Panel Derecho */}
              </Box>
              {/* Fin Layout Horizontal */}

              {/* Footer corporativo premium MEJORADO - Al pie de la tarjeta completa */}
              <Box
                textAlign="center"
                sx={{
                  background: `
                    linear-gradient(
                      180deg,
                      rgba(255, 255, 255, 0.99),
                      rgba(252, 252, 253, 0.97)
                    )
                  `,
                  borderRadius: { xs: '0 0 24px 24px', lg: '0 0 24px 24px' },
                  px: { xs: 1.75, sm: 2.25, md: 1.5, lg: 2, xl: 2.25 },
                  pb: { xs: 1.5, sm: 1.75, md: 1.1 },
                  pt: { xs: 1.5, sm: 1.75, md: 1 },
                }}
              >
                <Divider
                  sx={{
                    mb: { xs: 1.5, sm: 2, md: 1 },
                    height: '1px',
                    background: 'linear-gradient(to right, transparent, rgba(0, 0, 0, 0.08), transparent)',
                    border: 'none',
                  }}
                />

                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    mb: { xs: 1.5, md: 1 },
                    fontFamily: '"Inter", "Segoe UI", sans-serif',
                    fontWeight: 600,
                    fontSize: { xs: '0.75rem', md: '0.68rem' },
                    color: '#6B6B6B',  // Medium Gray - WCAG AA compliant
                    letterSpacing: '0.01em',
                  }}
                >
                  © 2025 Zentria.<br />
                  Todos los derechos reservados.
                </Typography>

                <Box sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  gap: { xs: 1.5, sm: 2.5, md: 1.25 },
                  flexWrap: 'wrap',
                  alignItems: 'center'
                }}>
                  <Chip
                    icon={<Security sx={{ fontSize: { xs: 15, md: 13 } }} />}
                    label="v1.0.0"
                    size="small"
                    variant="outlined"
                    sx={{
                      fontFamily: '"Inter", "Segoe UI", sans-serif',
                      fontSize: { xs: '0.7rem', md: '0.65rem' },
                      height: { xs: 26, md: 24 },
                      fontWeight: 700,
                      borderWidth: '1.5px',
                      borderColor: 'rgba(128, 0, 106, 0.3)',
                      color: '#80006A',  // Violeta ZENTRIA
                      background: 'rgba(128, 0, 106, 0.05)',
                      transition: 'all 0.2s',
                      '&:hover': {
                        borderColor: 'rgba(128, 0, 106, 0.5)',
                        background: 'rgba(128, 0, 106, 0.1)',
                        transform: 'translateY(-1px)',
                      },
                    }}
                  />
                  <Link
                    href="#"
                    variant="caption"
                    sx={{
                      color: '#80006A',  // Violeta ZENTRIA - mejor contraste WCAG
                      textDecoration: 'none',
                      fontFamily: '"Inter", "Segoe UI", sans-serif',
                      fontWeight: 700,
                      fontSize: { xs: '0.75rem', md: '0.68rem' },
                      transition: 'all 0.25s',
                      position: 'relative',
                      '&::after': {
                        content: '""',
                        position: 'absolute',
                        bottom: -2,
                        left: 0,
                        width: '0%',
                        height: '2px',
                        background: '#80006A',
                        transition: 'width 0.25s',
                      },
                      '&:hover': {
                        color: '#660055',  // Violeta más oscuro al hover
                        '&::after': {
                          width: '100%',
                        },
                      },
                    }}
                  >
                    Soporte Técnico
                  </Link>
                  <Link
                    href="#"
                    variant="caption"
                    sx={{
                      color: '#80006A',  // Violeta ZENTRIA - mejor contraste WCAG
                      textDecoration: 'none',
                      fontFamily: '"Inter", "Segoe UI", sans-serif',
                      fontWeight: 700,
                      fontSize: { xs: '0.75rem', md: '0.68rem' },
                      transition: 'all 0.25s',
                      position: 'relative',
                      '&::after': {
                        content: '""',
                        position: 'absolute',
                        bottom: -2,
                        left: 0,
                        width: '0%',
                        height: '2px',
                        background: '#80006A',
                        transition: 'width 0.25s',
                      },
                      '&:hover': {
                        color: '#660055',  // Violeta más oscuro al hover
                        '&::after': {
                          width: '100%',
                        },
                      },
                    }}
                  >
                    Términos de Uso
                  </Link>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Slide>
      </Box>

      {/* Diálogo de recuperación de contraseña mejorado */}
      <Dialog
        open={openForgotPassword}
        onClose={() => setOpenForgotPassword(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 5,
            background: 'rgba(255, 255, 255, 0.98)',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 20px 60px rgba(128, 0, 106, 0.35)',
          },
        }}
      >
        <DialogTitle
          sx={{
            background: '#80006A',  // Violeta principal ZENTRIA
            color: 'white',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            fontSize: '1.4rem',
            py: 3,
          }}
        >
          <Email sx={{ fontSize: 32 }} />
          Recuperar Contraseña
        </DialogTitle>
        <DialogContent sx={{ pt: 4, pb: 2 }}>
          <Typography variant="body2" color="text.secondary" mb={3.5} sx={{ fontWeight: 500, fontSize: '0.95rem' }}>
            Ingrese su correo electrónico registrado. Le enviaremos un enlace seguro para restablecer su
            contraseña.
          </Typography>
          <TextField
            fullWidth
            label="Correo Electrónico"
            type="email"
            value={recoveryEmail}
            onChange={(e) => {
              setRecoveryEmail(e.target.value);
              if (emailError) setEmailError('');
            }}
            error={!!emailError}
            helperText={emailError}
            autoFocus
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Email sx={{ color: emailError ? 'error.main' : '#80006A' }} />
                </InputAdornment>
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 3,
                '&:hover fieldset': {
                  borderColor: '#A65C99',  // Violeta opaco ZENTRIA
                  borderWidth: 2,
                },
                '&.Mui-focused': {
                  boxShadow: '0 0 0 3px rgba(128, 0, 106, 0.12)',
                },
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1.5 }}>
          <Button
            onClick={() => {
              setOpenForgotPassword(false);
              setRecoveryEmail('');
              setEmailError('');
            }}
            sx={{
              color: 'text.secondary',
              fontWeight: 700,
              textTransform: 'none',
              px: 3,
              fontSize: '0.95rem',
            }}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleForgotPassword}
            variant="contained"
            sx={{
              background: '#80006A',  // Violeta principal ZENTRIA
              fontWeight: 700,
              textTransform: 'none',
              px: 4,
              fontSize: '0.95rem',
              boxShadow: '0 4px 12px rgba(128, 0, 106, 0.35)',
              '&:hover': {
                background: '#660055',  // Violeta más oscuro
                boxShadow: '0 6px 16px rgba(128, 0, 106, 0.45)',
              },
            }}
          >
            Enviar Enlace
          </Button>
        </DialogActions>
      </Dialog>

      {/* Sistema de notificaciones mejorado */}
      <Snackbar
        open={notification.open}
        autoHideDuration={notification.severity === 'error' || notification.severity === 'warning' ? 8000 : 4000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseNotification}
          severity={notification.severity}
          icon={
            notification.severity === 'success' ? (
              <CheckCircle />
            ) : notification.severity === 'error' ? (
              <ErrorIcon />
            ) : notification.severity === 'warning' ? (
              <Warning />
            ) : (
              <Info />
            )
          }
          sx={{
            width: '100%',
            borderRadius: 4,
            backdropFilter: 'blur(20px)',
            boxShadow: `0 12px 40px ${zentriaColors.violeta.main}50`,
            border: '1.5px solid rgba(255, 255, 255, 0.3)',
            '& .MuiAlert-message': {
              fontWeight: 700,
              fontSize: '1rem',
            },
          }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default LoginPage;
