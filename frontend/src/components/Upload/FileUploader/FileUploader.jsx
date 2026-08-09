import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  LinearProgress,
} from '@mui/material';
import {
  CloudUpload,
  Close,
  Description,
  Image as ImageIcon,
  PictureAsPdf,
} from '@mui/icons-material';
import { validateFile } from '@utils/validators';
import { formatFileSize } from '@utils/formatters';

const FileUploader = ({ onFileSelect, selectedFile, onRemoveFile, isUploading = false }) => {
  const [error, setError] = useState(null);

  // Handle file drop
  const onDrop = useCallback(
    (acceptedFiles, rejectedFiles) => {
      setError(null);

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === 'file-too-large') {
          setError('File size must be less than 10MB');
        } else if (rejection.errors[0]?.code === 'file-invalid-type') {
          setError('Only PDF, JPG, and PNG files are allowed');
        } else {
          setError('Invalid file');
        }
        return;
      }

      // Validate accepted file
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        const validation = validateFile(file);

        if (!validation.isValid) {
          setError(validation.error);
          return;
        }

        // File is valid, pass to parent
        onFileSelect(file);
        setError(null);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    maxSize: 10485760, // 10MB
    multiple: false,
    disabled: isUploading,
  });

  // Get file icon based on type
  const getFileIcon = (file) => {
    if (!file) return <Description />;
    
    if (file.type === 'application/pdf') {
      return <PictureAsPdf sx={{ fontSize: 48, color: 'error.main' }} />;
    } else if (file.type.startsWith('image/')) {
      return <ImageIcon sx={{ fontSize: 48, color: 'primary.main' }} />;
    }
    return <Description sx={{ fontSize: 48 }} />;
  };

  const handleRemove = () => {
    setError(null);
    onRemoveFile();
  };

  return (
    <Box>
      {!selectedFile ? (
        // Upload Zone
        <Paper
          {...getRootProps()}
          elevation={0}
          sx={{
            border: 2,
            borderStyle: 'dashed',
            borderColor: error
              ? 'error.main'
              : isDragActive
              ? 'primary.main'
              : 'divider',
            bgcolor: error
              ? 'error.lighter'
              : isDragActive
              ? 'primary.lighter'
              : 'background.paper',
            p: 4,
            textAlign: 'center',
            cursor: isUploading ? 'not-allowed' : 'pointer',
            transition: 'all 0.3s ease',
            '&:hover': {
              borderColor: isUploading ? 'divider' : 'primary.main',
              bgcolor: isUploading ? 'background.paper' : 'primary.lighter',
            },
          }}
        >
          <input {...getInputProps()} />

          <CloudUpload
            sx={{
              fontSize: 64,
              color: error ? 'error.main' : isDragActive ? 'primary.main' : 'text.secondary',
              mb: 2,
            }}
          />

          {isDragActive ? (
            <Typography variant="h6" color="primary">
              Drop your invoice here
            </Typography>
          ) : (
            <>
              <Typography variant="h6" gutterBottom>
                Drag & drop your invoice here
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                or
              </Typography>
              <Button variant="contained" component="span" disabled={isUploading}>
                Browse Files
              </Button>
            </>
          )}

          <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 2 }}>
            Supported formats: PDF, JPG, PNG (Max 10MB)
          </Typography>

          {error && (
            <Typography variant="body2" color="error" sx={{ mt: 2 }}>
              {error}
            </Typography>
          )}
        </Paper>
      ) : (
        // Selected File Preview
        <Paper
          elevation={2}
          sx={{
            p: 3,
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            position: 'relative',
          }}
        >
          {/* File Icon */}
          <Box sx={{ flexShrink: 0 }}>
            {getFileIcon(selectedFile)}
          </Box>

          {/* File Details */}
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography variant="subtitle1" noWrap>
              {selectedFile.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatFileSize(selectedFile.size)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {selectedFile.type || 'Unknown type'}
            </Typography>
          </Box>

          {/* Remove Button */}
          {!isUploading && (
            <IconButton
              size="small"
              color="error"
              onClick={handleRemove}
              sx={{ position: 'absolute', top: 8, right: 8 }}
            >
              <Close />
            </IconButton>
          )}

          {/* Upload Progress */}
          {isUploading && (
            <Box sx={{ position: 'absolute', bottom: 0, left: 0, right: 0 }}>
              <LinearProgress />
            </Box>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default FileUploader;