"""System Status Bar - Consolidated Real-time Backend State Visualization

Redesigned from 6 LEDs to 3 consolidated indicators:
- Pipeline: ML model status
- Ingestion: Log source and processing status  
- Governance: Kill switch + permissions combined

With tooltip expansion for detailed information.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QPushButton,
    QGraphicsDropShadowEffect, QToolTip
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class StatusIndicator(QWidget):
    """LED-style status indicator with label and tooltip expansion"""
    
    COLORS = {
        "green": "#4CAF50",
        "yellow": "#FFC107", 
        "red": "#f44336",
        "blue": "#2196F3",
        "gray": "#757575"
    }
    
    def __init__(self, label: str, initial_color: str = "gray"):
        super().__init__()
        self._color = initial_color
        self._details = []
        self._init_ui(label)
    
    def _init_ui(self, label: str):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)
        
        # LED dot with glow effect
        self.led = QLabel("●")
        self.led.setFont(QFont("Segoe UI", 11))
        self._update_led_style()
        layout.addWidget(self.led)
        
        # Label
        self.label = QLabel(label)
        self.label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.label)
        
        # Value
        self.value = QLabel("")
        self.value.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.value)
        
        # Info icon for tooltip
        self.info_icon = QLabel("ⓘ")
        self.info_icon.setFont(QFont("Segoe UI", 9))
        self.info_icon.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.info_icon.setVisible(False)
        layout.addWidget(self.info_icon)
        
        self.setLayout(layout)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme = {
            "text_primary": "#ffffff",
            "accent": "#00d4ff",
            "text_muted": "#555555",
        }
        self.apply_theme({
            "text_primary": "#ffffff",
            "accent": "#00d4ff",
            "text_muted": "#555555",
        })
    
    def _update_led_style(self):
        color = self.COLORS.get(self._color, self.COLORS["gray"])
        # Text shadow for glow effect
        self.led.setStyleSheet(f"""
            color: {color};
        """)
    
    def set_state(self, color: str, value: str = "", details: list = None):
        """Set indicator state with optional tooltip details"""
        self._color = color
        self._update_led_style()
        self.value.setText(value)
        
        if details:
            self._details = details
            self.info_icon.setVisible(True)
            tooltip_text = "\n".join([f"• {d}" for d in details])
            self.setToolTip(tooltip_text)
        else:
            self._details = []
            self.info_icon.setVisible(False)
            self.setToolTip("")

    def apply_theme(self, theme: dict):
        """Apply theme colors to static status indicator elements."""
        self._theme = theme
        self.label.setStyleSheet(f"color: {theme['text_primary']};")
        self.value.setStyleSheet(f"color: {theme['accent']};")
        self.info_icon.setStyleSheet(f"color: {theme['text_muted']};")
    
    def enterEvent(self, event):
        if self._details:
            self.info_icon.setStyleSheet(f"color: {self._theme['accent']};")
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.info_icon.setStyleSheet(f"color: {self._theme['text_muted']};")
        super().leaveEvent(event)


class SystemStatusBar(QFrame):
    """Consolidated status bar with 3 indicators (reduced from 6)
    
    Indicators:
    1. Pipeline - ML model loading and active status
    2. Ingestion - Log sources, processing, buffer status
    3. Governance - Kill switch + permissions
    """
    
    status_update = pyqtSignal(dict)
    theme_toggle_requested = pyqtSignal()
    
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self._init_ui()
        self._init_polling()
    
    def _init_ui(self):
        self.setFixedHeight(40)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(25)
        
        # Pipeline indicator (combines old Pipeline LED)
        self.pipeline_led = StatusIndicator("Pipeline")
        layout.addWidget(self.pipeline_led)
        
        # Separator
        layout.addWidget(self._separator())
        
        # Ingestion indicator (combines old Ingestion + Buffer LEDs)
        self.ingestion_led = StatusIndicator("Ingestion")
        layout.addWidget(self.ingestion_led)
        
        # Separator
        layout.addWidget(self._separator())
        
        # Governance indicator (combines old Kill Switch + Admin + Permissions LEDs)
        self.governance_led = StatusIndicator("Governance")
        layout.addWidget(self.governance_led)
        
        layout.addStretch()

        self.theme_button = QPushButton("Theme: Dark")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setToolTip("Cycle theme: Dark → Bright → System")
        self.theme_button.clicked.connect(lambda: self.theme_toggle_requested.emit())
        layout.addWidget(self.theme_button)

        layout.addWidget(self._separator())
        
        # Results count (compact)
        self.results_label = QLabel("📊 0 results")
        self.results_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.results_label)
        
        # Separator
        layout.addWidget(self._separator())
        
        # Last update time
        self.update_time = QLabel("")
        self.update_time.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.update_time)
        
        self.setLayout(layout)
        self._separators = self.findChildren(QLabel)
        self.apply_theme({
            "status_bg": "#0a1225",
            "border": "#1a2744",
            "button_bg": "#16213e",
            "button_hover": "#1a2744",
            "button_pressed": "#0f1629",
            "button_fg": "#ffffff",
            "border_strong": "#2a3f5f",
            "text_secondary": "#888888",
            "text_muted": "#555555",
            "text_primary": "#ffffff",
            "accent": "#00d4ff",
        })
    
    def _separator(self) -> QLabel:
        sep = QLabel("|")
        return sep

    def apply_theme(self, theme: dict):
        """Apply theme colors to the status bar."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['status_bg']};
                border-bottom: 1px solid {theme['border']};
            }}
        """)
        for indicator in (self.pipeline_led, self.ingestion_led, self.governance_led):
            indicator.apply_theme(theme)

        self.theme_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_fg']};
                border: 1px solid {theme['border_strong']};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme['button_pressed']};
            }}
        """)
        self.results_label.setStyleSheet(f"color: {theme['text_secondary']};")
        self.update_time.setStyleSheet(f"color: {theme['text_muted']};")
        for child in self.findChildren(QLabel):
            if child.text() == "|":
                child.setStyleSheet(f"color: {theme['border']};")

    def set_theme_button_text(self, text: str, tooltip: str = ""):
        """Update the theme button label."""
        self.theme_button.setText(text)
        if tooltip:
            self.theme_button.setToolTip(tooltip)
    
    def _init_polling(self):
        """Start polling for status updates - 2 seconds (optimized from 1s)"""
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._update_status)
        self.poll_timer.start(2000)
        
        # Initial update
        self._update_status()
    
    def _update_status(self):
        """Poll backend for current status"""
        from datetime import datetime
        
        try:
            stats = self.bridge.get_stats()
            
            # ─────────────────────────────────────────────────────────
            # PIPELINE STATUS
            # ─────────────────────────────────────────────────────────
            pipeline_loaded = stats.get("pipeline_loaded", False)
            pipeline_details = []
            
            if pipeline_loaded:
                self.pipeline_led.set_state("green", "Active", [
                    "ML models loaded",
                    "Ready for analysis"
                ])
            else:
                self.pipeline_led.set_state("yellow", "Loading", [
                    "ML models initializing",
                    "Please wait..."
                ])
            
            # ─────────────────────────────────────────────────────────
            # INGESTION STATUS (combines sources + buffer)
            # ─────────────────────────────────────────────────────────
            running = stats.get("running", False)
            sources = stats.get("sources_count", 0)
            buffer_size = stats.get("size", 0)
            max_size = stats.get("max_size", 10000)
            dropped = stats.get("dropped_count", 0)
            
            ingestion_details = [
                f"Sources: {sources}",
                f"Buffer: {buffer_size}/{max_size}"
            ]
            
            if dropped > 0:
                ingestion_details.append(f"⚠️ Dropped: {dropped}")
            
            if running and sources > 0:
                if dropped > 0 or buffer_size > max_size * 0.8:
                    self.ingestion_led.set_state("yellow", f"Active ({sources})", ingestion_details)
                else:
                    self.ingestion_led.set_state("blue", f"Active ({sources})", ingestion_details)
            elif sources > 0:
                self.ingestion_led.set_state("gray", f"Idle ({sources})", ingestion_details)
            else:
                self.ingestion_led.set_state("gray", "Not Started", [
                    "No log sources configured",
                    "Upload logs to begin"
                ])
            
            # ─────────────────────────────────────────────────────────
            # GOVERNANCE STATUS (combines kill switch + permissions)
            # ─────────────────────────────────────────────────────────
            shutdown = stats.get("shutdown_flag", False)
            permission_check = stats.get("permission_check", {})
            has_permission = permission_check.get("has_permission", True)
            
            governance_details = []
            
            if shutdown:
                governance_details.append("🛑 Kill Switch: ACTIVE")
                governance_details.append("All ML processing halted")
                self.governance_led.set_state("red", "HALTED", governance_details)
            elif not has_permission:
                governance_details.append("Kill Switch: OFF")
                governance_details.append("⚠️ Limited permissions")
                governance_details.append("Run as admin for system logs")
                self.governance_led.set_state("yellow", "Limited", governance_details)
            else:
                governance_details.append("Kill Switch: OFF")
                governance_details.append("Full system access")
                self.governance_led.set_state("green", "Active", governance_details)
            
            # ─────────────────────────────────────────────────────────
            # RESULTS COUNT
            # ─────────────────────────────────────────────────────────
            results_stored = stats.get("results_stored", 0)
            self.results_label.setText(f"📊 {results_stored} results")
            
            # Update time
            self.update_time.setText(datetime.now().strftime("%H:%M:%S"))
            
            # Emit status for listeners
            self.status_update.emit(stats)
            
        except Exception as e:
            self.pipeline_led.set_state("red", "Error")
            self.update_time.setText(f"Error: {str(e)[:15]}")


class PermissionBanner(QFrame):
    """Warning banner for permission issues"""
    
    dismissed = pyqtSignal()
    run_as_admin_requested = pyqtSignal()
    
    def __init__(self, message: str, icon: str = "⚠️"):
        super().__init__()
        self._init_ui(message, icon)
    
    def _init_ui(self, message: str, icon: str):
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d00;
                border: 1px solid #665c00;
                border-radius: 6px;
                margin: 5px 15px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 14))
        layout.addWidget(icon_label)
        
        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #ffcc00; font-size: 12px;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)
        
        # Action button
        action_btn = QLabel("Run as Admin")
        action_btn.setStyleSheet("""
            color: #ffcc00;
            font-size: 11px;
            text-decoration: underline;
            padding: 5px 10px;
        """)
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        action_btn.mousePressEvent = lambda e: self.run_as_admin_requested.emit()
        layout.addWidget(action_btn)
        
        # Close button
        close_btn = QLabel("✕")
        close_btn.setStyleSheet("color: #888; font-size: 14px; padding: 5px;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self._dismiss()
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def _dismiss(self):
        self.hide()
        self.dismissed.emit()


class KillSwitchBanner(QFrame):
    """Critical banner when kill switch is active"""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a0000, stop:1 #2d0000);
                border: 2px solid #ff0000;
                border-radius: 6px;
                margin: 5px 15px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 12, 15, 12)
        
        icon_label = QLabel("🛑")
        icon_label.setFont(QFont("Segoe UI Emoji", 16))
        layout.addWidget(icon_label)
        
        msg = QLabel("KILL SWITCH ACTIVE")
        msg.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold;")
        layout.addWidget(msg)
        
        desc = QLabel("All ML processing halted • Edit config/kill_switch.yaml to disable")
        desc.setStyleSheet("color: #ff8888; font-size: 11px;")
        layout.addWidget(desc, 1)
        
        self.setLayout(layout)
        self.hide()  # Hidden by default
    
    def show_if_active(self, is_active: bool):
        if is_active:
            self.show()
        else:
            self.hide()
