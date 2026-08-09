import axios from 'axios';
import config from '@config/app.config';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: config.api.baseURL,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add timestamp to request
    config.metadata = { startTime: new Date() };

    // You can add auth token here if needed in future
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }

    console.log(`[API Request] ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Calculate request duration
    const duration = new Date() - response.config.metadata.startTime;
    console.log(
      `[API Response] ${response.config.method.toUpperCase()} ${response.config.url} - ${duration}ms`
    );

    return response;
  },
  (error) => {
    // Handle errors
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;

      console.error(`[API Error] Status: ${status}`, data);

      // Handle specific error codes
      switch (status) {
        case 400:
          console.error('Bad Request:', data.message || 'Invalid request');
          break;
        case 401:
          console.error('Unauthorized:', data.message || 'Authentication required');
          // You can redirect to login here if needed
          break;
        case 403:
          console.error('Forbidden:', data.message || 'Access denied');
          break;
        case 404:
          console.error('Not Found:', data.message || 'Resource not found');
          break;
        case 500:
          console.error('Server Error:', data.message || 'Internal server error');
          break;
        default:
          console.error('Error:', data.message || 'Something went wrong');
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('[API Error] No response received:', error.message);
    } else {
      // Something else happened
      console.error('[API Error] Request setup failed:', error.message);
    }

    return Promise.reject(error);
  }
);

export default apiClient;