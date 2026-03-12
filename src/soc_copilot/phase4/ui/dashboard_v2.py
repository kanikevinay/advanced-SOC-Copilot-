"""SOC Dashboard - Zones A-F Architecture

Zone A: Threat Level Banner (primary indicator)
Zone B: System Status Strip (Pipeline/Ingestion/Governance consolidated)
Zone C: Metric Cards Row (secondary metrics)
Zone D: Quick Actions Bar
Zone E: Recent Alerts Timeline (replaces activity feed)
Zone F: Footer Status
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from datetime import datetime

from .state_constants import (
    get_pipeline_state, get_ingestion_state, get_governance_state,
    format_ingestion_label,
    PIPELINE_STATES, INGESTION_STATES, GOVERNANCE_STATES,
    PipelineState, IngestionState, GovernanceState
)


class FileProcessingWorker(QThread):
    """Worker thread for processing uploaded log files without blocking the UI."""

    # Signals to communicate with the main thread
    progress = pyqtSignal(int, int)       # (current_file_index, total_files)
    file_done = pyqtSignal(str, bool)     # (filepath, success)
    all_done = pyqtSignal(int, int)       # (success_count, total_count)
    error = pyqtSignal(str)               # error message

    def __init__(self, bridge, file_paths):
        super().__init__()
        self.bridge = bridge
        self.file_paths = file_paths
        self._cancelled = False

    def cancel(self):
        """Request cancellation of processing."""
        self._cancelled = True

    def run(self):
        """Process files in the background thread."""
        success_count = 0
        total = len(self.file_paths)

        for i, file_path in enumerate(self.file_paths):
            if self._cancelled:
                break
            try:
                self.bridge.add_file_source(file_path)
                success_count += 1
                self.file_done.emit(file_path, True)
            except Exception as e:
                self.file_done.emit(file_path, False)
                self.error.emit(f"Failed to process {file_path}: {str(e)}")

            self.progress.emit(i + 1, total)

        self.all_done.emit(success_count, total)


class ThreatBanner(QFrame):
    """Zone A: Primary threat level indicator"""
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(80)
        self._theme = None
        self._current_level = "normal"
        self._critical_count = 0
        self._high_count = 0
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        
        self.icon_label = QLabel("✅")
        self.icon_label.setFont(QFont("Segoe UI Emoji", 32))
        layout.addWidget(self.icon_label)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.level_label = QLabel("NORMAL")
        self.level_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        
        self.detail_label = QLabel("No critical threats detected")
        self.detail_label.setFont(QFont("Segoe UI", 11))
        
        text_layout.addWidget(self.level_label)
        text_layout.addWidget(self.detail_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        self.apply_theme({"text_secondary": "#888888"})
        self.set_level("normal", 0, 0)
    
    def set_level(self, level: str, critical: int, high: int):
        """Update threat level"""
        levels = {
            "loading": ("#16213e", "#888888", "⏳", "LOADING"),
            "critical": ("#4a0000", "#ff4444", "🚨", "CRITICAL"),
            "high": ("#4a2000", "#ff8800", "⚠️", "HIGH"),
            "elevated": ("#4a4000", "#ffaa00", "⚡", "ELEVATED"),
            "normal": ("#004a2a", "#4CAF50", "●", "NORMAL")
        }
        
        bg, fg, icon, text = levels.get(level, levels["normal"])
        self._current_level = level
        self._critical_count = critical
        self._high_count = high
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 2px solid {fg};
                border-radius: 10px;
            }}
        """)
        
        self.icon_label.setText(icon)
        self.level_label.setText(text)
        self.level_label.setStyleSheet(f"color: {fg};")
        
        if level == "loading":
            self.detail_label.setText("Loading threat analysis...")
        elif critical > 0:
            self.detail_label.setText(f"{critical} critical alerts require immediate attention")
        elif high > 0:
            self.detail_label.setText(f"{high} high-priority alerts detected")
        else:
            self.detail_label.setText("Routine activity only")

    def apply_theme(self, theme: dict):
        """Apply theme colors to the banner's secondary text."""
        self._theme = theme
        self.detail_label.setStyleSheet(f"color: {theme['text_secondary']};")
        self.set_level(self._current_level, self._critical_count, self._high_count)


class SystemStatusStrip(QFrame):
    """Zone B: Consolidated system status"""
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(40)
        self._theme = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.pipeline_label = QLabel("Pipeline: Loading...")
        self.ingestion_label = QLabel("Ingestion: Idle")
        self.governance_label = QLabel("Governance: OK")
        
        for lbl in [self.pipeline_label, self.ingestion_label, self.governance_label]:
            lbl.setFont(QFont("Segoe UI", 10))
            layout.addWidget(lbl)
            layout.addWidget(self._separator())
        
        layout.addStretch()
        
        self.timestamp_label = QLabel("")
        self.timestamp_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.timestamp_label)
        
        self.setLayout(layout)
        self.apply_theme({
            "panel_bg": "#16213e",
            "border": "#1a2744",
            "border_strong": "#2a3f5f",
            "text_secondary": "#888888",
            "text_muted": "#555555",
        })
    
    def _separator(self):
        sep = QLabel("|")
        return sep

    def apply_theme(self, theme: dict):
        """Apply theme colors to the status strip."""
        self._theme = theme
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['panel_bg']};
                border-bottom: 1px solid {theme['border']};
            }}
        """)
        for lbl in (self.pipeline_label, self.ingestion_label, self.governance_label):
            lbl.setStyleSheet(f"color: {theme['text_secondary']};")
        self.timestamp_label.setStyleSheet(f"color: {theme['text_muted']};")
        for child in self.findChildren(QLabel):
            if child.text() == "|":
                child.setStyleSheet(f"color: {theme['border_strong']};")
    
    def update_status(self, pipeline: bool, sources: int, running: bool, killswitch: bool):
        """Update all status indicators using centralized state mappings"""
        # Pipeline
        pipeline_state = get_pipeline_state(pipeline)
        pipeline_cfg = PIPELINE_STATES[pipeline_state]
        self.pipeline_label.setText(f"Pipeline: {pipeline_cfg.icon} {pipeline_cfg.label}")
        self.pipeline_label.setStyleSheet(f"color: {pipeline_cfg.color};")
        
        # Ingestion
        ingestion_state = get_ingestion_state(running, sources, killswitch)
        ingestion_cfg = INGESTION_STATES[ingestion_state]
        ingestion_label = format_ingestion_label(ingestion_state, sources)
        self.ingestion_label.setText(f"Ingestion: {ingestion_cfg.icon} {ingestion_label}")
        self.ingestion_label.setStyleSheet(f"color: {ingestion_cfg.color};")
        
        # Governance
        governance_state = get_governance_state(killswitch, True)
        governance_cfg = GOVERNANCE_STATES[governance_state]
        self.governance_label.setText(f"Governance: {governance_cfg.icon} {governance_cfg.label}")
        self.governance_label.setStyleSheet(f"color: {governance_cfg.color};")
        
        # Timestamp
        self.timestamp_label.setText(datetime.now().strftime("%H:%M:%S"))


class MetricCard(QFrame):
    """Individual metric card"""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, title: str, icon: str, color: str):
        super().__init__()
        self.title = title
        self.color = color
        self._theme = None
        self.setFixedHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui(title, icon, color)
    
    def _init_ui(self, title: str, icon: str, color: str):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 12))
        header.addWidget(icon_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 10))
        self.title_label = title_lbl
        header.addWidget(title_lbl)
        header.addStretch()
        
        self.value_label = QLabel("0")
        self.value_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        
        layout.addLayout(header)
        layout.addWidget(self.value_label)
        layout.addStretch()
        
        self.setLayout(layout)
        self.apply_theme({
            "panel_bg": "#16213e",
            "panel_hover": "#1a2744",
            "text_secondary": "#888888",
        })
    
    def set_value(self, value: int):
        self.value_label.setText(str(value))

    def apply_theme(self, theme: dict):
        """Apply theme colors to the metric card."""
        self._theme = theme
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['panel_bg']};
                border-left: 4px solid {self.color};
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {theme['panel_hover']};
            }}
        """)
        self.title_label.setStyleSheet(f"color: {theme['text_secondary']};")
        self.value_label.setStyleSheet(f"color: {self.color};")
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.title)


class MetricCardsRow(QFrame):
    """Zone C: Metric cards"""
    
    card_clicked = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        self.total_card = MetricCard("Total Alerts", "📊", "#3F51B5")
        self.critical_card = MetricCard("Critical", "🚨", "#ff4444")
        self.high_card = MetricCard("High", "⚠️", "#ff8800")
        self.medium_card = MetricCard("Medium", "📋", "#ffaa00")
        self.low_card = MetricCard("Low", "✓", "#4CAF50")
        
        for card in [self.total_card, self.critical_card, self.high_card, self.medium_card, self.low_card]:
            card.clicked.connect(self.card_clicked.emit)
            layout.addWidget(card)
        
        self.setLayout(layout)
    
    def update_metrics(self, total: int, critical: int, high: int, medium: int, low: int):
        self.total_card.set_value(total)
        self.critical_card.set_value(critical)
        self.high_card.set_value(high)
        self.medium_card.set_value(medium)
        self.low_card.set_value(low)

    def apply_theme(self, theme: dict):
        """Apply theme colors to all metric cards."""
        for card in [self.total_card, self.critical_card, self.high_card, self.medium_card, self.low_card]:
            card.apply_theme(theme)


class QuickActionsBar(QFrame):
    """Zone D: Quick action buttons"""
    
    upload_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self._theme = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(10)
        
        self.upload_btn = QPushButton("📁 Upload Logs")
        self.upload_btn.clicked.connect(self.upload_clicked.emit)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        
        layout.addWidget(self.upload_btn)
        layout.addWidget(self.refresh_btn)
        layout.addStretch()
        
        self.setLayout(layout)
        self.apply_theme({
            "accent": "#00d4ff",
            "accent_hover": "#00a8cc",
            "accent_fg": "#0a0a1a",
            "button_bg": "#424242",
            "button_hover": "#616161",
            "button_fg": "#ffffff",
            "text_muted": "#555555",
            "text_secondary": "#888888",
        })

    def apply_theme(self, theme: dict):
        """Apply theme colors to quick action buttons."""
        self._theme = theme
        self.upload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: {theme['accent_fg']};
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {theme['accent_hover']}; }}
            QPushButton:disabled {{ background-color: {theme['text_muted']}; color: {theme['text_secondary']}; }}
        """)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_fg']};
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {theme['button_hover']}; }}
        """)


class RecentAlertsTimeline(QFrame):
    """Zone E: Recent alerts (virtualized, max 10 rows)"""
    
    alert_clicked = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self._theme = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📋 Recent Alerts")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label = title
        header.addWidget(title)
        header.addStretch()
        
        self.count_label = QLabel("0 alerts")
        header.addWidget(self.count_label)
        
        layout.addLayout(header)
        
        # Table (virtualized to 10 rows max)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Time", "Priority", "Classification", "Source", "Confidence"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(350)  # ~10 rows
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemClicked.connect(self._on_row_clicked)
        
        layout.addWidget(self.table)
        
        # Empty state
        self.empty_label = QLabel("No alerts • Upload logs to begin analysis")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)
        
        self.setLayout(layout)
        self.apply_theme({
            "surface_bg": "#0f1629",
            "text_primary": "#ffffff",
            "text_secondary": "#888888",
            "text_muted": "#666666",
            "border": "#1a2744",
            "scrollbar_bg": "#0a0a1a",
            "scrollbar_handle": "#2a3f5f",
            "scrollbar_handle_hover": "#3a5f8f",
        })
    
    def update_alerts(self, alerts_data: list):
        """Update with latest 10 alerts"""
        if not alerts_data:
            self.table.hide()
            self.empty_label.show()
            self.count_label.setText("0 alerts")
            return
        
        self.table.show()
        self.empty_label.hide()
        
        # Limit to 10 most recent
        recent = alerts_data[:10]
        self.count_label.setText(f"{len(alerts_data)} alerts (showing {len(recent)})")
        
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(recent))
        
        for row, alert in enumerate(recent):
            items = [
                QTableWidgetItem(alert["time"]),
                QTableWidgetItem(alert["priority"]),
                QTableWidgetItem(alert["classification"]),
                QTableWidgetItem(alert["source_ip"]),
                QTableWidgetItem(alert["confidence"])
            ]
            
            for col, item in enumerate(items):
                # Store batch_id in first column using UserRole
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, alert["batch_id"])
                self.table.setItem(row, col, item)
            
            # Color by priority
            color = self._get_priority_color(alert["priority"])
            for col in range(5):
                self.table.item(row, col).setForeground(color)
        
        self.table.setUpdatesEnabled(True)
        self.table.resizeColumnsToContents()

    def apply_theme(self, theme: dict):
        """Apply theme colors to the recent alerts panel."""
        self._theme = theme
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['surface_bg']};
                border: 1px solid {theme['border']};
                border-radius: 10px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {theme['text_primary']};")
        self.count_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 11px;")
        self.empty_label.setStyleSheet(f"color: {theme['text_muted']}; padding: 40px;")

    def _get_priority_color(self, priority: str) -> QColor:
        p = priority.lower()
        if "critical" in p:
            return QColor("#ff4444")
        elif "high" in p:
            return QColor("#ff8800")
        elif "medium" in p:
            return QColor("#ffaa00")
        return QColor("#ffffff")

    def _on_row_clicked(self, item):
        row = item.row()
        batch_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        classification = self.table.item(row, 2).text()
        self.alert_clicked.emit(batch_id, classification)


class LiveAlertDashboard(QFrame):
    """Live alert dashboard that prioritizes critical log alerts."""

    alert_clicked = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._theme = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel("🔴 Live Alert Dashboard")
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.addWidget(self.title_label)
        header.addStretch()

        self.state_badge = QLabel("Watching")
        self.state_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_badge.setMinimumWidth(88)
        header.addWidget(self.state_badge)
        layout.addLayout(header)

        summary = QHBoxLayout()
        summary.setSpacing(12)
        self.critical_summary = QLabel("0 critical")
        self.high_summary = QLabel("0 high")
        self.latest_summary = QLabel("Latest: --")
        for label in (self.critical_summary, self.high_summary, self.latest_summary):
            label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            summary.addWidget(label)
        summary.addStretch()
        layout.addLayout(summary)

        self.feed_table = QTableWidget()
        self.feed_table.setColumnCount(4)
        self.feed_table.setHorizontalHeaderLabels(["Priority", "Time", "Classification", "Source"])
        self.feed_table.verticalHeader().setVisible(False)
        self.feed_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.feed_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.feed_table.setMaximumHeight(260)
        self.feed_table.horizontalHeader().setStretchLastSection(True)
        self.feed_table.itemClicked.connect(self._on_row_clicked)
        layout.addWidget(self.feed_table)

        self.empty_label = QLabel("No live critical or high-priority alerts yet.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

        self.setLayout(layout)
        self.apply_theme({
            "surface_bg": "#0f1629",
            "border": "#1a2744",
            "text_primary": "#ffffff",
            "text_secondary": "#888888",
            "text_muted": "#666666",
            "critical_bg": "#4a0000",
            "critical_border": "#ff4444",
            "critical_text": "#ff6666",
            "warning_bg": "#2d2d00",
            "warning_border": "#665c00",
            "warning_text": "#ffcc00",
            "panel_hover": "#1a2744",
        })

    def apply_theme(self, theme: dict):
        """Apply theme colors to the live alert dashboard."""
        self._theme = theme
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['surface_bg']};
                border: 1px solid {theme['border']};
                border-radius: 10px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {theme['text_primary']};")
        self.critical_summary.setStyleSheet(f"color: {theme['critical_text']};")
        self.high_summary.setStyleSheet(f"color: {theme['warning_text']};")
        self.latest_summary.setStyleSheet(f"color: {theme['text_secondary']};")
        self.empty_label.setStyleSheet(f"color: {theme['text_muted']}; padding: 20px;")

    def update_alerts(self, alerts_data: list):
        """Update the live feed with critical alerts first, then high alerts."""
        critical_alerts = [alert for alert in alerts_data if "critical" in alert["priority"].lower()]
        high_alerts = [alert for alert in alerts_data if "high" in alert["priority"].lower()]
        focus_alerts = (critical_alerts + high_alerts)[:8]

        latest_time = focus_alerts[0]["time"] if focus_alerts else "--"
        self.critical_summary.setText(f"{len(critical_alerts)} critical")
        self.high_summary.setText(f"{len(high_alerts)} high")
        self.latest_summary.setText(f"Latest: {latest_time}")

        if critical_alerts:
            badge_bg = self._theme['critical_bg']
            badge_fg = self._theme['critical_text']
            badge_border = self._theme['critical_border']
            self.state_badge.setText("Critical")
        elif high_alerts:
            badge_bg = self._theme['warning_bg']
            badge_fg = self._theme['warning_text']
            badge_border = self._theme['warning_border']
            self.state_badge.setText("Elevated")
        else:
            badge_bg = self._theme['panel_hover']
            badge_fg = self._theme['text_secondary']
            badge_border = self._theme['border']
            self.state_badge.setText("Watching")

        self.state_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: {badge_fg};
                border: 1px solid {badge_border};
                border-radius: 12px;
                padding: 4px 10px;
                font-weight: bold;
            }}
        """)

        self.feed_table.setRowCount(len(focus_alerts))
        self.feed_table.setVisible(bool(focus_alerts))
        self.empty_label.setVisible(not focus_alerts)

        for row, alert in enumerate(focus_alerts):
            items = [
                QTableWidgetItem(alert["priority"]),
                QTableWidgetItem(alert["time"]),
                QTableWidgetItem(alert["classification"]),
                QTableWidgetItem(alert["source_ip"]),
            ]
            items[0].setData(Qt.ItemDataRole.UserRole, (alert["batch_id"], alert["classification"]))

            for col, item in enumerate(items):
                self.feed_table.setItem(row, col, item)

            if "critical" in alert["priority"].lower():
                foreground = QColor(self._theme["critical_text"])
                background = QColor(self._theme["critical_bg"])
            else:
                foreground = QColor(self._theme["warning_text"])
                background = QColor(self._theme["warning_bg"])

            for col in range(4):
                cell = self.feed_table.item(row, col)
                if cell is not None:
                    cell.setForeground(foreground)
                    if col == 0:
                        cell.setBackground(background)

        self.feed_table.resizeColumnsToContents()

    def _on_row_clicked(self, item):
        payload = self.feed_table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        if payload:
            batch_id, classification = payload
            self.alert_clicked.emit(batch_id, classification)


class Dashboard(QWidget):
    """Main dashboard with Zones A-F"""
    
    navigate_to_alerts = pyqtSignal()
    navigate_to_alerts_filtered = pyqtSignal(str)
    navigate_to_settings = pyqtSignal()
    alert_selected = pyqtSignal(str, str)
    
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self._alerts_cache = []
        self._worker = None  # Background file processing thread
        self._theme = None
        self._init_ui()
        
        # Unified polling (3 seconds)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)
        
        self.refresh()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Zone A: Threat Banner
        self.threat_banner = ThreatBanner()
        layout.addWidget(self.threat_banner)
        
        # Zone B: System Status
        self.status_strip = SystemStatusStrip()
        layout.addWidget(self.status_strip)
        
        # Zone C: Metrics
        self.metrics_row = MetricCardsRow()
        self.metrics_row.card_clicked.connect(self._on_metric_clicked)
        layout.addWidget(self.metrics_row)
        
        # Zone D: Actions
        self.actions_bar = QuickActionsBar()
        self.actions_bar.upload_clicked.connect(self._upload_logs)
        self.actions_bar.refresh_clicked.connect(self.refresh)
        layout.addWidget(self.actions_bar)
        
        # Zone E: Recent Alerts
        alerts_row = QHBoxLayout()
        alerts_row.setSpacing(15)

        self.live_alerts_panel = LiveAlertDashboard()
        self.live_alerts_panel.alert_clicked.connect(self.alert_selected.emit)
        alerts_row.addWidget(self.live_alerts_panel, 1)

        self.alerts_timeline = RecentAlertsTimeline()
        self.alerts_timeline.alert_clicked.connect(self.alert_selected.emit)
        alerts_row.addWidget(self.alerts_timeline, 2)
        layout.addLayout(alerts_row, 1)
        
        # Progress bar for file uploads (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #1a1a2e;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff, stop:1 #00ff88);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        self.apply_theme({
            "window_bg": "#0a0a1a",
            "text_muted": "#666666",
            "panel_bg": "#16213e",
            "border": "#1a2744",
            "accent": "#00d4ff",
            "accent_hover": "#00a8cc",
            "accent_fg": "#0a0a1a",
            "button_bg": "#424242",
            "button_hover": "#616161",
            "button_fg": "#ffffff",
            "text_secondary": "#888888",
            "text_primary": "#ffffff",
            "scrollbar_bg": "#0a0a1a",
            "scrollbar_handle": "#2a3f5f",
            "scrollbar_handle_hover": "#3a5f8f",
            "border_strong": "#2a3f5f",
            "critical_bg": "#4a0000",
            "critical_border": "#ff4444",
            "critical_text": "#ff6666",
            "warning_bg": "#2d2d00",
            "warning_border": "#665c00",
            "warning_text": "#ffcc00",
            "surface_bg": "#0f1629",
            "surface_alt_bg": "#12192e",
            "panel_hover": "#1a2744",
            "success_text": "#4CAF50",
        })
    
    def refresh(self):
        """Unified refresh - single data fetch"""
        # Show loading state
        self.threat_banner.set_level("loading", 0, 0)
        
        try:
            # Single data fetch
            results = self.bridge.get_latest_alerts(limit=100)
            stats = self.bridge.get_stats()
            
            # Process alerts
            total = critical = high = medium = low = 0
            alerts_data = []
            
            for result in results:
                for alert in result.alerts:
                    total += 1
                    p = alert.priority.lower()
                    if "critical" in p:
                        critical += 1
                    elif "high" in p:
                        high += 1
                    elif "medium" in p:
                        medium += 1
                    elif "low" in p:
                        low += 1
                    
                    alerts_data.append({
                        "batch_id": result.batch_id,
                        "time": alert.timestamp.strftime("%H:%M:%S") if hasattr(alert.timestamp, 'strftime') else str(alert.timestamp),
                        "priority": alert.priority,
                        "classification": alert.classification,
                        "source_ip": getattr(alert, 'source_ip', 'N/A'),
                        "confidence": f"{alert.confidence:.2f}" if hasattr(alert, 'confidence') else "N/A"
                    })
            
            self._alerts_cache = alerts_data
            
            # Update Zone A: Threat Banner
            if critical > 0:
                self.threat_banner.set_level("critical", critical, high)
            elif high > 0:
                self.threat_banner.set_level("high", critical, high)
            elif medium > 0:
                self.threat_banner.set_level("elevated", critical, high)
            else:
                self.threat_banner.set_level("normal", critical, high)
            
            # Update Zone B: Status Strip
            self.status_strip.update_status(
                stats.get("pipeline_loaded", False),
                stats.get("sources_count", 0),
                stats.get("running", False),
                stats.get("shutdown_flag", False)
            )
            
            # Update Zone C: Metrics
            self.metrics_row.update_metrics(total, critical, high, medium, low)
            
            # Update live alert dashboard
            self.live_alerts_panel.update_alerts(alerts_data)

            # Update Zone E: Alerts Timeline
            self.alerts_timeline.update_alerts(alerts_data)
            
        except Exception:
            self.threat_banner.set_level("normal", 0, 0)

    def apply_theme(self, theme: dict):
        """Apply theme colors across the dashboard widgets."""
        self._theme = theme
        self.setStyleSheet(f"background-color: {theme['window_bg']}; color: {theme['text_primary']};")
        self.threat_banner.apply_theme(theme)
        self.status_strip.apply_theme(theme)
        self.metrics_row.apply_theme(theme)
        self.actions_bar.apply_theme(theme)
        self.live_alerts_panel.apply_theme(theme)
        self.alerts_timeline.apply_theme(theme)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: {theme['surface_alt_bg']};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {theme['accent']}, stop:1 {theme['success_text']});
                border-radius: 3px;
            }}
        """)
    
    def _on_metric_clicked(self, card_title: str):
        """Handle metric card click"""
        priority_map = {
            "Critical": "critical",
            "High": "high",
            "Medium": "medium",
            "Low": "low",
            "Total Alerts": "all"
        }
        priority = priority_map.get(card_title, "all")
        
        if priority == "all":
            self.navigate_to_alerts.emit()
        else:
            self.navigate_to_alerts_filtered.emit(priority)
    
    def _upload_logs(self):
        """Upload and analyze log files asynchronously via worker thread."""
        # Prevent overlapping uploads
        if self._worker is not None and self._worker.isRunning():
            return
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Log Files", "",
            "Log Files (*.json *.jsonl *.csv *.log);;All (*.*)"
        )
        
        if not files:
            return
        
        # Disable UI controls while processing
        self.actions_bar.upload_btn.setEnabled(False)
        self.actions_bar.upload_btn.setText("⏳ Processing...")
        self.actions_bar.refresh_btn.setEnabled(False)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(files))
        self.progress_bar.setValue(0)
        
        # Create and start worker thread
        self._worker = FileProcessingWorker(self.bridge, files)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.all_done.connect(self._on_worker_done)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
    
    def _on_worker_progress(self, current, total):
        """Update progress bar from worker thread signal."""
        self.progress_bar.setValue(current)
    
    def _on_worker_done(self, success_count, total_count):
        """Handle worker completion — refresh dashboard with new results."""
        self.bridge.start_ingestion()
        self.refresh()
        self.status_strip.timestamp_label.setText(
            f"Processed {success_count}/{total_count} files at {datetime.now().strftime('%H:%M:%S')}"
        )
    
    def _on_worker_finished(self):
        """Clean up worker reference, re-enable UI, and hide progress bar."""
        self.actions_bar.upload_btn.setEnabled(True)
        self.actions_bar.upload_btn.setText("📁 Upload Logs")
        self.actions_bar.refresh_btn.setEnabled(True)
        QTimer.singleShot(1000, self._hide_progress)
        self._worker = None
    
    def _hide_progress(self):
        """Hide the progress bar after a short delay."""
        self.progress_bar.setVisible(False)
