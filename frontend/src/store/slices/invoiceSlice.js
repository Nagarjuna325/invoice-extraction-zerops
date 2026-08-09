import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import invoiceService from '@services/invoiceService';

// Async thunk for fetching all invoices
export const fetchInvoices = createAsyncThunk(
  'invoice/fetchInvoices',
  async (filters, { rejectWithValue }) => {
    try {
      const response = await invoiceService.getAllInvoices(filters);
      return response;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.message || 'Failed to fetch invoices'
      );
    }
  }
);

// Async thunk for fetching invoice by ID
export const fetchInvoiceById = createAsyncThunk(
  'invoice/fetchInvoiceById',
  async (id, { rejectWithValue }) => {
    try {
      const response = await invoiceService.getInvoiceById(id);
      return response;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.message || 'Failed to fetch invoice'
      );
    }
  }
);

// Async thunk for updating invoice
export const updateInvoice = createAsyncThunk(
  'invoice/updateInvoice',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const response = await invoiceService.updateInvoice(id, data);
      return response;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.message || 'Failed to update invoice'
      );
    }
  }
);

// Async thunk for deleting invoice
export const deleteInvoice = createAsyncThunk(
  'invoice/deleteInvoice',
  async (id, { rejectWithValue }) => {
    try {
      await invoiceService.deleteInvoice(id);
      return id;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.message || 'Failed to delete invoice'
      );
    }
  }
);

// Async thunk for fetching invoice stats
export const fetchInvoiceStats = createAsyncThunk(
  'invoice/fetchInvoiceStats',
  async (_, { rejectWithValue }) => {
    try {
      const response = await invoiceService.getInvoiceStats();
      return response;
    } catch (error) {
      return rejectWithValue(
        error.response?.data?.message || 'Failed to fetch stats'
      );
    }
  }
);

const initialState = {
  // Invoice list
  invoices: [],
  
  // Current invoice being viewed/edited
  currentInvoice: null,
  
  // Statistics
  stats: {
    total: 0,
    processed: 0,
    pending: 0,
    failed: 0,
    avgConfidence: 0,
  },
  
  // Filters
  filters: {
    status: 'all',
    vendor_name: '',
    date_from: null,
    date_to: null,
    min_confidence: null,
  },
  
  // Pagination
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  },
  
  // Loading states
  isLoading: false,
  isLoadingCurrent: false,
  isUpdating: false,
  isDeleting: false,
  isLoadingStats: false,
  
  // Error state
  error: null,
};

const invoiceSlice = createSlice({
  name: 'invoice',
  initialState,
  reducers: {
    // Set filters
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
      state.pagination.page = 1; // Reset to first page when filters change
    },

    // Clear filters
    clearFilters: (state) => {
      state.filters = {
        status: 'all',
        vendor_name: '',
        date_from: null,
        date_to: null,
        min_confidence: null,
      };
      state.pagination.page = 1;
    },

    // Set pagination
    setPagination: (state, action) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },

    // Clear current invoice
    clearCurrentInvoice: (state) => {
      state.currentInvoice = null;
    },

    // Clear error
    clearError: (state) => {
      state.error = null;
    },

    // Update current invoice locally (for optimistic updates)
    updateCurrentInvoiceLocal: (state, action) => {
      if (state.currentInvoice) {
        state.currentInvoice = {
          ...state.currentInvoice,
          ...action.payload,
        };
      }
    },
  },
  extraReducers: (builder) => {
    // Fetch invoices
    builder
      .addCase(fetchInvoices.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchInvoices.fulfilled, (state, action) => {
        state.isLoading = false;
        state.invoices = action.payload.invoices || [];
        state.pagination.total = action.payload.total || 0;
        state.pagination.totalPages = Math.ceil(
          action.payload.total / state.pagination.limit
        );
      })
      .addCase(fetchInvoices.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });

    // Fetch invoice by ID
    builder
      .addCase(fetchInvoiceById.pending, (state) => {
        state.isLoadingCurrent = true;
        state.error = null;
      })
      .addCase(fetchInvoiceById.fulfilled, (state, action) => {
        state.isLoadingCurrent = false;
        state.currentInvoice = action.payload;
      })
      .addCase(fetchInvoiceById.rejected, (state, action) => {
        state.isLoadingCurrent = false;
        state.error = action.payload;
      });

    // Update invoice
    builder
      .addCase(updateInvoice.pending, (state) => {
        state.isUpdating = true;
        state.error = null;
      })
      .addCase(updateInvoice.fulfilled, (state, action) => {
        state.isUpdating = false;
        state.currentInvoice = action.payload;
        
        // Update in list if exists
        const index = state.invoices.findIndex(
          (inv) => inv.id === action.payload.id
        );
        if (index !== -1) {
          state.invoices[index] = action.payload;
        }
      })
      .addCase(updateInvoice.rejected, (state, action) => {
        state.isUpdating = false;
        state.error = action.payload;
      });

    // Delete invoice
    builder
      .addCase(deleteInvoice.pending, (state) => {
        state.isDeleting = true;
        state.error = null;
      })
      .addCase(deleteInvoice.fulfilled, (state, action) => {
        state.isDeleting = false;
        // Remove from list
        state.invoices = state.invoices.filter(
          (inv) => inv.id !== action.payload
        );
        state.pagination.total = Math.max(0, state.pagination.total - 1);
      })
      .addCase(deleteInvoice.rejected, (state, action) => {
        state.isDeleting = false;
        state.error = action.payload;
      });

    // Fetch stats
    builder
      .addCase(fetchInvoiceStats.pending, (state) => {
        state.isLoadingStats = true;
      })
      .addCase(fetchInvoiceStats.fulfilled, (state, action) => {
        state.isLoadingStats = false;
        state.stats = action.payload;
      })
      .addCase(fetchInvoiceStats.rejected, (state, action) => {
        state.isLoadingStats = false;
        state.error = action.payload;
      });
  },
});

export const {
  setFilters,
  clearFilters,
  setPagination,
  clearCurrentInvoice,
  clearError,
  updateCurrentInvoiceLocal,
} = invoiceSlice.actions;

export default invoiceSlice.reducer;