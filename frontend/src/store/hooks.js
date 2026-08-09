import { useDispatch, useSelector } from 'react-redux';

// Export typed hooks for better developer experience
export const useAppDispatch = () => useDispatch();
export const useAppSelector = useSelector;

// You can also create specific selectors here
export const useUploadState = () => useAppSelector((state) => state.upload);
export const useInvoiceState = () => useAppSelector((state) => state.invoice);
export const useUIState = () => useAppSelector((state) => state.ui);