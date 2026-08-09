import { AppBar, Toolbar, Typography, IconButton, Box, Button } from '@mui/material';
import { Menu as MenuIcon, Dashboard, Upload, Home } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@store/hooks';
import { toggleSidebar } from '@store/slices/uiSlice';
import config from '@config/app.config';
import ROUTES from '@config/routes';

const Header = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const sidebarOpen = useAppSelector((state) => state.ui.sidebarOpen);

  const handleNavigate = (path) => {
    navigate(path);
  };

  const handleToggleSidebar = () => {
    dispatch(toggleSidebar());
  };

  return (
    <AppBar position="sticky" elevation={1}>
      <Toolbar>
        {/* Sidebar Toggle (for mobile/future use) */}
        <IconButton
          color="inherit"
          aria-label="toggle sidebar"
          edge="start"
          onClick={handleToggleSidebar}
          sx={{ mr: 2, display: { sm: 'none' } }}
        >
          <MenuIcon />
        </IconButton>

        {/* App Logo/Title */}
        <Typography
          variant="h6"
          component="div"
          sx={{ 
            flexGrow: 0, 
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
          onClick={() => handleNavigate(ROUTES.HOME)}
        >
          📄 {config.app.name}
        </Typography>

        {/* Spacer */}
        <Box sx={{ flexGrow: 1 }} />

        {/* Navigation Buttons */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            color="inherit"
            startIcon={<Home />}
            onClick={() => handleNavigate(ROUTES.HOME)}
            sx={{ display: { xs: 'none', sm: 'flex' } }}
          >
            Home
          </Button>

          <Button
            color="inherit"
            startIcon={<Upload />}
            onClick={() => handleNavigate(ROUTES.UPLOAD)}
          >
            Upload
          </Button>

          <Button
            color="inherit"
            startIcon={<Dashboard />}
            onClick={() => handleNavigate(ROUTES.DASHBOARD)}
            sx={{ display: { xs: 'none', sm: 'flex' } }}
          >
            Dashboard
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;