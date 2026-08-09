import React from 'react';
import { Chip } from '@mui/material';
import { CheckCircle, Warning, Error } from '@mui/icons-material';

const ConfidenceBadge = ({ confidence, size = 'small' }) => {
  const getConfidenceConfig = (conf) => {
    if (conf >= 85) {
      return {
        label: `${conf}% High`,
        color: 'success',
        icon: <CheckCircle />,
        bgcolor: '#e8f5e9',
        textColor: '#2e7d32'
      };
    } else if (conf >= 70) {
      return {
        label: `${conf}% Medium`,
        color: 'warning',
        icon: <Warning />,
        bgcolor: '#fff3e0',
        textColor: '#e65100'
      };
    } else {
      return {
        label: `${conf}% Low`,
        color: 'error',
        icon: <Error />,
        bgcolor: '#ffebee',
        textColor: '#c62828'
      };
    }
  };

  if (!confidence && confidence !== 0) return null;

  const config = getConfidenceConfig(Math.round(confidence));

  return (
    <Chip
      icon={config.icon}
      label={config.label}
      size={size}
      sx={{
        backgroundColor: config.bgcolor,
        color: config.textColor,
        fontWeight: 600,
        '& .MuiChip-icon': {
          color: config.textColor
        }
      }}
    />
  );
};

export default ConfidenceBadge;