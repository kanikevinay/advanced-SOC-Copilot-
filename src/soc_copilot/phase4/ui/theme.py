"""Theme helpers for the Phase 4 PyQt UI."""

from __future__ import annotations

from typing import Dict, Tuple

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication


THEME_MODE_LABELS = {
    "dark": "Dark",
    "bright": "Bright",
    "system": "System",
}


THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "name": "dark",
        "window_bg": "#0a0a1a",
        "surface_bg": "#0f1629",
        "surface_alt_bg": "#12192e",
        "panel_bg": "#16213e",
        "panel_hover": "#1a2744",
        "panel_active": "#22355c",
        "status_bg": "#0a1225",
        "sidebar_bg": "#0f1629",
        "border": "#1a2744",
        "border_strong": "#2a3f5f",
        "text_primary": "#ffffff",
        "text_secondary": "#a8b3c7",
        "text_muted": "#6d7b94",
        "accent": "#00d4ff",
        "accent_hover": "#00a8cc",
        "accent_pressed": "#0088aa",
        "accent_fg": "#0a0a1a",
        "button_bg": "#16213e",
        "button_hover": "#1a2744",
        "button_pressed": "#0f1629",
        "button_fg": "#ffffff",
        "input_bg": "#1a2744",
        "input_border": "#2a3f5f",
        "table_alt_bg": "#12192e",
        "selection_bg": "#00d4ff",
        "selection_fg": "#0a0a1a",
        "scrollbar_bg": "#0a0a1a",
        "scrollbar_handle": "#2a3f5f",
        "scrollbar_handle_hover": "#3a5f8f",
        "warning_bg": "#2d2d00",
        "warning_border": "#665c00",
        "warning_text": "#ffcc00",
        "critical_bg": "#4a0000",
        "critical_border": "#ff4444",
        "critical_text": "#ff6666",
        "success_bg": "#004a2a",
        "success_text": "#4CAF50",
        "shadow": "rgba(0, 0, 0, 0.35)",
    },
    "bright": {
        "name": "bright",
        "window_bg": "#f2f5f9",
        "surface_bg": "#ffffff",
        "surface_alt_bg": "#f6f9fc",
        "panel_bg": "#eaf2ff",
        "panel_hover": "#dce9ff",
        "panel_active": "#cfe1ff",
        "status_bg": "#e3ebf7",
        "sidebar_bg": "#e7f0fd",
        "border": "#bccde6",
        "border_strong": "#8ea8cf",
        "text_primary": "#0f1b2d",
        "text_secondary": "#355070",
        "text_muted": "#5b7595",
        "accent": "#0a63c9",
        "accent_hover": "#084ea0",
        "accent_pressed": "#063d7d",
        "accent_fg": "#ffffff",
        "button_bg": "#e7effd",
        "button_hover": "#d9e7fd",
        "button_pressed": "#cbdefb",
        "button_fg": "#0f1b2d",
        "input_bg": "#ffffff",
        "input_border": "#96afcf",
        "table_alt_bg": "#f4f8fe",
        "selection_bg": "#c8ddfb",
        "selection_fg": "#0f1b2d",
        "scrollbar_bg": "#e2eaf7",
        "scrollbar_handle": "#98aed0",
        "scrollbar_handle_hover": "#6f8eb8",
        "warning_bg": "#fff3cf",
        "warning_border": "#d6b14a",
        "warning_text": "#855f00",
        "critical_bg": "#ffe0e0",
        "critical_border": "#cc4242",
        "critical_text": "#a01919",
        "success_bg": "#dcf3e3",
        "success_text": "#1f6f3a",
        "shadow": "rgba(23, 50, 85, 0.14)",
    },
}


def detect_system_theme() -> str:
    """Infer a system theme from the current application palette."""
    app = QApplication.instance()
    if app is None:
        return "dark"

    window_color = app.palette().color(QPalette.ColorRole.Window)
    return "dark" if window_color.lightness() < 128 else "bright"


def resolve_theme_name(theme_mode: str) -> str:
    """Resolve a stored theme mode to a concrete theme name."""
    if theme_mode == "system":
        return detect_system_theme()
    return theme_mode if theme_mode in THEMES else "dark"


def get_theme(theme_mode: str) -> dict[str, str]:
    """Return the concrete theme dictionary for a mode."""
    return THEMES[resolve_theme_name(theme_mode)]


def get_resolved_theme(theme_mode: str) -> Tuple[str, dict[str, str]]:
    """Return both the resolved theme name and its theme tokens."""
    resolved_name = resolve_theme_name(theme_mode)
    return resolved_name, THEMES[resolved_name]


def cycle_theme_mode(theme_mode: str) -> str:
    """Cycle through dark, bright, and system modes."""
    order = ["dark", "bright", "system"]
    try:
        index = order.index(theme_mode)
    except ValueError:
        return "dark"
    return order[(index + 1) % len(order)]


def build_main_window_styles(theme: Dict[str, str]) -> str:
    """Create the shared application stylesheet for the main window."""
    return f"""
        QMainWindow {{
            background-color: {theme['window_bg']};
            color: {theme['text_primary']};
        }}
        QWidget {{
            background-color: {theme['window_bg']};
            color: {theme['text_primary']};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        QTabWidget::pane {{
            border: none;
            background-color: {theme['surface_bg']};
            border-radius: 8px;
        }}
        QTabBar::tab {{
            background-color: {theme['window_bg']};
            color: {theme['text_secondary']};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: {theme['surface_bg']};
            color: {theme['accent']};
            font-weight: bold;
        }}
        QTableWidget {{
            background-color: {theme['surface_bg']};
            alternate-background-color: {theme['table_alt_bg']};
            gridline-color: {theme['border']};
            border: none;
            border-radius: 8px;
            selection-background-color: {theme['selection_bg']};
            selection-color: {theme['selection_fg']};
        }}
        QHeaderView::section {{
            background-color: {theme['status_bg']};
            color: {theme['text_primary']};
            padding: 10px;
            border: none;
            font-weight: bold;
        }}
        QLineEdit, QComboBox {{
            background-color: {theme['input_bg']};
            color: {theme['text_primary']};
            border: 1px solid {theme['input_border']};
            border-radius: 4px;
            padding: 5px 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme['input_bg']};
            color: {theme['text_primary']};
            selection-background-color: {theme['selection_bg']};
            selection-color: {theme['selection_fg']};
        }}
        QScrollBar:vertical {{
            background-color: {theme['scrollbar_bg']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {theme['scrollbar_handle']};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {theme['scrollbar_handle_hover']};
        }}
        QStatusBar {{
            background-color: {theme['status_bg']};
            color: {theme['text_secondary']};
            padding: 5px 15px;
        }}
        QMenuBar {{
            background-color: {theme['status_bg']};
            color: {theme['text_primary']};
            padding: 2px;
        }}
        QMenuBar::item {{
            padding: 5px 10px;
        }}
        QMenuBar::item:selected {{
            background-color: {theme['panel_hover']};
        }}
        QMenu {{
            background-color: {theme['surface_bg']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border']};
        }}
        QMenu::item:selected {{
            background-color: {theme['accent']};
            color: {theme['accent_fg']};
        }}
    """