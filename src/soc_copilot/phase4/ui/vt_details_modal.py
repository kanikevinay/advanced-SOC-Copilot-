"""VirusTotal Information Details Dialog"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, 
    QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from soc_copilot.integrations import VTIPInfo


class VTDetailsModal(QDialog):
    """Modal dialog showing VirusTotal reputation details for an IP"""
    
    def __init__(self, ip: str, vt_info: VTIPInfo, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.vt_info = vt_info
        self.setWindowTitle(f"VirusTotal Report - {ip}")
        self.setGeometry(100, 100, 600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a1a;
            }
        """)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the modal UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel(f"🔍 IP Reputation: {self.ip}")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d4ff;")
        layout.addWidget(title)
        
        # Risk Level Badge
        risk_color = self._get_risk_color(self.vt_info.risk_level)
        risk_badge = QFrame()
        risk_badge.setStyleSheet(f"""
            QFrame {{
                background-color: {risk_color};
                border-radius: 4px;
                padding: 10px;
            }}
        """)
        risk_layout = QHBoxLayout()
        risk_label = QLabel(f"Risk Level: {self.vt_info.risk_level}")
        risk_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        risk_layout.addWidget(risk_label)
        risk_layout.addStretch()
        risk_badge.setLayout(risk_layout)
        layout.addWidget(risk_badge)
        
        # Scroll area for details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical {
                background-color: #16213e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #2a3f5f;
                border-radius: 4px;
            }
        """)
        
        # Details container
        details_widget = QFrame()
        details_widget.setStyleSheet("background-color: transparent;")
        details_layout = QVBoxLayout()
        details_layout.setSpacing(10)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Reputation
        details_layout.addWidget(self._create_detail_field(
            "Reputation Score",
            str(self.vt_info.reputation),
            "#00d4ff" if self.vt_info.reputation >= 0 else "#ff3333"
        ))
        
        # Malicious Votes
        details_layout.addWidget(self._create_detail_field(
            "Malicious Votes",
            str(self.vt_info.malicious_votes),
            "#ff3333" if self.vt_info.malicious_votes > 5 else "#ffaa00"
        ))
        
        # Undetected Votes
        details_layout.addWidget(self._create_detail_field(
            "Undetected Votes",
            str(self.vt_info.undetected_votes),
            "#ffaa00"
        ))
        
        # Last Update
        details_layout.addWidget(self._create_detail_field(
            "Last Analysis",
            self.vt_info.last_update if self.vt_info.last_update != "Unknown" else "Not analyzed",
            "#888888"
        ))
        
        # ASN (if available)
        if self.vt_info.asn:
            details_layout.addWidget(self._create_detail_field(
                "ASN",
                self.vt_info.asn,
                "#00d4ff"
            ))
        
        # Country (if available)
        if self.vt_info.country:
            details_layout.addWidget(self._create_detail_field(
                "Country",
                self.vt_info.country,
                "#00d4ff"
            ))
        
        # Error message (if any)
        if self.vt_info.error:
            details_layout.addWidget(self._create_detail_field(
                "Status",
                self.vt_info.error,
                "#ffaa00"
            ))
        
        details_layout.addStretch()
        details_widget.setLayout(details_layout)
        scroll.setWidget(details_widget)
        layout.addWidget(scroll)
        
        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a2744;
                color: #ffffff;
                border: 1px solid #2a3f5f;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2a3f5f;
            }
        """)
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)
        
        layout.addLayout(actions_layout)
        self.setLayout(layout)
    
    def _create_detail_field(self, label: str, value: str, color: str = "#ffffff") -> QFrame:
        """Create a styled detail field"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 1px solid #1a2744;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold;")
        
        val = QLabel(value)
        val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        val.setWordWrap(True)
        
        layout.addWidget(lbl)
        layout.addWidget(val)
        frame.setLayout(layout)
        
        return frame
    
    def _get_risk_color(self, risk_level: str) -> str:
        """Get color for risk level"""
        colors = {
            "Critical": "#cc0000",
            "High": "#ff3333",
            "Medium": "#ffaa00",
            "Low": "#ffdd00",
            "Clean": "#00cc00",
            "Unknown": "#666666",
        }
        return colors.get(risk_level, "#666666")
