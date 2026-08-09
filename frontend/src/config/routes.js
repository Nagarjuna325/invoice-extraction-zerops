// Route paths configuration
export const ROUTES = {
  HOME: '/',
  UPLOAD: '/upload',
  DASHBOARD: '/dashboard',
  INVOICE_DETAIL: '/invoice/:id',
  INVOICE_REVIEW: '/invoice/:id/review',
  NOT_FOUND: '*',
};

// Helper function to generate dynamic routes
export const generatePath = (path, params = {}) => {
  let generatedPath = path;
  Object.keys(params).forEach((key) => {
    generatedPath = generatedPath.replace(`:${key}`, params[key]);
  });
  return generatedPath;
};

// Navigation items for sidebar/header
export const navigationItems = [
  {
    path: ROUTES.HOME,
    label: 'Home',
    icon: 'home',
  },
  {
    path: ROUTES.UPLOAD,
    label: 'Upload Invoice',
    icon: 'upload',
  },
  {
    path: ROUTES.DASHBOARD,
    label: 'Dashboard',
    icon: 'dashboard',
  },
];

export default ROUTES;