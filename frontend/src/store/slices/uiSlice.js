import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  // Sidebar state
  sidebarOpen: true,
  
  // Theme mode
  themeMode: 'light', // 'light' or 'dark'
  
  // Notifications
  notifications: [],
  
  // Global loading state
  globalLoading: false,
  
  // Snackbar state
  snackbar: {
    open: false,
    message: '',
    severity: 'info', // 'success', 'error', 'warning', 'info'
    duration: 6000,
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // Toggle sidebar
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },

    // Set sidebar state
    setSidebarOpen: (state, action) => {
      state.sidebarOpen = action.payload;
    },

    // Toggle theme mode
    toggleThemeMode: (state) => {
      state.themeMode = state.themeMode === 'light' ? 'dark' : 'light';
    },

    // Set theme mode
    setThemeMode: (state, action) => {
      state.themeMode = action.payload;
    },

    // Show snackbar notification
    showSnackbar: (state, action) => {
      state.snackbar = {
        open: true,
        message: action.payload.message,
        severity: action.payload.severity || 'info',
        duration: action.payload.duration || 6000,
      };
    },

    // Hide snackbar
    hideSnackbar: (state) => {
      state.snackbar.open = false;
    },

    // Add notification
    addNotification: (state, action) => {
      const notification = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        ...action.payload,
      };
      state.notifications.unshift(notification);
      
      // Keep only last 50 notifications
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50);
      }
    },

    // Remove notification
    removeNotification: (state, action) => {
      state.notifications = state.notifications.filter(
        (notif) => notif.id !== action.payload
      );
    },

    // Clear all notifications
    clearNotifications: (state) => {
      state.notifications = [];
    },

    // Mark notification as read
    markNotificationAsRead: (state, action) => {
      const notification = state.notifications.find(
        (notif) => notif.id === action.payload
      );
      if (notification) {
        notification.read = true;
      }
    },

    // Set global loading
    setGlobalLoading: (state, action) => {
      state.globalLoading = action.payload;
    },
  },
});

export const {
  toggleSidebar,
  setSidebarOpen,
  toggleThemeMode,
  setThemeMode,
  showSnackbar,
  hideSnackbar,
  addNotification,
  removeNotification,
  clearNotifications,
  markNotificationAsRead,
  setGlobalLoading,
} = uiSlice.actions;

export default uiSlice.reducer;