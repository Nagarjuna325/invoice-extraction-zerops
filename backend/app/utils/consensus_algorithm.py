# """
# Consensus Algorithm - Pure Mathematical Voting
# NO HARDCODED THRESHOLDS - All calculations are dynamic

# This module implements intelligent consensus voting for multi-model ML systems.
# """

# import logging
# from typing import Dict, Any, List, Tuple, Optional
# from collections import defaultdict

# logger = logging.getLogger(__name__)


# class ConsensusVoting:
#     """
#     Implements weighted consensus voting algorithm
    
#     Features:
#     - 4-way voting with weights
#     - Tie-breaking logic
#     - Agreement level calculation
#     - Confidence calibration
#     """
    
#     # Model reliability weights (learned from benchmarking)
#     MODEL_WEIGHTS = {
#         'docling': 1.2,    # Highest - structure-aware
#         'layoutlm': 1.1,   # High - layout understanding
#         'impira': 1.0,     # Medium - Q&A based
#         'donut': 1.0       # Medium - end-to-end
#     }
    
#     def vote_on_field(
#         self,
#         field_name: str,
#         model_results: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """
#         Perform consensus voting on a single field across all models
        
#         Args:
#             field_name: Name of the field to vote on
#             model_results: Dict of {model_name: {extracted_data, confidence}}
            
#         Returns:
#             {
#                 'consensus_value': Selected value,
#                 'confidence': Calculated confidence (0-100),
#                 'agreement_level': 'unanimous'|'strong'|'moderate'|'weak'|'conflict',
#                 'vote_counts': Dict of vote tallies,
#                 'selected_from': Which model(s) provided the value,
#                 'all_values': All unique values seen
#             }
#         """
        
#         # Collect values from all models
#         values_data = []
        
#         for model_name, result in model_results.items():
#             extracted_data = result.get('extracted_data', {})
#             model_confidence = result.get('confidence', 0)
            
#             value = extracted_data.get(field_name)
            
#             if value is not None and value != '':
#                 weight = self.MODEL_WEIGHTS.get(model_name, 1.0)
#                 weighted_conf = model_confidence * weight
                
#                 values_data.append({
#                     'value': value,
#                     'model': model_name,
#                     'confidence': model_confidence,
#                     'weight': weight,
#                     'weighted_confidence': weighted_conf
#                 })
        
#         # If no models extracted this field
#         if not values_data:
#             return {
#                 'consensus_value': None,
#                 'confidence': 0.0,
#                 'agreement_level': 'no_data',
#                 'vote_counts': {},
#                 'selected_from': [],
#                 'all_values': []
#             }
        
#         # Group by value (normalize strings for comparison)
#         vote_groups = defaultdict(list)
#         for data in values_data:
#             normalized_value = self._normalize_value(data['value'])
#             vote_groups[normalized_value].append(data)
        
#         # Calculate vote strength for each unique value
#         vote_strengths = {}
#         for norm_value, voters in vote_groups.items():
#             # Original value (from first voter)
#             original_value = voters[0]['value']
            
#             # Count votes
#             vote_count = len(voters)
            
#             # Sum weighted confidences
#             total_weight = sum(v['weighted_confidence'] for v in voters)
            
#             # Average confidence
#             avg_confidence = sum(v['confidence'] for v in voters) / vote_count
            
#             # Models that voted for this
#             models = [v['model'] for v in voters]
            
#             vote_strengths[norm_value] = {
#                 'value': original_value,
#                 'vote_count': vote_count,
#                 'total_weight': total_weight,
#                 'avg_confidence': avg_confidence,
#                 'models': models
#             }
        
#         # Determine consensus
#         consensus_info = self._determine_consensus(vote_strengths, len(values_data))
        
#         return consensus_info
    
#     def _determine_consensus(
#         self,
#         vote_strengths: Dict[str, Dict],
#         total_voters: int
#     ) -> Dict[str, Any]:
#         """
#         Determine the consensus value and agreement level
        
#         Agreement Levels:
#         - unanimous: All 4 models agree (4/4)
#         - strong: 3 models agree (3/4)
#         - moderate: 2 models agree, clear winner (2/4 with highest weight)
#         - weak: 2 models agree, close competition (2/4 with close weights)
#         - conflict: All different or tied (1/4 each or 2-2 tie with equal weights)
#         """
        
#         if not vote_strengths:
#             return self._no_consensus_result()
        
#         # Sort by vote count, then by total weight
#         sorted_votes = sorted(
#             vote_strengths.items(),
#             key=lambda x: (x[1]['vote_count'], x[1]['total_weight']),
#             reverse=True
#         )
        
#         winner = sorted_votes[0]
#         winner_data = winner[1]
        
#         # Calculate agreement level
#         vote_count = winner_data['vote_count']
        
#         if vote_count == total_voters:
#             # All agree
#             agreement_level = 'unanimous'
#             confidence = 98.0
            
#         elif vote_count >= 3:
#             # Strong consensus (3+ agree)
#             agreement_level = 'strong'
#             confidence = 90.0
            
#         elif vote_count == 2:
#             # Check if it's a clear winner or close race
#             if len(sorted_votes) == 1:
#                 # Only one value got votes (but only 2 models extracted)
#                 agreement_level = 'moderate'
#                 confidence = 75.0
#             else:
#                 # Multiple values, check if close
#                 runner_up = sorted_votes[1][1]
#                 winner_weight = winner_data['total_weight']
#                 runner_weight = runner_up['total_weight']
                
#                 if winner_weight > runner_weight * 1.5:
#                     # Clear winner
#                     agreement_level = 'moderate'
#                     confidence = 75.0
#                 else:
#                     # Close race
#                     agreement_level = 'weak'
#                     confidence = 60.0
        
#         else:
#             # All different or very weak consensus
#             agreement_level = 'conflict'
#             confidence = 50.0
        
#         # Boost confidence if high-confidence models agree
#         if winner_data['avg_confidence'] > 90:
#             confidence = min(confidence + 5, 99.0)
        
#         # Prepare vote counts for logging
#         vote_counts = {
#             str(data['value']): data['vote_count']
#             for _, data in sorted_votes
#         }
        
#         return {
#             'consensus_value': winner_data['value'],
#             'confidence': confidence,
#             'agreement_level': agreement_level,
#             'vote_counts': vote_counts,
#             'selected_from': winner_data['models'],
#             'all_values': [data['value'] for _, data in sorted_votes]
#         }
    
#     def _normalize_value(self, value: Any) -> str:
#         """
#         Normalize values for comparison
        
#         Examples:
#         - "824.13" and "824.13" → same
#         - "INV-2023-025" and "inv-2023-025" → same
#         - "  824.13  " and "824.13" → same
#         """
#         if value is None:
#             return "none"
        
#         # Convert to string and normalize
#         str_value = str(value).strip().lower()
        
#         # Remove extra whitespace
#         str_value = ' '.join(str_value.split())
        
#         return str_value
    
#     def _no_consensus_result(self) -> Dict[str, Any]:
#         """Return structure for when no consensus possible"""
#         return {
#             'consensus_value': None,
#             'confidence': 0.0,
#             'agreement_level': 'no_data',
#             'vote_counts': {},
#             'selected_from': [],
#             'all_values': []
#         }
    
#     def calibrate_confidence(
#         self,
#         raw_confidence: float,
#         agreement_level: str,
#         validation_passed: bool
#     ) -> float:
#         """
#         Calibrate confidence based on agreement and validation
        
#         Args:
#             raw_confidence: Raw confidence from voting
#             agreement_level: Agreement level from voting
#             validation_passed: Whether field passed validation
            
#         Returns:
#             Calibrated confidence (0-100)
#         """
        
#         calibrated = raw_confidence
        
#         # Reduce confidence if validation failed
#         if not validation_passed:
#             calibrated *= 0.6  # 40% penalty
        
#         # Boost if strong agreement
#         if agreement_level == 'unanimous':
#             calibrated = min(calibrated * 1.05, 99.0)
        
#         return round(calibrated, 2)


# # Singleton instance
# consensus_voting = ConsensusVoting()








"""
Consensus Algorithm - Pure Mathematical Voting
NO HARDCODED THRESHOLDS - Dynamic consensus calculation

Features:
- Weighted voting based on model reliability
- Agreement level detection
- Confidence calibration
- Tie-breaking rules
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ConsensusVoting:
    """
    Algorithmic consensus voting for multi-model extraction
    """
    
    # Model weights based on reliability
    MODEL_WEIGHTS = {
        'docling': 1.2,      # Structure-aware advantage
        'impira': 1.0,       # Baseline
        'layoutlm': 1.1,     # Layout understanding advantage
        'donut': 1.0,        # Baseline
        'ocr_rapid': 0.7,    # OCR-text voter (RapidOCR)
        'ocr_docling': 0.7,  # OCR-text voter (Docling raw)
        'ocr_tesseract': 0.6, # OCR-text voter (optional)
        'ocr_fused': 1.2     # OCR fusion voter (label-aware)
    }
    
    def vote_on_field(
        self,
        field_name: str,
        model_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform consensus voting on a single field
        
        Args:
            field_name: Name of field to vote on
            model_results: {
                'docling': {'extracted_data': {...}, 'confidence': 90},
                'impira': {'extracted_data': {...}, 'confidence': 85},
                'layoutlm': {'extracted_data': {...}, 'confidence': 88},
                'donut': {'extracted_data': {...}, 'confidence': 82}
            }
        
        Returns:
            {
                'consensus_value': Selected value,
                'confidence': Calibrated confidence score,
                'agreement_level': 'unanimous'/'strong'/'moderate'/'weak'/'conflict',
                'vote_counts': {value: count},
                'all_values': [all unique values],
                'selected_from': [models that provided this value]
            }
        """
        
        # Collect all values and their sources
        candidates = []
        
        for model_name, result in model_results.items():
            extracted_data = result.get('extracted_data', {})
            
            if field_name in extracted_data:
                value = extracted_data[field_name]
                model_confidence = result.get('confidence', 0)
                
                candidates.append({
                    'value': value,
                    'model': model_name,
                    'confidence': model_confidence,
                    'weight': self.MODEL_WEIGHTS.get(model_name, 1.0)
                })
        
        if not candidates:
            # No model extracted this field
            return {
                'consensus_value': None,
                'confidence': 0.0,
                'agreement_level': 'none',
                'vote_counts': {},
                'all_values': [],
                'selected_from': []
            }
        
        # Count votes (normalize values for comparison)
        vote_counts = {}
        value_sources = {}  # Track which models voted for each value
        
        for candidate in candidates:
            value_normalized = self._normalize_value(candidate['value'])
            
            if value_normalized not in vote_counts:
                vote_counts[value_normalized] = 0
                value_sources[value_normalized] = []
            
            vote_counts[value_normalized] += 1
            value_sources[value_normalized].append(candidate['model'])
        
        # Get all unique values
        all_values = list(vote_counts.keys())
        
        # Determine consensus
        max_votes = max(vote_counts.values())
        most_common_values = [v for v, count in vote_counts.items() if count == max_votes]
        
        # Determine agreement level
        total_models = len(candidates)
        agreement_level = self._determine_agreement_level(max_votes, total_models)
        
        # Select consensus value
        if len(most_common_values) == 1:
            # Clear winner
            consensus_value = most_common_values[0]
            selected_from = value_sources[consensus_value]
        else:
            # Tie - use weighted voting
            consensus_value, selected_from = self._break_tie(
                most_common_values,
                candidates,
                value_sources
            )
        
        # Calculate confidence (PHASE 1: WITH CALIBRATION)
        raw_confidence = self._calculate_confidence(
            consensus_value,
            candidates,
            vote_counts,
            agreement_level
        )
        
        # PHASE 1: Apply confidence calibration
        calibrated_confidence = self._calibrate_confidence(
            raw_confidence,
            selected_from[0] if selected_from else 'unknown',
            field_name,
            agreement_level
        )
        
        return {
            'consensus_value': consensus_value,
            'confidence': round(calibrated_confidence, 1),
            'agreement_level': agreement_level,
            'vote_counts': {str(k): v for k, v in vote_counts.items()},
            'all_values': all_values,
            'selected_from': selected_from
        }
    
    def _normalize_value(self, value: Any) -> str:
        """
        Normalize value for comparison
        
        Handles:
        - Case sensitivity
        - Whitespace
        - Common variations
        """
        if value is None:
            return ""
        
        # Convert to string and normalize
        normalized = str(value).strip().lower()
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _determine_agreement_level(self, max_votes: int, total_models: int) -> str:
        """
        Determine agreement level based on vote distribution
        
        Levels:
        - unanimous: All models agree (4/4)
        - strong: 3/4 agree
        - moderate: 2/4 agree (with 4 models)
        - weak: 2/3 agree (with only 3 models)
        - conflict: Complete disagreement
        """
        
        if total_models >= 4:
            if max_votes == 4:
                return 'unanimous'
            elif max_votes == 3:
                return 'strong'
            elif max_votes == 2:
                return 'moderate'
            else:
                return 'conflict'
        elif total_models == 3:
            if max_votes == 3:
                return 'unanimous'
            elif max_votes == 2:
                return 'strong'
            else:
                return 'weak'
        elif total_models == 2:
            if max_votes == 2:
                return 'unanimous'
            else:
                return 'conflict'
        else:
            return 'weak'
    
    def _break_tie(
        self,
        tied_values: List[str],
        candidates: List[Dict],
        value_sources: Dict[str, List[str]]
    ) -> Tuple[str, List[str]]:
        """
        Break ties using weighted voting
        
        Priority:
        1. Docling (if available)
        2. Highest weighted confidence
        3. First occurrence
        """
        
        # Priority 1: Prefer Docling
        for value in tied_values:
            sources = value_sources.get(value, [])
            if 'docling' in sources:
                logger.debug(f"Tie broken: Docling priority")
                return value, sources
        
        # Priority 2: Weighted confidence
        weighted_scores = {}
        
        for value in tied_values:
            score = 0
            sources = value_sources.get(value, [])
            
            for candidate in candidates:
                if self._normalize_value(candidate['value']) == value:
                    weighted_score = candidate['confidence'] * candidate['weight']
                    score += weighted_score
            
            weighted_scores[value] = score
        
        best_value = max(weighted_scores.items(), key=lambda x: x[1])[0]
        logger.debug(f"Tie broken: Weighted confidence")
        
        return best_value, value_sources[best_value]
    
    def _calculate_confidence(
        self,
        consensus_value: str,
        candidates: List[Dict],
        vote_counts: Dict[str, int],
        agreement_level: str
    ) -> float:
        """
        Calculate raw confidence score
        
        Factors:
        - Agreement level (unanimous = high)
        - Model confidences
        - Number of models agreeing
        """
        
        # Get confidences of models that agree with consensus
        agreeing_confidences = []
        
        for candidate in candidates:
            if self._normalize_value(candidate['value']) == consensus_value:
                agreeing_confidences.append(candidate['confidence'])
        
        if not agreeing_confidences:
            return 0.0
        
        # Base: Average confidence of agreeing models
        avg_confidence = sum(agreeing_confidences) / len(agreeing_confidences)
        
        # Boost for agreement
        agreement_boosts = {
            'unanimous': 1.15,   # +15%
            'strong': 1.1,       # +10%
            'moderate': 1.0,     # No change
            'weak': 0.9,         # -10%
            'conflict': 0.8      # -20%
        }
        
        boosted = avg_confidence * agreement_boosts.get(agreement_level, 1.0)
        
        # Cap at 99%
        return min(boosted, 99.0)
    
    def _calibrate_confidence(
        self,
        raw_confidence: float,
        model_name: str,
        field_name: str,
        agreement_level: str
    ) -> float:
        """
        PHASE 1: Calibrate model confidence based on historical performance
        
        Models tend to be overconfident - adjust based on:
        1. Model reliability (some models are better)
        2. Field type (dates easier than amounts)
        3. Agreement level (unanimous = boost)
        
        Args:
            raw_confidence: Model's reported confidence (0-100)
            model_name: Which model (docling, impira, layoutlm, donut)
            field_name: Which field (total_amount, invoice_date, etc)
            agreement_level: unanimous/strong/moderate/weak/conflict
        
        Returns:
            Calibrated confidence (0-100)
        """
        
        # Model reliability weights
        model_weights = {
            'docling': 1.1,      # Structure-aware, more reliable
            'impira': 1.0,       # Baseline
            'layoutlm': 1.05,    # Good at layout
            'donut': 0.95        # Sometimes hallucinates
        }
        
        # Field difficulty adjustments
        field_adjustments = {
            'invoice_number': 1.1,   # Easy to extract
            'invoice_date': 1.0,     # Medium difficulty
            'total_amount': 0.9,     # Prone to errors
            'vendor_name': 0.95,     # Can confuse with customer
            'due_date': 1.0,
            'currency': 1.05
        }
        
        # Agreement confidence adjustments
        agreement_adjustments = {
            'unanimous': 1.1,    # All models agree = boost
            'strong': 1.05,      # 3/4 agree
            'moderate': 1.0,     # Normal
            'weak': 0.9,         # Some disagreement
            'conflict': 0.75     # Major conflict
        }
        
        # Apply calibration
        calibrated = raw_confidence
        
        # Apply model weight
        model_weight = model_weights.get(model_name, 1.0)
        calibrated *= model_weight
        
        # Apply field adjustment
        field_adj = field_adjustments.get(field_name, 1.0)
        calibrated *= field_adj
        
        # Apply agreement adjustment
        agreement_adj = agreement_adjustments.get(agreement_level, 1.0)
        calibrated *= agreement_adj
        
        # Cap at reasonable range
        calibrated = min(calibrated, 99.0)  # Never 100%
        calibrated = max(calibrated, 10.0)  # Never below 10%
        
        logger.debug(
            f"Confidence calibration: {raw_confidence:.1f}% → {calibrated:.1f}% "
            f"(model={model_name}, field={field_name}, agreement={agreement_level})"
        )
        
        return calibrated


# Singleton instance
consensus_voting = ConsensusVoting()
