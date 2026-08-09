import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle,
  Error as ErrorIcon,
  HourglassEmpty,
} from '@mui/icons-material';

const UploadProgress = ({ uploadState }) => {
  const { status, progress, processingStage, error } = uploadState;

  // Define processing steps
  const steps = [
    { label: 'Uploading', stage: 'uploading' },
    { label: 'OCR Processing', stage: 'processing' },
    { label: 'Data Extraction', stage: 'processing' },
    { label: 'Complete', stage: 'completed' },
  ];

  // Determine active step
  const getActiveStep = () => {
    if (status === 'uploading') return 0;
    if (status === 'processing') return 1;
    if (status === 'completed' || status === 'EXTRACTED') return 3;
    if (status === 'failed') return -1;
    return 0;
  };

  const activeStep = getActiveStep();

  // Get status icon
  const getStatusIcon = () => {
    if (status === 'failed') {
      return <ErrorIcon sx={{ fontSize: 48, color: 'error.main' }} />;
    }
    if (status === 'completed' || status === 'EXTRACTED') {
      return <CheckCircle sx={{ fontSize: 48, color: 'success.main' }} />;
    }
    return <CircularProgress size={48} />;
  };

  // Get status message
  const getStatusMessage = () => {
    if (status === 'uploading') return 'Uploading your invoice...';
    if (status === 'processing') return 'Processing with OCR...';
    if (status === 'completed' || status === 'EXTRACTED') return 'Processing complete!';
    if (status === 'failed') return 'Processing failed';
    return 'Processing...';
  };

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      {/* Status Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          mb: 3,
        }}
      >
        {getStatusIcon()}
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" gutterBottom>
            {getStatusMessage()}
          </Typography>
          {processingStage && (
            <Typography variant="body2" color="text.secondary">
              Current stage: {processingStage}
            </Typography>
          )}
        </Box>
      </Box>

      {/* Progress Bar */}
      {(status === 'uploading' || status === 'processing') && (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Progress
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {progress}%
            </Typography>
          </Box>
          <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 1 }} />
        </Box>
      )}

      {/* Processing Steps */}
      <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 2 }}>
        {steps.map((step, index) => (
          <Step key={step.label} completed={index < activeStep}>
            <StepLabel
              error={status === 'failed' && index === activeStep}
              StepIconProps={{
                sx: {
                  '&.Mui-completed': {
                    color: 'success.main',
                  },
                  '&.Mui-error': {
                    color: 'error.main',
                  },
                },
              }}
            >
              <Typography variant="caption">{step.label}</Typography>
            </StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* Error Message */}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="body2">{error}</Typography>
        </Alert>
      )}

      {/* Success Message */}
      {(status === 'completed' || status === 'EXTRACTED') && (
        <Alert severity="success" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Your invoice has been processed successfully! Redirecting to results...
          </Typography>
        </Alert>
      )}

      {/* Processing Message */}
      {status === 'processing' && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Please wait while we extract data from your invoice. This may take 10-30 seconds.
          </Typography>
        </Alert>
      )}
    </Paper>
  );
};

export default UploadProgress;