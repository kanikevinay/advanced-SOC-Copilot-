"""Application controller orchestrating ingestion → analysis → results"""

import time
import uuid
import re
from datetime import datetime
from typing import Optional, Callable, List, Set
from pathlib import Path

from soc_copilot.pipeline import create_soc_copilot
from soc_copilot.integrations import get_vt_client
from .schemas import AnalysisResult, AlertSummary, PipelineStats
from .result_store import ResultStore

from soc_copilot.core.logging import get_logger

logger = get_logger(__name__)


class AppController:
    """Main application controller for real-time analysis"""
    
    def __init__(self, models_dir: str, killswitch_check: Optional[Callable[[], bool]] = None):
        self.models_dir = models_dir
        self.killswitch_check = killswitch_check
        self.result_store = ResultStore(max_results=1000)
        self._pipeline = None
        self._text_log_classifier = None
        self._running = False
        self._sources_count = 0
        self._dropped_count = 0
        self._batches_processed = 0
        self._vt_client = get_vt_client()
        self._current_session_id = str(uuid.uuid4())
        self.result_store.set_session_id(self._current_session_id)
    
    def initialize(self):
        """Initialize analysis pipelines (network-flow ML + text log ML)"""
        self._pipeline = create_soc_copilot(self.models_dir)
        
        # Load text log classifier (optional — falls back to rules)
        text_log_model_path = Path(self.models_dir) / "text_log_rf_v1.joblib"
        try:
            from models.text_log_classifier.text_log_classifier import TextLogClassifier
            clf = TextLogClassifier()
            clf.load(text_log_model_path)
            self._text_log_classifier = clf
            logger.info("text_log_classifier_loaded", path=str(text_log_model_path))
        except (FileNotFoundError, ImportError) as e:
            logger.warning(
                "text_log_classifier_not_available",
                error=str(e),
                fallback="rule-based detection",
            )
            self._text_log_classifier = None
    
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
        
        # Run text log detection (ML + deterministic rules)
        text_log_alerts = self._text_log_ml_detect(raw_lines)
        
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
        
        # Merge text log alerts with network-flow ML alerts
        alert_summaries.extend(text_log_alerts)
        
        pipeline_stats = self._convert_stats(stats, processing_time)
        # Update stats with text log alerts
        pipeline_stats.alerts_generated += len(text_log_alerts)
        for ta in text_log_alerts:
            cls = ta.classification
            pipeline_stats.classification_distribution[cls] = (
                pipeline_stats.classification_distribution.get(cls, 0) + 1
            )
        
        # Create result
        result = AnalysisResult(
            batch_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            alerts=alert_summaries,
            stats=pipeline_stats,
            raw_count=len(raw_lines),
            raw_logs=raw_lines,
            session_id=self._current_session_id,
        )
        
        # VirusTotal lookups are done on-demand from the Investigation view.
        # Running per-IP lookups during upload can block processing because
        # free-tier VT rate limits are strict.
        
        # Store result
        self.result_store.add(result)
        
        return result
    
    def _extract_source_ips(self, alerts: List[AlertSummary], raw_lines: List[str]) -> Set[str]:
        """Extract unique source IPs from alerts and raw log lines"""
        ips = set()
        
        # From alerts
        for alert in alerts:
            if alert.source_ip:
                ips.add(alert.source_ip)
        
        # From raw logs using regex pattern IPv4
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        for line in raw_lines:
            matches = re.findall(ip_pattern, line)
            for ip in matches:
                # Basic validation (not 255.255.255.255 or 0.0.0.0)
                if ip not in ('255.255.255.255', '0.0.0.0'):
                    ips.add(ip)
        
        return ips
    
    # ------------------------------------------------------------------
    # Text Log ML Detection
    # ------------------------------------------------------------------
    
    # Priority and action mappings for text log classifications
    _CLASSIFICATION_CONFIG = {
        "BruteForce": {
            "priority_high": "P1-Critical",
            "priority_low": "P2-High",
            "prefix": "ML-BF",
            "action": "Block source IP and investigate compromised credentials",
        },
        "Malware": {
            "priority_high": "P1-Critical",
            "priority_low": "P1-Critical",
            "prefix": "ML-MAL",
            "action": "Isolate host immediately, run malware scan, check for lateral movement",
        },
        "Exfiltration": {
            "priority_high": "P1-Critical",
            "priority_low": "P2-High",
            "prefix": "ML-EXFIL",
            "action": "Block outbound connection, investigate data contents and authorization",
        },
        "Suspicious": {
            "priority_high": "P2-High",
            "priority_low": "P3-Medium",
            "prefix": "ML-SUSP",
            "action": "Investigate the activity and correlate with other events",
        },
    }
    
    def _text_log_ml_detect(self, lines: List[str]) -> List[AlertSummary]:
        """ML-based threat detection for text log lines.
        
        Uses the text log Random Forest classifier. Falls back to
        rule-based detection if the model is not loaded.
        
        Args:
            lines: Raw log lines
            
        Returns:
            List of AlertSummary objects for detected threats
        """
        alerts: List[AlertSummary] = []

        # Always include deterministic rules so known patterns reliably trigger.
        rule_alerts = self._rule_based_detect(lines)

        # If ML model is not available, rely on rules only.
        if self._text_log_classifier is None:
            return rule_alerts
        
        for line in lines:
            parsed = self._parse_raw_log(line)
            
            try:
                classification, confidence, class_probas = (
                    self._text_log_classifier.classify(parsed)
                )
            except Exception as e:
                logger.warning("text_log_classify_failed", line=line[:80], error=str(e))
                continue
            
            # Skip benign events
            if classification == "Benign":
                continue
            
            # Only alert if confidence is above threshold
            if confidence < 0.70:
                continue
            
            config = self._CLASSIFICATION_CONFIG.get(classification, {})
            if not config:
                continue
            
            # Determine priority based on confidence
            if confidence >= 0.85:
                priority = config["priority_high"]
                risk = min(confidence, 0.95)
            else:
                priority = config["priority_low"]
                risk = confidence
            
            # Build human-readable reasoning
            src_ip = parsed.get("src_ip", "")
            dst_ip = parsed.get("dst_ip", "")
            user = parsed.get("user", "")
            event_type = parsed.get("event_type", "")
            
            reasoning_parts = [
                f"ML classification: {classification} ({confidence:.0%} confidence).",
            ]
            if event_type:
                reasoning_parts.append(f"Event: {event_type}.")
            if user:
                reasoning_parts.append(f"User: {user}.")
            if src_ip and self._is_external_ip(src_ip):
                reasoning_parts.append(f"External source IP: {src_ip}.")
            if dst_ip and self._is_external_ip(dst_ip):
                reasoning_parts.append(f"External destination IP: {dst_ip}.")
            if parsed.get("login_attempts", 0) > 0:
                reasoning_parts.append(f"Failed login attempts: {parsed['login_attempts']}.")
            if parsed.get("data_size_mb", 0) > 0:
                reasoning_parts.append(f"Data transfer: {parsed['data_size_mb']}MB.")
            
            # Top class probabilities for context
            top_3 = sorted(class_probas.items(), key=lambda x: -x[1])[:3]
            prob_str = ", ".join(f"{c}: {p:.0%}" for c, p in top_3)
            reasoning_parts.append(f"Class probabilities: [{prob_str}]")
            
            alerts.append(AlertSummary(
                alert_id=f"{config['prefix']}-{uuid.uuid4().hex[:8]}",
                priority=priority,
                classification=classification,
                confidence=confidence,
                anomaly_score=risk,
                risk_score=risk,
                source_ip=src_ip or None,
                destination_ip=dst_ip or None,
                timestamp=datetime.now(),
                reasoning=" ".join(reasoning_parts),
                suggested_action=config["action"],
            ))
        
        # Merge ML and rule alerts with simple de-duplication by classification + src/dst.
        merged = rule_alerts + alerts
        deduped: List[AlertSummary] = []
        seen = set()
        for alert in merged:
            key = (
                alert.classification,
                alert.priority,
                alert.source_ip or "",
                alert.destination_ip or "",
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(alert)

        return deduped
    
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
        failed_streak_by_ip: dict[str, int] = {}

        for line in lines:
            parsed = self._parse_raw_log(line)
            event_type = (parsed.get("event_type", "") or "").strip()
            event_type_key = event_type.lower()
            
            # Rule 1: Brute Force Detection
            if event_type_key in {"loginattempt", "userlogin", "login"}:
                src_ip = parsed.get("src_ip", "")
                user = parsed.get("user", "unknown")
                is_external = self._is_external_ip(src_ip)
                login_failed = parsed.get("login_failed", False)

                if login_failed and src_ip:
                    failed_streak_by_ip[src_ip] = failed_streak_by_ip.get(src_ip, 0) + 1
                elif src_ip:
                    failed_streak_by_ip[src_ip] = 0

                attempts = max(parsed.get("login_attempts", 0), failed_streak_by_ip.get(src_ip, 0))
                
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
                elif 2 <= attempts <= 4:
                    # Medium: early-stage suspicious login pattern
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-LOGIN-{uuid.uuid4().hex[:8]}",
                        priority="P3-Medium",
                        classification="Suspicious",
                        confidence=0.75,
                        anomaly_score=0.55,
                        risk_score=0.55,
                        source_ip=src_ip or None,
                        destination_ip=None,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"Suspicious login pattern: {attempts} failed logins "
                            f"for user '{user}' from IP {src_ip}"
                        ),
                        suggested_action="Monitor account and enforce step-up authentication",
                    ))
            
            # Rule 2: Malware Execution Detection
            elif event_type_key in {"fileexecution", "file_execute"}:
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
            elif event_type_key in {"datatransfer", "filetransfer", "transfer"}:
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
                elif 100 <= size_mb <= 400:
                    # Medium: unusual but not extreme transfer volume
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-DATA-{uuid.uuid4().hex[:8]}",
                        priority="P3-Medium",
                        classification="Suspicious",
                        confidence=0.72,
                        anomaly_score=0.52,
                        risk_score=0.52,
                        source_ip=parsed.get("src_ip") or None,
                        destination_ip=dst_ip or None,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"Medium-risk transfer detected: {size_mb}MB "
                            f"from {host} to {dst_ip or 'unknown destination'}"
                        ),
                        suggested_action="Review transfer context and validate business justification",
                    ))

            # Rule 4: Flood / DDoS Detection
            elif event_type_key in {"networkflood", "ddos", "flood"}:
                pps = int(parsed.get("packets_per_second", 0) or 0)
                src_ip = parsed.get("src_ip", "")
                dst_ip = parsed.get("dst_ip", "")

                if pps >= 40000:
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-DDOS-{uuid.uuid4().hex[:8]}",
                        priority="P1-Critical",
                        classification="DDoS",
                        confidence=0.96,
                        anomaly_score=0.96,
                        risk_score=0.96,
                        source_ip=src_ip or None,
                        destination_ip=dst_ip or None,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"High-volume flood traffic detected ({pps} packets/sec) "
                            f"from {src_ip or 'unknown source'} to {dst_ip or 'unknown destination'}"
                        ),
                        suggested_action="Enable DDoS mitigation controls and block malicious sources",
                    ))
                elif pps >= 10000:
                    alerts.append(AlertSummary(
                        alert_id=f"RULE-DDOS-{uuid.uuid4().hex[:8]}",
                        priority="P2-High",
                        classification="DDoS",
                        confidence=0.84,
                        anomaly_score=0.82,
                        risk_score=0.82,
                        source_ip=src_ip or None,
                        destination_ip=dst_ip or None,
                        timestamp=datetime.now(),
                        reasoning=(
                            f"Potential DDoS behavior: sustained flood rate of {pps} packets/sec"
                        ),
                        suggested_action="Monitor traffic spike and apply rate limiting",
                    ))
        
        return alerts
    
    def _parse_raw_log(self, line: str) -> dict:
        """Extract security-relevant fields from raw log lines.
        
        Parses log formats like:
        2026-01-18 02:56:01 LoginAttempt user=admin ip=45.67.89.101 success=false attempts=23
        2026-01-18 02:49:12 FileExecution host=server-02 file=payload.exe
        2026-01-18 02:58:11 DataTransfer source=server-02 destination=185.220.101.45 size=3526MB
        """
        import json
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
            "data_size_mb": 0,
            "login_failed": False,
            "packets_per_second": 0,
        }

        # Parse JSON logs first (common uploaded format).
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                status = str(payload.get("status", "")).lower()
                action = str(payload.get("action", payload.get("event", ""))).lower()

                entry["timestamp"] = str(payload.get("timestamp", ""))
                entry["user"] = str(payload.get("username", payload.get("user", "")))
                entry["src_ip"] = str(payload.get("src_ip", payload.get("source_ip", payload.get("ip", ""))))
                entry["dst_ip"] = str(payload.get("dst_ip", payload.get("destination_ip", payload.get("dest_ip", ""))))
                entry["host"] = str(payload.get("host", payload.get("source", "")))
                entry["protocol"] = str(payload.get("protocol", "TCP") or "TCP").upper()

                attempts_raw = payload.get("attempt_count", payload.get("attempts", 0))
                try:
                    entry["login_attempts"] = int(attempts_raw or 0)
                except (ValueError, TypeError):
                    entry["login_attempts"] = 0

                pps_raw = payload.get("packets_per_second", payload.get("pps", 0))
                try:
                    entry["packets_per_second"] = int(pps_raw or 0)
                except (ValueError, TypeError):
                    entry["packets_per_second"] = 0

                bytes_sent = payload.get("bytes_sent", 0)
                size_mb_raw = payload.get("size_mb", payload.get("size", 0))
                try:
                    size_mb = int(size_mb_raw or 0)
                except (ValueError, TypeError):
                    size_mb = 0
                if size_mb <= 0:
                    try:
                        size_mb = int((int(bytes_sent or 0)) / (1024 * 1024))
                    except (ValueError, TypeError):
                        size_mb = 0
                entry["data_size_mb"] = size_mb

                if payload.get("filename"):
                    entry["action"] = f"execute:{payload.get('filename')}"
                elif payload.get("file"):
                    entry["action"] = f"execute:{payload.get('file')}"
                else:
                    entry["action"] = action or "log_entry"

                if action in {"login_attempt", "login", "user_login", "auth_failed"}:
                    entry["event_type"] = "LoginAttempt"
                elif action in {"flood", "ddos", "dos"} or entry["packets_per_second"] >= 10000:
                    entry["event_type"] = "NetworkFlood"
                elif action in {"file_transfer", "data_transfer", "upload", "download", "transfer"} or entry["data_size_mb"] > 0:
                    entry["event_type"] = "DataTransfer"
                elif action in {"file_execution", "execute"}:
                    entry["event_type"] = "FileExecution"

                entry["login_failed"] = status in {"failed", "blocked", "denied", "error"}

                if entry["login_attempts"] >= 5:
                    entry["action"] = "brute_force"
                if "payload" in line.lower() or ".exe" in line.lower():
                    entry["action"] = "malware_execution"
                if entry["data_size_mb"] > 500:
                    entry["action"] = "data_exfiltration"
                if entry["packets_per_second"] >= 10000:
                    entry["action"] = "ddos_flood"

                for ip_field in ["src_ip", "dst_ip"]:
                    ip = entry.get(ip_field, "")
                    if ip and not ip.startswith(("192.168.", "10.", "172.16.", "127.", "0.0.0.0")):
                        entry["external_ip"] = True

                return entry
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        
        # Extract timestamp (YYYY-MM-DD HH:MM:SS)
        ts_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if ts_match:
            entry["timestamp"] = ts_match.group(1).replace(' ', 'T') + 'Z'
        
        # Extract event type
        event_match = re.search(r'\b(UserLogin|LoginAttempt|FileExecution|DataTransfer)\b', line)
        if event_match:
            entry["event_type"] = event_match.group(1)
        
        # Extract explicit login status from text format ("UserLogin failed").
        if re.search(r'\bUserLogin\s+failed\b', line, re.IGNORECASE):
            entry["login_failed"] = True

        # Extract key=value pairs
        for match in re.finditer(r'(\w+)=([^\s]+)', line):
            key, value = match.groups()
            if key == 'ip':
                entry["src_ip"] = value
            elif key == 'src_ip':
                entry["src_ip"] = value
            elif key == 'source':
                entry["host"] = value
            elif key == 'destination':
                entry["dst_ip"] = value
            elif key == 'dst_ip':
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
