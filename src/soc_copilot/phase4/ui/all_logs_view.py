"""All Logs view - monitors both alert and normal logs with manual escalation."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


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

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Refresh logs")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Time", "Type", "Priority", "Classification", "Source", "Batch ID", "Details"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
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

                for alert in result.alerts:
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
                if self._search_text in r["classification"].lower()
                or self._search_text in r["details"].lower()
                or self._search_text in r["batch_id"].lower()
                or self._search_text in r["type"].lower()
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
            if row_type == "alert":
                color = QColor("#ff4444") if "critical" in row["priority"].lower() else QColor("#ff8800")
            else:
                color = QColor("#4CAF50")

            for col in range(self.table.columnCount()):
                cell = self.table.item(row_index, col)
                if cell is not None:
                    cell.setForeground(color)

        self.table.resizeColumnsToContents()

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
