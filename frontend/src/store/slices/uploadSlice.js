import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import uploadService from '@services/uploadService';

// Async thunk for uploading invoice
export const uploadInvoice = createAsyncThunk(
  'upload/uploadInvoice',
  async ({ file, ocrEngine }, { rejectWithValue, dispatch }) => {
    try {
      const response = await uploadService.uploadInvoice(
        file,
        ocrEngine,
        (progress) => {
          dispatch(updateProgress(progress));
        }
      );
      return response;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.message || 'Upload failed'
      );
    }
  }
);

// Async thunk for polling processing status
export const pollProcessingStatus = createAsyncThunk(
  'upload/pollProcessingStatus',
  async (uploadId, { rejectWithValue, dispatch }) => {
    try {
      const response = await uploadService.pollProcessingStatus(
        uploadId,
        (status) => {
          dispatch(updateProcessingStatus(status));
        }
      );
      return response;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.message || error.message || 'Polling failed'
      );
    }
  }
);

const initialState = {
  // Current upload state
  currentUpload: {
    file: null,
    fileName: null,
    fileSize: null,
    uploadId: null,
    progress: 0,
    status: 'idle', // idle, uploading, processing, completed, failed
    ocrEngine: 'tesseract',
    processingStage: null,
  },
  
  // Upload history
  uploadHistory: [],
  
  // Loading states
  isUploading: false,
  isProcessing: false,
  
  // Error state
  error: null,
};

const uploadSlice = createSlice({
  name: 'upload',
  initialState,
  reducers: {
    // Set selected file
    setSelectedFile: (state, action) => {
      const file = action.payload;
      state.currentUpload.file = file;
      state.currentUpload.fileName = file.name;
      state.currentUpload.fileSize = file.size;
      state.error = null;
    },

    // Set OCR engine
    setOcrEngine: (state, action) => {
      state.currentUpload.ocrEngine = action.payload;
    },

    // Update upload progress
    updateProgress: (state, action) => {
      state.currentUpload.progress = action.payload;
    },

    // Update processing status
    updateProcessingStatus: (state, action) => {
      const status = action.payload;
      state.currentUpload.status = status.status;
      state.currentUpload.processingStage = status.current_stage;
      state.currentUpload.progress = status.progress || state.currentUpload.progress;
    },

    // Reset upload state
    resetUpload: (state) => {
      state.currentUpload = {
        file: null,
        fileName: null,
        fileSize: null,
        uploadId: null,
        progress: 0,
        status: 'idle',
        ocrEngine: 'tesseract',
        processingStage: null,
      };
      state.isUploading = false;
      state.isProcessing = false;
      state.error = null;
    },

    // Clear error
    clearError: (state) => {
      state.error = null;
    },

    // Add to upload history
    addToHistory: (state, action) => {
      state.uploadHistory.unshift(action.payload);
      // Keep only last 10 uploads
      if (state.uploadHistory.length > 10) {
        state.uploadHistory = state.uploadHistory.slice(0, 10);
      }
    },
  },
  extraReducers: (builder) => {
    // Upload invoice
    builder
      .addCase(uploadInvoice.pending, (state) => {
        state.isUploading = true;
        state.currentUpload.status = 'uploading';
        state.error = null;
      })
      .addCase(uploadInvoice.fulfilled, (state, action) => {
        state.isUploading = false;
        state.currentUpload.uploadId = action.payload.upload_id;
        state.currentUpload.status = action.payload.status || 'processing';
        state.currentUpload.progress = 100;
        
        // Add to history
        state.uploadHistory.unshift({
          uploadId: action.payload.upload_id,
          fileName: state.currentUpload.fileName,
          timestamp: new Date().toISOString(),
          status: action.payload.status,
        });
      })
      .addCase(uploadInvoice.rejected, (state, action) => {
        state.isUploading = false;
        state.currentUpload.status = 'failed';
        state.error = action.payload;
      });

    // Poll processing status
    builder
      .addCase(pollProcessingStatus.pending, (state) => {
        state.isProcessing = true;
        state.error = null;
      })
      .addCase(pollProcessingStatus.fulfilled, (state, action) => {
        state.isProcessing = false;
        state.currentUpload.status = action.payload.status;
        state.currentUpload.processingStage = action.payload.current_stage;
      })
      .addCase(pollProcessingStatus.rejected, (state, action) => {
        state.isProcessing = false;
        state.currentUpload.status = 'failed';
        state.error = action.payload;
      });
  },
});

export const {
  setSelectedFile,
  setOcrEngine,
  updateProgress,
  updateProcessingStatus,
  resetUpload,
  clearError,
  addToHistory,
} = uploadSlice.actions;

export default uploadSlice.reducer;