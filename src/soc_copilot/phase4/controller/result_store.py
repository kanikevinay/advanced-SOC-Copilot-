"""Thread-safe in-memory result storage (read-only access)"""

from collections import deque
from threading import Lock
from typing import List, Optional
from .schemas import AnalysisResult


class ResultStore:
    """Thread-safe in-memory storage for analysis results"""
    
    def __init__(self, max_results: int = 1000):
        self.max_results = max_results
        self._results = deque(maxlen=max_results)
        self._lock = Lock()
        self._current_session_id: Optional[str] = None
    
    def set_session_id(self, session_id: str):
        """Set the current upload session ID"""
        with self._lock:
            self._current_session_id = session_id
    
    def add(self, result: AnalysisResult):
        """Add analysis result"""
        with self._lock:
            # Auto-assign session ID if not already set
            if not result.session_id and self._current_session_id:
                result.session_id = self._current_session_id
            self._results.append(result)
    
    def get_latest(self, limit: int = 10) -> List[AnalysisResult]:
        """Get latest N results"""
        with self._lock:
            return list(self._results)[-limit:]
    
    def get_all(self) -> List[AnalysisResult]:
        """Get all stored results"""
        with self._lock:
            return list(self._results)
    
    def get_by_id(self, batch_id: str) -> Optional[AnalysisResult]:
        """Get result by batch ID"""
        with self._lock:
            for result in reversed(self._results):
                if result.batch_id == batch_id:
                    return result
            return None
    
    def get_by_session(self, session_id: str) -> List[AnalysisResult]:
        """Get all results for a specific session"""
        with self._lock:
            return [r for r in self._results if r.session_id == session_id]
    
    def get_current_session_results(self) -> List[AnalysisResult]:
        """Get all results for current session"""
        with self._lock:
            if not self._current_session_id:
                return []
            return [r for r in self._results if r.session_id == self._current_session_id]
    
    def count(self) -> int:
        """Get total result count"""
        with self._lock:
            return len(self._results)
    
    def clear_current_batch(self) -> int:
        """Clear only current session results. Returns count removed."""
        with self._lock:
            if not self._current_session_id:
                return 0
            
            original_count = len(self._results)
            # Remove results with current session ID
            self._results = deque(
                (r for r in self._results if r.session_id != self._current_session_id),
                maxlen=self.max_results
            )
            removed_count = original_count - len(self._results)
            
            # Clear session after removing
            self._current_session_id = None
            
            return removed_count
    
    def clear_all_sessions(self) -> int:
        """Clear all results (all sessions). Returns count removed."""
        with self._lock:
            removed_count = len(self._results)
            self._results.clear()
            self._current_session_id = None
            return removed_count
    
    def clear(self):
        """Clear all results (alias for clear_all_sessions)"""
        self.clear_all_sessions()
