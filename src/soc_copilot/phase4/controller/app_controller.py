"""Application controller orchestrating ingestion → analysis → results"""

import time
import uuid
from datetime import datetime
from typing import Optional, Callable, List
from pathlib import Path

from soc_copilot.pipeline import create_soc_copilot
from .schemas import AnalysisResult, AlertSummary, PipelineStats
from .result_store import ResultStore


class AppController:
    """Main application controller for real-time analysis"""
    
    def __init__(self, models_dir: str, killswitch_check: Optional[Callable[[], bool]] = None):
        self.models_dir = models_dir
        self.killswitch_check = killswitch_check
        self.result_store = ResultStore(max_results=1000)
        self._pipeline = None
        self._running = False
        self._sources_count = 0
        self._dropped_count = 0
        self._batches_processed = 0
    
    def initialize(self):
        """Initialize analysis pipeline"""
        self._pipeline = create_soc_copilot(self.models_dir)
    
    def process_batch(self, records: List[dict]) -> Optional[AnalysisResult]:
        """Process batch of raw log records"""
        # Check kill switch
        if self.killswitch_check and self.killswitch_check():
            return None
        
        if not self._pipeline:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")
        
        # Extract raw lines
        raw_lines = [r.get("raw_line", "") for r in records if r.get("raw_line")]
        if not raw_lines:
            return None
        
        # Measure processing time
        start_time = time.time()
        
        # Run rule-based detection on raw lines first
        rule_alerts = self._rule_based_detect(raw_lines)
        
        # Analyze batch (using existing ML pipeline)
        try:
            results, alerts, stats = self._analyze_lines(raw_lines)
        except Exception:
            self._dropped_count += len(raw_lines)
            return None
        
        # Mark as active after first successful batch
        self._running = True
        self._sources_count += 1
        self._batches_processed += 1
        
        processing_time = time.time() - start_time
        
        # Convert ML alerts to view models
        alert_summaries = self._convert_alerts(alerts)
        
        # Merge rule-based alerts with ML alerts
        alert_summaries.extend(rule_alerts)
        
        pipeline_stats = self._convert_stats(stats, processing_time)
        # Update stats with rule-based alerts
        pipeline_stats.alerts_generated += len(rule_alerts)
        for ra in rule_alerts:
            cls = ra.classification
            pipeline_stats.classification_distribution[cls] = (
                pipeline_stats.classification_distribution.get(cls, 0) + 1
            )
        
        # Create result
        result = AnalysisResult(
            batch_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            alerts=alert_summaries,
            stats=pipeline_stats,
            raw_count=len(raw_lines)
        )
        
        # Store result
        self.result_store.add(result)
        
        return result
    
    @staticmethod
    def _is_external_ip(ip: str) -> bool:
        """Check if an IP address is external (non-RFC1918)."""
        if not ip:
            return False
        return not ip.startswith(("192.168.", "10.", "172.16.", "127.", "0.0.0.0"))
    
    def _rule_based_detect(self, lines: List[str]) -> List[AlertSummary]:
        """Rule-based threat detection for custom text log formats.
        
        Detects:
        - Brute force: LoginAttempt with attempts >= 5
        - Malware execution: FileExecution with suspicious files (.exe, payload)
        - Data exfiltration: DataTransfer > 500MB to external IPs
        - External brute force: LoginAttempt from external IPs
        
        Returns:
            List of AlertSummary objects for detected threats
        """
        alerts = []
        
        for line in lines:
            parsed = self._parse_raw_log(line)
            event_type = parsed.get("event_type", "")
            
            # Rule 1: Brute Force Detection
            if event_type == "LoginAttempt":
                attempts = parsed.get("login_attempts", 0)
                src_ip = parsed.get("src_ip", "")
                user = parsed.get("user", "unknown")
                is_external = self._is_external_ip(src_ip)
                
                if attempts >= 10 and is_external:
                    # Critical: high-volume brute force from external IP
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-BF-{uuid.uuid4().hex[:8]}",
                        priority="P1-Critical",
                        classification="BruteForce",
                        confidence=0.95,
                        anomaly_score=0.95,
                        risk_score=0.95,
                        source_ip=src_ip,
                        destination_ip=None,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"Brute force attack detected: {attempts} failed login attempts "
                            f"for user '{user}' from external IP {src_ip}"
                        ),
                        suggested_action="Block source IP immediately and investigate compromised credentials",
                    ))
                elif attempts >= 5:
                    # High: moderate brute force
                    priority = "P1-Critical" if is_external else "P2-High"
                    risk = 0.90 if is_external else 0.75
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-BF-{uuid.uuid4().hex[:8]}",
                        priority=priority,
                        classification="BruteForce",
                        confidence=0.85,
                        anomaly_score=risk,
                        risk_score=risk,
                        source_ip=src_ip,
                        destination_ip=None,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"Brute force attempt: {attempts} failed logins "
                            f"for user '{user}' from {'external' if is_external else 'internal'} IP {src_ip}"
                        ),
                        suggested_action="Investigate account and consider temporary lockout",
                    ))
            
            # Rule 2: Malware Execution Detection
            elif event_type == "FileExecution":
                host = parsed.get("host", "unknown")
                action = parsed.get("action", "")
                filename = action.replace("execute:", "") if action.startswith("execute:") else ""
                
                if filename and (".exe" in filename.lower() or "payload" in filename.lower()):
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-MAL-{uuid.uuid4().hex[:8]}",
                        priority="P1-Critical",
                        classification="Malware",
                        confidence=0.90,
                        anomaly_score=0.92,
                        risk_score=0.92,
                        source_ip=None,
                        destination_ip=None,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"Suspicious executable detected: '{filename}' executed on {host}"
                        ),
                        suggested_action="Isolate host immediately, run malware scan, check for lateral movement",
                    ))
            
            # Rule 3: Data Exfiltration Detection
            elif event_type == "DataTransfer":
                size_mb = parsed.get("data_size_mb", 0)
                dst_ip = parsed.get("dst_ip", "")
                host = parsed.get("host", "unknown")
                is_external = self._is_external_ip(dst_ip)
                
                if size_mb > 500 and is_external:
                    if size_mb > 2000:
                        priority = "P1-Critical"
                        risk = 0.95
                    else:
                        priority = "P2-High"
                        risk = 0.80
                    
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-EXFIL-{uuid.uuid4().hex[:8]}",
                        priority=priority,
                        classification="Exfiltration",
                        confidence=0.88,
                        anomaly_score=risk,
                        risk_score=risk,
                        source_ip=None,
                        destination_ip=dst_ip,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"Potential data exfiltration: {size_mb}MB transferred "
                            f"from {host} to external IP {dst_ip}"
                        ),
                        suggested_action="Block outbound connection, investigate data contents and authorization",
                    ))
        
        return alerts
    
    def _parse_raw_log(self, line: str) -> dict:
        """Extract security-relevant fields from raw log lines.
        
        Parses log formats like:
        2026-01-18 02:56:01 LoginAttempt user=admin ip=45.67.89.101 success=false attempts=23
        2026-01-18 02:49:12 FileExecution host=server-02 file=payload.exe
        2026-01-18 02:58:11 DataTransfer source=server-02 destination=185.220.101.45 size=3526MB
        """
        import re
        
        entry = {
            "timestamp": "",
            "event_type": "",
            "user": "",
            "src_ip": "",
            "dst_ip": "",
            "host": "",
            "action": "log_entry",
            "protocol": "TCP",
            "raw_log": line,
            "login_attempts": 0,
            "data_size_mb": 0
        }
        
        # Extract timestamp (YYYY-MM-DD HH:MM:SS)
        ts_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if ts_match:
            entry["timestamp"] = ts_match.group(1).replace(' ', 'T') + 'Z'
        
        # Extract event type
        event_match = re.search(r'\b(UserLogin|LoginAttempt|FileExecution|DataTransfer)\b', line)
        if event_match:
            entry["event_type"] = event_match.group(1)
        
        # Extract key=value pairs
        for match in re.finditer(r'(\w+)=([^\s]+)', line):
            key, value = match.groups()
            if key == 'ip':
                entry["src_ip"] = value
            elif key == 'source':
                entry["host"] = value
            elif key == 'destination':
                entry["dst_ip"] = value
            elif key == 'host':
                entry["host"] = value
            elif key == 'user':
                entry["user"] = value
            elif key == 'file':
                entry["action"] = f"execute:{value}"
            elif key == 'attempts':
                try:
                    entry["login_attempts"] = int(value)
                except ValueError:
                    pass
            elif key == 'size':
                try:
                    entry["data_size_mb"] = int(value.replace('MB', ''))
                except ValueError:
                    pass
        
        # Flag suspicious patterns based on thresholds
        if entry["login_attempts"] >= 5:
            entry["action"] = "brute_force"
        if "payload" in line.lower() or ".exe" in line:
            entry["action"] = "malware_execution"
        if entry["data_size_mb"] > 500:
            entry["action"] = "data_exfiltration"
        
        # Mark external IPs as suspicious
        for ip_field in ["src_ip", "dst_ip"]:
            ip = entry.get(ip_field, "")
            if ip and not ip.startswith(("192.168.", "10.", "172.16.", "0.0.0.0", "")):
                entry["external_ip"] = True
        
        return entry
    
    def _analyze_lines(self, lines: List[str]):
        """Analyze lines using existing pipeline"""
        import tempfile
        import json
        
        # Create temp file in JSONL format for proper parsing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            for line in lines:
                # Try to parse as JSON, otherwise extract from raw log
                try:
                    # If it's already valid JSON, write as-is
                    json.loads(line)
                    f.write(line + '\n')
                except (json.JSONDecodeError, TypeError):
                    # Parse raw log to extract attack patterns
                    log_entry = self._parse_raw_log(line)
                    f.write(json.dumps(log_entry) + '\n')
            temp_path = f.name
        
        try:
            results, alerts, stats = self._pipeline.analyze_file(Path(temp_path))
            return results, alerts, stats
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def _convert_alerts(self, alerts) -> List[AlertSummary]:
        """Convert pipeline alerts to view models"""
        summaries = []
        for alert in alerts:
            summaries.append(AlertSummary(
                alert_id=alert.alert_id,
                priority=alert.priority.value,
                classification=alert.classification,
                confidence=alert.classification_confidence,
                anomaly_score=alert.anomaly_score,
                risk_score=alert.combined_risk_score,
                source_ip=alert.source_ip,
                destination_ip=alert.destination_ip,
                timestamp=datetime.now(),
                reasoning=alert.reasoning,
                suggested_action=alert.suggested_action
            ))
        return summaries
    
    def _convert_stats(self, stats, processing_time: float) -> PipelineStats:
        """Convert pipeline stats to view model"""
        return PipelineStats(
            total_records=stats.total_records,
            processed_records=stats.processed_records,
            alerts_generated=len(stats.risk_distribution),
            risk_distribution=dict(stats.risk_distribution),
            classification_distribution=dict(stats.classification_distribution),
            processing_time=processing_time
        )
    
    def get_results(self, limit: int = 10) -> List[AnalysisResult]:
        """Get latest analysis results"""
        return self.result_store.get_latest(limit)
    
    def get_result_by_id(self, batch_id: str) -> Optional[AnalysisResult]:
        """Get specific result by ID"""
        return self.result_store.get_by_id(batch_id)
    
    def get_stats(self) -> dict:
        """Get controller statistics"""
        return {
            "pipeline_loaded": self._pipeline is not None,
            "results_stored": self.result_store.count(),
            "models_dir": self.models_dir,
            "running": self._running,
            "sources_count": self._sources_count,
            "dropped_count": self._dropped_count,
            "batches_processed": self._batches_processed,
        }
    
    def clear_results(self):
        """Clear stored results"""
        self.result_store.clear()
