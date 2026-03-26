"""Read-only bridge between UI and AppController"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import threading
import uuid
from ..controller import AppController, AnalysisResult
from ..controller.schemas import AlertSummary, PipelineStats
from soc_copilot.integrations import VTIPInfo


class ControllerBridge:
    """Adapter for UI to access AppController with file upload support and status reporting"""
    
    def __init__(self, controller: AppController):
        self._controller = controller
        self._permission_status = None
        self._sources_added = 0
        self._process_lock = threading.Lock()  # Serialize pipeline access
        self._manual_results: List[AnalysisResult] = []
        self._manual_lock = threading.Lock()
        self._check_permissions()
    
    def _check_permissions(self):
        """Check system permissions on init"""
        import ctypes
        import sys
        
        self._permission_status = {
            "has_permission": False,
            "elevation_required": True,
            "reason": "Administrator rights required",
            "checked_at": datetime.now().isoformat()
        }
        
        # Check if running as admin on Windows
        if sys.platform == 'win32':
            try:
                self._permission_status["has_permission"] = ctypes.windll.shell32.IsUserAnAdmin()
                if self._permission_status["has_permission"]:
                    self._permission_status["reason"] = "Full access"
                    self._permission_status["elevation_required"] = False
            except Exception:
                pass
    
    def get_latest_alerts(self, limit: int = 50) -> List[AnalysisResult]:
        """Get latest analysis results (read-only)"""
        base_results = self._controller.get_results(limit=limit)
        if not isinstance(base_results, list):
            base_results = []
        with self._manual_lock:
            manual_results = list(self._manual_results)
        merged = base_results + manual_results
        merged.sort(key=lambda r: r.timestamp, reverse=True)
        return merged[:limit]
    
    def get_alert_by_id(self, batch_id: str) -> Optional[AnalysisResult]:
        """Get specific result by ID (read-only)"""
        result = self._controller.get_result_by_id(batch_id)
        if result is not None:
            return result
        with self._manual_lock:
            for item in reversed(self._manual_results):
                if item.batch_id == batch_id:
                    return item
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive controller statistics (read-only)"""
        base_stats = self._controller.get_stats()
        if not isinstance(base_stats, dict):
            base_stats = {}
        
        # Enhance with additional status info
        enhanced_stats = {
            **base_stats,
            "permission_check": self._permission_status,
            "shutdown_flag": False,  # Default, updated if kill switch is checked
        }
        
        # Check kill switch if available
        if hasattr(self._controller, 'killswitch_check') and self._controller.killswitch_check:
            try:
                enhanced_stats["shutdown_flag"] = self._controller.killswitch_check()
            except Exception:
                pass
        
        return enhanced_stats
    
    def get_kill_switch_status(self) -> Dict[str, Any]:
        """Get kill switch state (read-only)"""
        is_active = False
        reason = "Normal operation"
        
        if hasattr(self._controller, 'killswitch_check') and self._controller.killswitch_check:
            try:
                is_active = self._controller.killswitch_check()
                if is_active:
                    reason = "Kill switch engaged - processing halted"
            except Exception as e:
                reason = f"Check failed: {str(e)}"
        
        return {
            "active": is_active,
            "reason": reason,
            "checked_at": datetime.now().isoformat()
        }
    
    def get_permission_status(self) -> Dict[str, Any]:
        """Get permission check results (read-only)"""
        return self._permission_status
    
    def get_total_alert_count(self) -> int:
        """Get total stored alert count"""
        return self._controller.result_store.count()
    
    def add_file_source(self, filepath: str) -> bool:
        """Add a file for analysis. Process immediately (thread-safe)."""
        try:
            path = Path(filepath)
            if not path.exists():
                return False
            
            # Read and parse file content
            records = self._parse_file(path)
            if records:
                with self._process_lock:
                    self._controller.process_batch(records)
                    self._sources_added += 1
                    self._controller._sources_count = self._sources_added
            return True
        except Exception:
            return False
    
    def _parse_file(self, path: Path) -> List[dict]:
        """Parse log file and return records"""
        records = []
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            records = self._parse_csv(path)
        elif suffix == '.json':
            records = self._parse_json(path)
        elif suffix == '.evtx':
            records = self._parse_evtx(path)
        else:
            # Plain text - treat each line as a log
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append({"raw_line": line})
        
        return records
    
    def _parse_csv(self, path: Path) -> List[dict]:
        """Parse CSV file"""
        import csv
        records = []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Create raw_line from the CSV row
                raw_line = ','.join(f"{k}={v}" for k, v in row.items())
                records.append({"raw_line": raw_line, **row})
        return records
    
    def _parse_json(self, path: Path) -> List[dict]:
        """Parse JSON file"""
        import json
        records = []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    raw_line = json.dumps(item)
                    records.append({"raw_line": raw_line, **item})
            elif isinstance(data, dict):
                raw_line = json.dumps(data)
                records.append({"raw_line": raw_line, **data})
        return records
    
    def _parse_evtx(self, path: Path) -> List[dict]:
        """Parse Windows Event Log (EVTX) file"""
        try:
            from Evtx.Evtx import Evtx
            records = []
            with Evtx(str(path)) as log:
                for record in log.records():
                    xml = record.xml()
                    records.append({"raw_line": xml})
            return records
        except Exception:
            return []
    
    def start_ingestion(self):
        """Placeholder for ingestion start (files are processed immediately)"""
        pass

    def clear_all_results(self) -> None:
        """Clear all stored results (all sessions)."""
        self._controller.result_store.clear_all_sessions()
        with self._manual_lock:
            self._manual_results.clear()

    def clear_current_batch(self) -> int:
        """Clear only current batch/session results. Returns count removed."""
        removed = self._controller.result_store.clear_current_batch()
        with self._manual_lock:
            self._manual_results.clear()
        return removed

    def get_vt_info(self, ip: str) -> Optional[VTIPInfo]:
        """Get VirusTotal info for an IP address"""
        # Check all results for cached VT info
        for result in self._controller.get_results(limit=1000):
            if ip in result.vt_results:
                return result.vt_results[ip]
        
        # If not in cache, do a lookup
        return self._controller._vt_client.lookup_ip(ip)
    
    def get_all_source_ips(self) -> List[tuple]:
        """Get all discovered source IPs with their risk levels. Returns list of (ip, risk_level)"""
        ips_with_risk = []
        seen_ips = set()
        
        for result in self._controller.get_results(limit=1000):
            for ip, vt_info in result.vt_results.items():
                if ip not in seen_ips:
                    ips_with_risk.append((ip, vt_info.risk_level, vt_info))
                    seen_ips.add(ip)
        
        return ips_with_risk

    def create_manual_alert(
        self,
        raw_log: str,
        classification: str = "ManualEscalation",
        priority: str = "P2-High",
        source_ip: str = "N/A",
    ) -> bool:
        """Create a manual alert entry from a selected log row."""
        try:
            now = datetime.now()
            alert = AlertSummary(
                alert_id=f"MANUAL-{uuid.uuid4().hex[:8]}",
                priority=priority,
                classification=classification,
                confidence=1.0,
                anomaly_score=1.0,
                risk_score=1.0,
                source_ip=source_ip if source_ip and source_ip != "N/A" else None,
                destination_ip=None,
                timestamp=now,
                reasoning=f"Manual alert created by analyst from log: {raw_log[:300]}",
                suggested_action="Investigate this event and correlate with recent activity",
            )

            stats = PipelineStats(
                total_records=1,
                processed_records=1,
                alerts_generated=1,
                risk_distribution={"P2-High": 1},
                classification_distribution={classification: 1},
                processing_time=0.0,
            )

            manual_result = AnalysisResult(
                batch_id=f"manual-{uuid.uuid4().hex[:10]}",
                timestamp=now,
                alerts=[alert],
                stats=stats,
                raw_count=1,
            )

            with self._manual_lock:
                self._manual_results.append(manual_result)
                self._manual_results = self._manual_results[-500:]
            return True
        except Exception:
            return False

