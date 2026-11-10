"""One stylesheet for the whole window: one palette, three text sizes, two button kinds."""

from __future__ import annotations

from PyQt5 import QtWidgets

INK = "#17243A"
MUTED = "#566275"
LINE = "#D3DAE3"
GROUND = "#F2F5F8"
SURFACE = "#FFFFFF"
ACCENT = "#148FBD"
ACCENT_DARK = "#0F7396"
ACCENT_SOFT = "#E3F1F8"

APP_STYLESHEET = f"""
QWidget {{
    font-family: "Microsoft JhengHei UI", "Microsoft JhengHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {INK};
}}
QMainWindow, QWidget#resultPane {{ background: {GROUND}; }}
QWidget#sidebar, QScrollArea#sidebarScroll, QWidget#sidebarBody {{ background: {SURFACE}; }}
QFrame#sidebarEdge {{ background: {LINE}; max-width: 1px; }}
QScrollArea {{ border: none; }}

QLabel#appTitle {{ font-size: 18px; font-weight: 700; }}
QLabel#stepTitle {{ font-size: 14px; font-weight: 700; padding-top: 6px; }}
QLabel#hint, QLabel#fieldLabel {{ font-size: 12px; color: {MUTED}; }}
QLabel#emptyState {{ font-size: 15px; color: {MUTED}; }}

QLineEdit, QPlainTextEdit {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 4px;
    padding: 4px 6px;
    min-height: 20px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {ACCENT}; }}
QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit {{ min-height: 24px; }}
QLineEdit#dropTarget {{ border: 1px dashed #AAB2BD; padding: 8px 6px; }}

QPushButton {{
    background: {SURFACE};
    border: 1px solid #AAB2BD;
    border-radius: 4px;
    padding: 6px 14px;
    min-height: 20px;
}}
QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT_DARK}; }}
QPushButton:disabled {{ color: #98A2B3; border-color: {LINE}; background: {GROUND}; }}
QPushButton[primary="true"] {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: white;
    font-weight: 700;
}}
QPushButton[primary="true"]:hover {{ background: {ACCENT_DARK}; color: white; }}
QPushButton[primary="true"]:disabled {{ background: #B9C4CF; border-color: #B9C4CF; color: white; }}
QPushButton#analyzeButton {{ padding: 10px 14px; font-size: 14px; }}

QToolButton#channelButton {{
    background: {GROUND};
    border: 1px dashed #AAB2BD;
    border-radius: 4px;
    color: {MUTED};
    font-size: 11px;
}}
QToolButton#channelButton:checked {{
    background: {ACCENT_SOFT};
    border: 1px solid {ACCENT};
    color: {INK};
}}
QToolButton#channelButton[state="partial"]:checked {{
    background: #FFF4D6;
    border: 1px solid #D28A18;
}}
QToolButton#channelButton[state="invalid"] {{ background: #FCE6E6; border: 1px solid #E0A3A3; }}
QToolButton#channelButton:disabled {{ color: #98A2B3; }}

QTabWidget::pane {{ border: 1px solid {LINE}; background: {SURFACE}; top: -1px; }}
QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    color: {MUTED};
}}
QTabBar::tab:selected {{ color: {INK}; font-weight: 700; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {INK}; }}

QListWidget {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 4px; }}
QFrame#statusStrip {{ background: #E6EAEF; }}
QFrame#statusStrip QLabel {{ font-size: 12px; color: {MUTED}; }}
"""


def set_primary(button: QtWidgets.QPushButton, primary: bool) -> None:
    """Mark the one button that carries the next step; restyle it immediately."""
    button.setProperty("primary", primary)
    button.style().unpolish(button)
    button.style().polish(button)
