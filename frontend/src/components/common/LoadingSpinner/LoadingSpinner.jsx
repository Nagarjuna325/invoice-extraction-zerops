import { Box, CircularProgress, Typography } from '@mui/material';

const LoadingSpinner = ({ 
  message = 'Loading...', 
  size = 40,
  fullScreen = false 
}) => {
  const content = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        ...(fullScreen && {
          minHeight: '100vh',
        }),
        ...(!fullScreen && {
          minHeight: 200,
        }),
      }}
    >
      <CircularProgress size={size} />
      {message && (
        <Typography variant="body2" color="text.secondary">
          {message}
        </Typography>
      )}
    </Box>
  );

  return content;
};

export default LoadingSpinner;