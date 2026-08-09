import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Alert,
} from '@mui/material';
import { Upload as UploadIcon, ArrowBack } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '@store/hooks';
import {
  setSelectedFile,
  setOcrEngine,
  uploadInvoice,
  pollProcessingStatus,
  resetUpload,
} from '@store/slices/uploadSlice';
import { showSnackbar } from '@store/slices/uiSlice';
import FileUploader from '@components/Upload/FileUploader/FileUploader';
import OCRSelector from '@components/Upload/OCRSelector/OCRSelector';
import UploadProgress from '@components/Upload/UploadProgress/UploadProgress';
import ROUTES from '@config/routes';

const UploadPage = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  
  const uploadState = useAppSelector((state) => state.upload);
  const { currentUpload, isUploading, isProcessing, error } = uploadState;

  const [localFile, setLocalFile] = useState(null);

  // Handle file selection
  const handleFileSelect = (file) => {
    setLocalFile(file);
    dispatch(setSelectedFile(file));
  };

  // Handle file removal
  const handleRemoveFile = () => {
    setLocalFile(null);
    dispatch(resetUpload());
  };

  // Handle OCR engine change
  const handleEngineChange = (engine) => {
    dispatch(setOcrEngine(engine));
  };

  // Handle upload
  const handleUpload = async () => {
    if (!localFile) {
      dispatch(
        showSnackbar({
          message: 'Please select a file first',
          severity: 'warning',
        })
      );
      return;
    }

    try {
      // Dispatch upload action
      const result = await dispatch(
        uploadInvoice({
          file: localFile,
          ocrEngine: currentUpload.ocrEngine,
        })
      ).unwrap();

      // Show success message
      dispatch(
        showSnackbar({
          message: 'Upload successful! Processing invoice...',
          severity: 'success',
        })
      );

      // Start polling for status
      const uploadId = result.upload_id;
      await dispatch(pollProcessingStatus(uploadId)).unwrap();

      // Processing complete - show success and redirect
      dispatch(
        showSnackbar({
          message: 'Processing complete!',
          severity: 'success',
        })
      );

      // Redirect to review page after 2 seconds
      setTimeout(() => {
        navigate(`/invoice/${uploadId}/review`);
      }, 2000);
    } catch (err) {
      console.error('Upload failed:', err);
      dispatch(
        showSnackbar({
          message: err || 'Upload failed. Please try again.',
          severity: 'error',
        })
      );
    }
  };

  // Reset on component unmount
  useEffect(() => {
    return () => {
      dispatch(resetUpload());
    };
  }, [dispatch]);

  // Check if upload is in progress
  const uploadInProgress = isUploading || isProcessing || currentUpload.status === 'processing';

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate(ROUTES.HOME)}
            sx={{ mb: 2 }}
          >
            Back to Home
          </Button>

          <Typography variant="h4" component="h1" gutterBottom fontWeight={600}>
            Upload Invoice
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Upload your invoice for automatic data extraction
          </Typography>
        </Box>

        <Grid container spacing={4}>
          {/* Left Column - Upload Form */}
          <Grid item xs={12} md={uploadInProgress ? 12 : 7}>
            {!uploadInProgress ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {/* File Uploader */}
                <Paper elevation={2} sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    1. Select Invoice File
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Upload a PDF, JPG, or PNG file of your invoice
                  </Typography>
                  <FileUploader
                    onFileSelect={handleFileSelect}
                    selectedFile={localFile}
                    onRemoveFile={handleRemoveFile}
                    isUploading={uploadInProgress}
                  />
                </Paper>

                {/* OCR Selector */}
                {localFile && (
                  <Paper elevation={2} sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      2. Select OCR Engine
                    </Typography>
                    <OCRSelector
                      selectedEngine={currentUpload.ocrEngine}
                      onEngineChange={handleEngineChange}
                      disabled={uploadInProgress}
                    />
                  </Paper>
                )}

                {/* Upload Button */}
                {localFile && (
                  <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                    <Button
                      variant="outlined"
                      onClick={handleRemoveFile}
                      disabled={uploadInProgress}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<UploadIcon />}
                      onClick={handleUpload}
                      disabled={uploadInProgress}
                    >
                      Upload & Process
                    </Button>
                  </Box>
                )}
              </Box>
            ) : (
              // Upload Progress
              <UploadProgress uploadState={currentUpload} />
            )}
          </Grid>

          {/* Right Column - Information */}
          {!uploadInProgress && (
            <Grid item xs={12} md={5}>
              <Paper elevation={1} sx={{ p: 3, bgcolor: 'background.paper' }}>
                <Typography variant="h6" gutterBottom>
                  📋 Supported Formats
                </Typography>
                <Box component="ul" sx={{ pl: 2 }}>
                  <Typography component="li" variant="body2" paragraph>
                    <strong>PDF:</strong> Best for digital invoices
                  </Typography>
                  <Typography component="li" variant="body2" paragraph>
                    <strong>JPG/JPEG:</strong> Good for scanned documents
                  </Typography>
                  <Typography component="li" variant="body2" paragraph>
                    <strong>PNG:</strong> High-quality image format
                  </Typography>
                </Box>

                <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                  ⚡ Processing Time
                </Typography>
                <Typography variant="body2" paragraph>
                  Typical processing takes 10-30 seconds depending on document size and
                  complexity.
                </Typography>

                <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                  🎯 Accuracy
                </Typography>
                <Typography variant="body2" paragraph>
                  Our AI-powered extraction achieves 99% accuracy for clear, printed
                  invoices. You can review and edit any extracted data.
                </Typography>

                <Alert severity="info" sx={{ mt: 3 }}>
                  <Typography variant="caption">
                    <strong>Tip:</strong> For best results, ensure your invoice image is
                    clear, well-lit, and properly aligned.
                  </Typography>
                </Alert>
              </Paper>
            </Grid>
          )}
        </Grid>

        {/* Error Display */}
        {error && !uploadInProgress && (
          <Alert severity="error" sx={{ mt: 3 }}>
            <Typography variant="body2">{error}</Typography>
          </Alert>
        )}
      </Box>
    </Container>
  );
};

export default UploadPage;