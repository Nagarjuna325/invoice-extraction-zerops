import { configureStore } from '@reduxjs/toolkit';
import uploadReducer from './slices/uploadSlice';
import invoiceReducer from './slices/invoiceSlice';
import uiReducer from './slices/uiSlice';

// Configure Redux store
const store = configureStore({
  reducer: {
    upload: uploadReducer,
    invoice: invoiceReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for serializability check
        ignoredActions: ['upload/setSelectedFile'],
        // Ignore these paths in the state
        ignoredPaths: ['upload.currentUpload.file'],
      },
    }),
  devTools: import.meta.env.MODE !== 'production', // Enable Redux DevTools in development
});

export default store;