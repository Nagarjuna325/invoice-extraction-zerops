import { Chip, Box, Typography } from '@mui/material';
import { CheckCircle, Warning, Error } from '@mui/icons-material';
import { formatConfidence, getConfidenceLevel } from '@utils/formatters';

const ConfidenceIndicator = ({ 
  confidence, 
  showLabel = true, 
  size = 'medium',
  variant = 'filled' 
}) => {
  if (confidence === null || confidence === undefined) {
    return <Typography color="text.secondary">-</Typography>;
  }

  const level = getConfidenceLevel(confidence);
  const formattedConfidence = formatConfidence(confidence);

  // Get icon based on confidence level
  const getIcon = () => {
    if (level.label === 'High') return <CheckCircle />;
    if (level.label === 'Medium') return <Warning />;
    return <Error />;
  };

  // Chip variant
  if (variant === 'chip') {
    return (
      <Chip
        icon={getIcon()}
        label={showLabel ? `${formattedConfidence} - ${level.label}` : formattedConfidence}
        color={level.color}
        size={size}
      />
    );
  }

  // Badge variant (default)
  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.5,
        px: 1.5,
        py: 0.5,
        borderRadius: 1,
        bgcolor: `${level.color}.light`,
        color: `${level.color}.dark`,
      }}
    >
      {getIcon()}
      <Typography variant="body2" fontWeight={600}>
        {formattedConfidence}
      </Typography>
      {showLabel && (
        <Typography variant="caption" sx={{ ml: 0.5 }}>
          ({level.label})
        </Typography>
      )}
    </Box>
  );
};

export default ConfidenceIndicator;