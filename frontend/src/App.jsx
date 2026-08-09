import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Snackbar, Alert } from '@mui/material';
import { useAppDispatch, useAppSelector } from './store/hooks';
import { hideSnackbar } from './store/slices/uiSlice';
import ErrorBoundary from './components/common/ErrorBoundary/ErrorBoundary';
import MainLayout from './components/Layout/MainLayout/MainLayout';
import HomePage from './pages/HomePage/HomePage';
import UploadPage from './pages/UploadPage/UploadPage';
import NotFoundPage from './pages/NotFoundPage/NotFoundPage';
import ROUTES from './config/routes';

// Placeholder components (we'll build these in Phase 4 and 5)
const DashboardPage = () => (
  <div style={{ padding: 20, textAlign: 'center' }}>
    <h2>Dashboard Page - Coming in Phase 5! 📊</h2>
  </div>
);

const ReviewPage = () => (
  <div style={{ padding: 20, textAlign: 'center' }}>
    <h2>Review Page - Coming in Phase 4! 📋</h2>
  </div>
);

const InvoiceDetailPage = () => (
  <div style={{ padding: 20, textAlign: 'center' }}>
    <h2>Invoice Detail Page - Coming in Phase 4! 📄</h2>
  </div>
);

function App() {
  const dispatch = useAppDispatch();
  const snackbar = useAppSelector((state) => state.ui.snackbar);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          {/* Routes with Layout */}
          <Route element={<MainLayout />}>
            <Route path={ROUTES.HOME} element={<HomePage />} />
            <Route path={ROUTES.UPLOAD} element={<UploadPage />} />
            <Route path={ROUTES.DASHBOARD} element={<DashboardPage />} />
            <Route path={ROUTES.INVOICE_DETAIL} element={<InvoiceDetailPage />} />
            <Route path={ROUTES.INVOICE_REVIEW} element={<ReviewPage />} />
            <Route path={ROUTES.NOT_FOUND} element={<NotFoundPage />} />
          </Route>
        </Routes>

        {/* Global Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={snackbar.duration}
          onClose={() => dispatch(hideSnackbar())}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            onClose={() => dispatch(hideSnackbar())}
            severity={snackbar.severity}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;