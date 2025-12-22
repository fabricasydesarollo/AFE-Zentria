import { ThemeProvider, CssBaseline } from '@mui/material';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { zentriaTheme } from './theme/zentriaTheme';
import { store } from './app/store';
import AppRoutes from './AppRoutes';
import { NotificationProvider } from './components/Notifications/NotificationProvider';

/**
 * App Component
 * Componente principal con todos los providers
 * Theme: Ultra-compact 12px base
 */

function App() {
  return (
    <Provider store={store}>
      <ThemeProvider theme={zentriaTheme}>
        <CssBaseline />
        <NotificationProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </NotificationProvider>
      </ThemeProvider>
    </Provider>
  );
}

export default App;
