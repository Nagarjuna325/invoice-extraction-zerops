"""
Smart total amount detection
Handles payment schedules and multiple amounts
"""
import re
from typing import Optional, List, Tuple


class AmountDetector:
    """Detects the correct total amount from invoices with multiple amounts"""
    
    @staticmethod
    def find_invoice_total(text: str, extracted_amount: float) -> Optional[float]:
        """
        Find the actual invoice total from text
        Handles payment schedules
        
        Args:
            text: OCR text from invoice
            extracted_amount: Amount extracted by model
            
        Returns:
            Corrected total amount or None
        """
        # Find all amounts in the text
        amounts = AmountDetector._extract_all_amounts(text)
        
        if not amounts:
            return extracted_amount
        
        # Check if this looks like a payment schedule
        if AmountDetector._is_payment_schedule(text, amounts):
            # Return the highest/last amount (usually the total)
            return max(amounts)
        
        # Check for explicit "Invoice Total" or "Balance Due"
        total_amount = AmountDetector._find_labeled_total(text)
        if total_amount:
            return total_amount
        
        # Return original if no better option
        return extracted_amount
    
    @staticmethod
    def _extract_all_amounts(text: str) -> List[float]:
        """Extract all dollar amounts from text"""
        amounts = []
        
        # Pattern: $123.45 or 123.45
        pattern = r'\$?\s*([\d,]+\.\d{2})\b'
        
        for match in re.finditer(pattern, text):
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                if 0 < amount < 1000000:  # Reasonable range
                    amounts.append(amount)
            except:
                pass
        
        return amounts
    
    @staticmethod
    def _is_payment_schedule(text: str, amounts: List[float]) -> bool:
        """Check if text contains a payment schedule"""
        # Look for payment schedule keywords
        schedule_keywords = [
            r'up to \d{4}',
            r'payment.*schedule',
            r'payment.*terms',
            r'due.*\d{4}-\d{2}-\d{2}'
        ]
        
        for keyword in schedule_keywords:
            if re.search(keyword, text, re.IGNORECASE):
                # If we have 3+ amounts, likely a payment schedule
                if len(amounts) >= 3:
                    return True
        
        return False
    
    @staticmethod
    def _find_labeled_total(text: str) -> Optional[float]:
        """Find amount labeled as 'Invoice Total' or 'Balance Due'"""
        patterns = [
            r'invoice\s+total[:\s]*\$?\s*([\d,]+\.\d{2})',
            r'balance\s+due[:\s]*\$?\s*([\d,]+\.\d{2})',
            r'total\s+amount[:\s]*\$?\s*([\d,]+\.\d{2})',
            r'grand\s+total[:\s]*\$?\s*([\d,]+\.\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except:
                    pass
        
        return None


# Create singleton
amount_detector = AmountDetector()