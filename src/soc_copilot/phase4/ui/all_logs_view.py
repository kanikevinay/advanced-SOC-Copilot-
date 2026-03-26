"""All Logs view - monitors both alert and normal logs with manual escalation."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import json
import re


class AllLogsView(QWidget):
    """Unified log monitor for alert + normal logs."""

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self._theme = None
        self._search_text = ""
        self._rows = []
        self._init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header = QHBoxLayout()

        title_layout = QVBoxLayout()
        self.title_label = QLabel("🗂️ All Logs")
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))

        self.counter_label = QLabel("Loading...")
        self.counter_label.setFont(QFont("Segoe UI", 11))

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.counter_label)
        header.addLayout(title_layout)

        header.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search logs...")
        self.search_box.textChanged.connect(self._on_search_changed)
        self.search_box.setMinimumWidth(260)
        header.addWidget(self.search_box)

        self.create_alert_btn = QPushButton("🚨 Create Alert from Selected Log")
        self.create_alert_btn.clicked.connect(self._create_alert_from_selection)
        header.addWidget(self.create_alert_btn)

        # Batch and session clear buttons
        self.clear_batch_btn = QPushButton("🗑️ Clear Current Batch")
        self.clear_batch_btn.setToolTip("Remove only logs from the current upload batch")
        self.clear_batch_btn.clicked.connect(self._clear_current_batch)
        header.addWidget(self.clear_batch_btn)

        self.clear_all_btn = QPushButton("🧹 Clear All Sessions")
        self.clear_all_btn.setToolTip("Remove all logs from all upload sessions")
        self.clear_all_btn.clicked.connect(self._clear_all_sessions)
        header.addWidget(self.clear_all_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh logs")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Time", "Type", "Priority", "Classification", "Source IP", "Batch ID", "Details"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        # Note: Click on alerts to see VirusTotal info in Investigation view
        layout.addWidget(self.table)

        self.empty_label = QLabel("")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.empty_label)

        self.setLayout(layout)
        self.apply_theme({
            "window_bg": "#0a0a1a",
            "text_primary": "#ffffff",
            "text_secondary": "#888888",
            "text_muted": "#666666",
            "input_bg": "#1a2744",
            "input_border": "#2a3f5f",
            "selection_bg": "#00d4ff",
            "selection_fg": "#0a0a1a",
            "button_bg": "#16213e",
            "button_hover": "#1a2744",
            "button_fg": "#ffffff",
            "accent": "#00d4ff",
            "accent_fg": "#0a0a1a",
            "accent_hover": "#00a8cc",
            "border_strong": "#2a3f5f",
        })

    def apply_theme(self, theme: dict):
        """Apply active application theme."""
        self._theme = theme
        self.setStyleSheet(f"background-color: {theme['window_bg']};")
        self.title_label.setStyleSheet(f"color: {theme['text_primary']};")
        self.counter_label.setStyleSheet(f"color: {theme['text_secondary']};")
        self.empty_label.setStyleSheet(f"color: {theme['text_secondary']}; font-style: italic; padding: 20px;")

        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['text_primary']};
                border: 1px solid {theme['input_border']};
                border-radius: 4px;
                padding: 5px 10px;
            }}
        """)

        self.create_alert_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: {theme['accent_fg']};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_hover']};
            }}
            QPushButton:disabled {{
                background-color: {theme['text_muted']};
                color: {theme['text_secondary']};
            }}
        """)

        # Style batch and all-sessions clear buttons
        self.clear_batch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_fg']};
                border: 1px solid {theme['border_strong']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
        """)

        self.clear_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #cc0000;
                color: {theme['button_fg']};
                border: 1px solid #ff3333;
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: #ff3333;
            }}
        """)

    def _on_search_changed(self, text: str):
        self._search_text = text.lower().strip()
        self._render_rows(self._rows)

    def refresh(self):
        """Refresh all logs table from latest processed batches."""
        try:
            results = self.bridge.get_latest_alerts(limit=200)
            rows = []
            alerts_count = 0
            normal_count = 0

            for result in results:
                batch_time = result.timestamp.strftime("%H:%M:%S") if hasattr(result.timestamp, "strftime") else str(result.timestamp)
                batch_id = result.batch_id

                # Show every uploaded raw log line, not only batch-level summary.
                raw_logs = list(getattr(result, "raw_logs", []) or [])
                streak_by_ip = {}
                inferred_alert_keys = set()
                for raw_line in raw_logs:
                    classification, priority, source = self._classify_raw_line(raw_line, streak_by_ip)
                    row_type = "Alert" if priority != "P4-Low" else "Normal"
                    if row_type == "Alert":
                        alerts_count += 1
                        inferred_alert_keys.add(self._alert_dedup_key(classification, priority, source))
                    else:
                        normal_count += 1

                    rows.append({
                        "time": batch_time,
                        "type": row_type,
                        "priority": priority,
                        "classification": classification,
                        "source": source,
                        "batch_id": batch_id,
                        "details": raw_line,
                        "raw_log": raw_line,
                    })

                for alert in result.alerts:
                    alert_key = self._alert_dedup_key(
                        alert.classification,
                        alert.priority,
                        alert.source_ip or "N/A",
                    )
                    if alert_key in inferred_alert_keys:
                        # Skip duplicate rendering when the same threat is already
                        # represented by a classified raw log row in this batch.
                        continue

                    alerts_count += 1
                    
                    rows.append({
                        "time": alert.timestamp.strftime("%H:%M:%S") if hasattr(alert.timestamp, "strftime") else batch_time,
                        "type": "Alert",
                        "priority": alert.priority,
                        "classification": alert.classification,
                        "source": alert.source_ip or "N/A",
                        "batch_id": batch_id,
                        "details": alert.reasoning or "",
                        "raw_log": alert.reasoning or "",
                    })

                # Backward-compatibility for old results that don't include raw_logs.
                if not raw_logs:
                    estimated_normal = max(int(result.raw_count) - len(result.alerts), 0)
                    if estimated_normal > 0:
                        normal_count += estimated_normal
                        rows.append({
                            "time": batch_time,
                            "type": "Normal",
                            "priority": "P4-Low",
                            "classification": "Routine Activity",
                            "source": "N/A",
                            "batch_id": batch_id,
                            "details": f"{estimated_normal} normal logs in this batch",
                            "raw_log": f"batch={batch_id} normal_count={estimated_normal}",
                        })

            total_visible = alerts_count + normal_count
            self.counter_label.setText(
                f"Total: {total_visible} • Alerts: {alerts_count} • Normal: {normal_count}"
            )

            self._rows = rows
            self._render_rows(rows)

        except Exception as e:
            self.table.setRowCount(0)
            self.table.hide()
            self.empty_label.setText(f"❌ Error loading logs: {str(e)}")
            self.empty_label.show()

    def _render_rows(self, rows: list):
        if self._search_text:
            rows = [
                r for r in rows
                if self._search_text in str(r.get("classification", "")).lower()
                or self._search_text in str(r.get("details", "")).lower()
                or self._search_text in str(r.get("batch_id", "")).lower()
                or self._search_text in str(r.get("type", "")).lower()
                or self._search_text in str(r.get("source", "")).lower()
            ]

        if not rows:
            self.table.setRowCount(0)
            self.table.hide()
            self.empty_label.setText("No logs to display.")
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.table.show()
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                row["time"],
                row["type"],
                row["priority"],
                row["classification"],
                row["source"],
                row["batch_id"],
                row["details"],
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row)
                self.table.setItem(row_index, col, item)

            row_type = row["type"].lower()
            text_primary = (self._theme or {}).get("text_primary", "#ffffff")
            success_text = (self._theme or {}).get("success_text", "#4CAF50")
            warning_text = (self._theme or {}).get("warning_text", "#ff8800")
            critical_text = (self._theme or {}).get("critical_text", "#ff4444")

            if row_type == "alert":
                priority_l = row["priority"].lower()
                if "critical" in priority_l:
                    color = QColor(critical_text)
                elif "high" in priority_l or "medium" in priority_l:
                    color = QColor(warning_text)
                else:
                    color = QColor(text_primary)
            else:
                color = QColor(success_text)

            for col in range(self.table.columnCount()):
                cell = self.table.item(row_index, col)
                if cell is not None:
                    cell.setForeground(color)

        self.table.resizeColumnsToContents()

    @staticmethod
    def _normalize_alert_classification(classification: str) -> str:
        value = (classification or "").strip().lower()
        if "suspicious" in value:
            return "suspicious"
        if "bruteforce" in value or "brute force" in value:
            return "bruteforce"
        if "exfiltration" in value:
            return "exfiltration"
        if "ddos" in value or "flood" in value:
            return "ddos"
        if "malware" in value:
            return "malware"
        return value

    @classmethod
    def _alert_dedup_key(cls, classification: str, priority: str, source: str) -> tuple[str, str, str]:
        normalized = cls._normalize_alert_classification(classification)
        priority_l = (priority or "").strip().lower()
        if "critical" in priority_l:
            priority_band = "critical"
        elif "high" in priority_l:
            priority_band = "high"
        elif "medium" in priority_l:
            priority_band = "medium"
        else:
            priority_band = "low"
        source_norm = (source or "N/A").strip().lower()
        return normalized, priority_band, source_norm

    def _classify_raw_line(self, raw_line: str, streak_by_ip: dict) -> tuple[str, str, str]:
        """Best-effort inline severity classification for All Logs rendering."""
        line = raw_line or ""

        # JSON logs are common in uploads; classify them explicitly first.
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                src_ip = str(payload.get("src_ip", payload.get("source_ip", payload.get("ip", "N/A"))))
                dst_ip = str(payload.get("dst_ip", payload.get("destination_ip", payload.get("dest_ip", "N/A"))))
                action = str(payload.get("action", payload.get("event", ""))).lower()
                status = str(payload.get("status", "")).lower()

                attempts_raw = payload.get("attempt_count", payload.get("attempts", 0))
                try:
                    attempts = int(attempts_raw or 0)
                except (ValueError, TypeError):
                    attempts = 0

                pps_raw = payload.get("packets_per_second", payload.get("pps", 0))
                try:
                    packets_per_second = int(pps_raw or 0)
                except (ValueError, TypeError):
                    packets_per_second = 0

                bytes_sent_raw = payload.get("bytes_sent", 0)
                try:
                    bytes_sent = int(bytes_sent_raw or 0)
                except (ValueError, TypeError):
                    bytes_sent = 0

                size_mb = int(bytes_sent / (1024 * 1024)) if bytes_sent > 0 else 0
                external_dst = dst_ip not in {"N/A", ""} and not dst_ip.startswith(("192.168.", "10.", "172.16."))

                if action in {"flood", "ddos", "dos"} or packets_per_second >= 40000:
                    return "DDoS", "P1-Critical", src_ip
                if packets_per_second >= 10000:
                    return "DDoS", "P2-High", src_ip
                if action in {"login_attempt", "login", "user_login"} and (status in {"failed", "blocked", "denied"} or attempts >= 5):
                    return "BruteForce", "P2-High", src_ip
                if size_mb > 500 and external_dst:
                    return "Exfiltration", "P2-High", src_ip
                if str(payload.get("filename", payload.get("file", ""))).lower().endswith(".exe"):
                    return "Malware", "P1-Critical", src_ip

                return "Routine Activity", "P4-Low", src_ip
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Parse common fields used by the project's text format.
        src_match = re.search(r'\b(?:ip|src_ip)=([^\s]+)', line)
        dst_match = re.search(r'\bdst_ip=([^\s]+)', line)
        size_match = re.search(r'\bsize=(\d+)MB\b', line)
        file_match = re.search(r'\bfile=([^\s]+)', line)

        src_ip = src_match.group(1) if src_match else "N/A"
        dst_ip = dst_match.group(1) if dst_match else "N/A"
        size_mb = int(size_match.group(1)) if size_match else 0
        filename = file_match.group(1).lower() if file_match else ""

        # Track continuous failed logins by source IP.
        if "UserLogin failed" in line and src_ip != "N/A":
            streak_by_ip[src_ip] = streak_by_ip.get(src_ip, 0) + 1
        elif "UserLogin success" in line and src_ip != "N/A":
            streak_by_ip[src_ip] = 0

        failed_streak = streak_by_ip.get(src_ip, 0)
        external_dst = dst_ip not in {"N/A"} and not dst_ip.startswith(("192.168.", "10.", "172.16."))

        # Critical patterns
        if failed_streak >= 10:
            return "BruteForce", "P1-Critical", src_ip
        if size_mb > 2000 and external_dst:
            return "Exfiltration", "P1-Critical", src_ip
        if filename and ("payload" in filename or filename == "payload.exe"):
            return "Malware", "P1-Critical", src_ip

        # High patterns
        if failed_streak >= 5:
            return "BruteForce", "P2-High", src_ip
        if size_mb > 500:
            return "Exfiltration", "P2-High", src_ip

        # Medium patterns
        if 2 <= failed_streak <= 4:
            return "Suspicious Login", "P3-Medium", src_ip
        if 100 <= size_mb <= 400:
            return "Suspicious Transfer", "P3-Medium", src_ip

        return "Routine Activity", "P4-Low", src_ip

    def _create_alert_from_selection(self):
        """Create a manual alert from selected log row in one click."""
        row_index = self.table.currentRow()
        if row_index < 0:
            QMessageBox.information(self, "Create Alert", "Select a log row first.")
            return

        payload = self.table.item(row_index, 0).data(Qt.ItemDataRole.UserRole)
        if not payload:
            QMessageBox.warning(self, "Create Alert", "Could not read selected row.")
            return

        source_text = payload.get("raw_log") or payload.get("details") or payload.get("classification")
        created = self.bridge.create_manual_alert(
            raw_log=str(source_text),
            classification="ManualEscalation",
            priority="P2-High",
            source_ip=payload.get("source", "N/A"),
        )

        if created:
            QMessageBox.information(self, "Create Alert", "Alert created from selected log.")
            self.refresh()
        else:
            QMessageBox.warning(self, "Create Alert", "Unable to create alert from selected log.")

    def _clear_current_batch(self):
        """Clear only current batch/session results from UI and backend store."""
        confirm = QMessageBox.question(
            self,
            "Clear Current Batch",
            "This will remove logs from the current upload batch only.\n\nOther sessions will remain. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            removed_count = self.bridge.clear_current_batch()
            if removed_count > 0:
                QMessageBox.information(self, "Clear Current Batch", f"Removed {removed_count} result(s) from current batch.")
            else:
                QMessageBox.information(self, "Clear Current Batch", "No results to clear in current batch.")
            self._rows = []
            self.table.setRowCount(0)
            self.counter_label.setText("Total: 0 • Alerts: 0 • Normal: 0")
            self.empty_label.setText("No logs to display.")
            self.empty_label.show()
            self.table.hide()
        except Exception as e:
            QMessageBox.warning(self, "Clear Current Batch", f"Failed to clear batch: {str(e)}")

    def _clear_all_sessions(self):
        """Clear all stored analysis results from all sessions (UI and backend)."""
        confirm = QMessageBox.question(
            self,
            "Clear All Sessions",
            "⚠️ This will remove ALL logs from ALL upload sessions.\n\nThis cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.bridge.clear_all_results()
            self._rows = []
            self.table.setRowCount(0)
            self.counter_label.setText("Total: 0 • Alerts: 0 • Normal: 0")
            self.empty_label.setText("No logs to display.")
            self.empty_label.show()
            self.table.hide()
            QMessageBox.information(self, "Clear All Sessions", "All results have been cleared.")
        except Exception as e:
            QMessageBox.warning(self, "Clear All Sessions", f"Failed to clear results: {str(e)}")
