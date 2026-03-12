"""Configuration Status Panel with system logs toggle

Provides UI controls for configuration without modifying ML models,
pipeline logic, or auto-starting ingestion.
"""

import platform
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..config import ConfigManager
from ..kill_switch import KillSwitch
from .state_constants import (
    get_ingestion_state, get_governance_state,
    INGESTION_STATES, GOVERNANCE_STATES,
    GovernanceState
)


class ToggleSwitch(QFrame):
    """Custom toggle switch widget"""
    
    def __init__(self, initial_state: bool = False, on_toggle=None):
        super().__init__()
        self._state = initial_state
        self._on_toggle = on_toggle
        self._init_ui()
        self._update_style()
    
    def _init_ui(self):
        self.setFixedSize(60, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.knob = QLabel()
        self.knob.setFixedSize(24, 24)
        
        if self._state:
            layout.addStretch()
            layout.addWidget(self.knob)
        else:
            layout.addWidget(self.knob)
            layout.addStretch()
        
        self.setLayout(layout)
    
    def _update_style(self):
        if self._state:
            self.setStyleSheet("""
                QFrame {
                    background-color: #4CAF50;
                    border-radius: 15px;
                    border: 2px solid #388E3C;
                }
            """)
            self.knob.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #666666;
                    border-radius: 15px;
                    border: 2px solid #444444;
                }
            """)
            self.knob.setStyleSheet("""
                QLabel {
                    background-color: #cccccc;
                    border-radius: 12px;
                }
            """)
    
    def mousePressEvent(self, event):
        self._state = not self._state
        self._update_style()
        self._rebuild_layout()
        if self._on_toggle:
            self._on_toggle(self._state)
    
    def _rebuild_layout(self):
        """Rebuild layout to move knob"""
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            # Don't delete the knob widget
        
        if self._state:
            layout.addStretch()
            layout.addWidget(self.knob)
        else:
            layout.addWidget(self.knob)
            layout.addStretch()
    
    def is_on(self) -> bool:
        return self._state
    
    def set_state(self, state: bool):
        if self._state != state:
            self._state = state
            self._update_style()
            self._rebuild_layout()


class StatusIndicator(QFrame):
    """Status indicator with colored dot and label"""
    
    def __init__(self, label: str, status: str = "Unknown", color: str = "#888888"):
        super().__init__()
        self._init_ui(label, status, color)
    
    def _init_ui(self, label: str, status: str, color: str):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Colored indicator dot
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {color}; font-size: 16px;")
        layout.addWidget(self.dot)
        
        # Label
        label_widget = QLabel(f"{label}:")
        self.label_widget = label_widget
        layout.addWidget(label_widget)
        
        # Status value
        self.status_label = QLabel(status)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
        self.apply_theme({"text_secondary": "#888888", "text_primary": "#ffffff"})
    
    def update_status(self, status: str, color: str):
        """Update status text and color"""
        self.status_label.setText(status)
        self.dot.setStyleSheet(f"color: {color}; font-size: 16px;")

    def apply_theme(self, theme: dict):
        """Apply theme colors to indicator labels."""
        self.label_widget.setStyleSheet(f"color: {theme['text_secondary']}; font-weight: bold;")
        self.status_label.setStyleSheet(f"color: {theme['text_primary']};")


class ConfigPanel(QWidget):
    """Configuration Status Panel with toggle and status display
    
    Displays:
    - System Logs toggle (writes to YAML, does NOT start ingestion)
    - Restart Required warning when config changes
    - Read-only status indicators for system state
    """
    
    def __init__(self, bridge=None, project_root: Optional[Path] = None):
        super().__init__()
        self.bridge = bridge
        self._theme = None
        
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent.parent.parent
        self.project_root = Path(project_root)
        
        self.config_manager = ConfigManager(self.project_root)
        self.kill_switch = KillSwitch(self.project_root)
        
        self._config_changed = False
        self._init_ui()
        self._refresh_status()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Configuration Status")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.title_label = title
        layout.addWidget(title)
        
        # Restart warning (hidden by default)
        self.restart_warning = QFrame()
        warning_layout = QHBoxLayout()
        warning_icon = QLabel("⚠️")
        warning_icon.setFont(QFont("Arial", 18))
        self.warning_icon = warning_icon
        warning_text = QLabel("Configuration changed. Restart required for changes to take effect.")
        self.warning_text = warning_text
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_text)
        warning_layout.addStretch()
        self.restart_warning.setLayout(warning_layout)
        self.restart_warning.setVisible(False)
        layout.addWidget(self.restart_warning)
        
        # System Logs Toggle Section
        toggle_group = QGroupBox("System Log Ingestion")
        self.toggle_group = toggle_group
        toggle_layout = QHBoxLayout()
        
        toggle_label = QLabel("Enable System Logs:")
        self.toggle_label = toggle_label
        toggle_layout.addWidget(toggle_label)
        
        initial_state = self.config_manager.get_system_logs_enabled()
        self.system_logs_toggle = ToggleSwitch(initial_state, self._on_toggle_changed)
        toggle_layout.addWidget(self.system_logs_toggle)
        
        toggle_layout.addStretch()
        
        toggle_note = QLabel("Changes require application restart")
        self.toggle_note = toggle_note
        toggle_layout.addWidget(toggle_note)
        
        toggle_group.setLayout(toggle_layout)
        layout.addWidget(toggle_group)
        
        # Status Indicators Section
        status_group = QGroupBox("System Status")
        self.status_group = status_group
        status_layout = QGridLayout()
        status_layout.setSpacing(10)
        
        # System Logs Enabled
        self.logs_indicator = StatusIndicator("System Logs", "Disabled", "#666666")
        status_layout.addWidget(self.logs_indicator, 0, 0)
        
        # Operating System
        self.os_indicator = StatusIndicator("Operating System", platform.system(), "#2196F3")
        status_layout.addWidget(self.os_indicator, 0, 1)
        
        # Permission Status
        self.perm_indicator = StatusIndicator("Permissions", "Unknown", "#888888")
        status_layout.addWidget(self.perm_indicator, 1, 0)
        
        # Kill Switch
        self.kill_indicator = StatusIndicator("Kill Switch", "Inactive", "#4CAF50")
        status_layout.addWidget(self.kill_indicator, 1, 1)
        
        # Ingestion Status
        self.ingestion_indicator = StatusIndicator("Ingestion", "Not Started", "#666666")
        status_layout.addWidget(self.ingestion_indicator, 2, 0)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Info text
        info_label = QLabel(
            "This panel shows the current configuration and system status. "
            "Only the system logs toggle can be modified. All other indicators are read-only."
        )
        self.info_label = info_label
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        self.setLayout(layout)
        self.apply_theme({
            "window_bg": "#0a0a1a",
            "text_primary": "#ffffff",
            "text_secondary": "#888888",
            "text_muted": "#666666",
            "border": "#444444",
            "warning_bg": "#FFC107",
            "warning_text": "#000000",
            "surface_bg": "#0f1629",
        })

    def apply_theme(self, theme: dict):
        """Apply theme colors to the configuration page."""
        self._theme = theme
        self.setStyleSheet(f"background-color: {theme['window_bg']};")
        self.title_label.setStyleSheet(f"color: {theme['text_primary']};")
        self.restart_warning.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['warning_bg']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        self.warning_text.setStyleSheet(f"color: {theme['warning_text']}; font-weight: bold;")
        group_style = f"""
            QGroupBox {{
                color: {theme['text_primary']};
                font-weight: bold;
                border: 1px solid {theme['border']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {theme['surface_bg']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """
        self.toggle_group.setStyleSheet(group_style)
        self.status_group.setStyleSheet(group_style)
        self.toggle_label.setStyleSheet(f"color: {theme['text_primary']};")
        self.toggle_note.setStyleSheet(f"color: {theme['text_secondary']}; font-style: italic;")
        self.info_label.setStyleSheet(f"color: {theme['text_muted']}; font-style: italic;")
        for indicator in [
            self.logs_indicator,
            self.os_indicator,
            self.perm_indicator,
            self.kill_indicator,
            self.ingestion_indicator,
        ]:
            indicator.apply_theme(theme)
    
    def _on_toggle_changed(self, new_state: bool):
        """Handle toggle state change"""
        success = self.config_manager.set_system_logs_enabled(new_state)
        if success:
            self._config_changed = True
            self.restart_warning.setVisible(True)
            self._update_logs_indicator(new_state)
    
    def _update_logs_indicator(self, enabled: bool):
        """Update system logs status indicator"""
        if enabled:
            self.logs_indicator.update_status("Enabled", "#4CAF50")
        else:
            self.logs_indicator.update_status("Disabled", "#666666")
    
    def _refresh_status(self):
        """Refresh all status indicators"""
        # System Logs
        logs_enabled = self.config_manager.get_system_logs_enabled()
        self._update_logs_indicator(logs_enabled)
        
        # Permissions (check system log access)
        try:
            from ..ingestion.system_log_reader import SystemLogReader
            reader = SystemLogReader()
            perm_check = reader.validate_system_log_access()
            if perm_check.has_permission:
                self.perm_indicator.update_status("OK", "#4CAF50")
            elif perm_check.requires_elevation:
                self.perm_indicator.update_status("Elevation Required", "#FFC107")
            else:
                self.perm_indicator.update_status("Limited", "#FFC107")
        except Exception:
            self.perm_indicator.update_status("Unknown", "#888888")
        
        # Kill Switch (using centralized governance state for color consistency)
        if self.kill_switch.is_active():
            gov_cfg = GOVERNANCE_STATES[GovernanceState.HALTED]
            self.kill_indicator.update_status("Active", gov_cfg.color)
        else:
            gov_cfg = GOVERNANCE_STATES[GovernanceState.OK]
            self.kill_indicator.update_status("Inactive", gov_cfg.color)
        
        # Ingestion Status (using centralized ingestion states)
        if self.bridge:
            try:
                stats = self.bridge.get_stats()
                running = stats.get('running', False)
                shutdown = stats.get('shutdown_flag', False)
                sources = stats.get('sources_count', 0)
                
                ingestion_state = get_ingestion_state(running, sources, shutdown)
                ingestion_cfg = INGESTION_STATES[ingestion_state]
                self.ingestion_indicator.update_status(ingestion_cfg.label, ingestion_cfg.color)
            except Exception:
                self.ingestion_indicator.update_status("Unknown", "#888888")
        else:
            not_started_cfg = INGESTION_STATES["not_started"]
            self.ingestion_indicator.update_status(not_started_cfg.label, not_started_cfg.color)
    
    def refresh(self):
        """Public method to refresh status (called by timer)"""
        self._refresh_status()
