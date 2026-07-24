"""Light and dark themes (QSS) for the installer UI.

The palette mirrors the app itself: orange hour numbers, a gold digital
frame and the digital clock's blue for progress.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    toggle_label: str
    qss: str


LIGHT = Theme(
    name="light",
    toggle_label="Dark Theme",
    qss="""
        QWidget { background: #f4f4f4; color: #1f2937; font-family: 'Segoe UI'; }
        QLabel#HeaderTitle { font-size: 38px; font-weight: 700; color: #b45309; }
        QLabel#HeaderVersion { font-size: 14px; color: #6b7280; }
        QLabel#SubTitle { font-size: 22px; font-weight: 700; color: #b45309; }
        QLabel#StatusLine { font-size: 13px; color: #6b7280; }

        QCheckBox { spacing: 10px; font-size: 13px; }
        QCheckBox::indicator { width: 16px; height: 16px; }

        QPushButton#ThemeToggle {
            background: #ffa500; color: #1f2937; border: none;
            padding: 10px 18px; border-radius: 18px; font-weight: 600;
        }
        QPushButton#ThemeToggle:hover { background: #e69500; }

        QPushButton#LicenceButton {
            background: #ffa500; color: #1f2937; border: none;
            padding: 10px 18px; border-radius: 18px; font-weight: 600;
        }
        QPushButton#LicenceButton:hover { background: #e69500; }

        QPushButton#PrimaryAction {
            background: #ffa500; color: #1f2937; border: none;
            padding: 14px 26px; border-radius: 26px; font-size: 14px;
            font-weight: 700; min-width: 150px;
        }
        QPushButton#PrimaryAction:hover { background: #e69500; }

        QPushButton#DangerAction {
            background: #7a1f25; color: white; border: none;
            padding: 12px 26px; border-radius: 22px; font-size: 13px;
            font-weight: 700; min-width: 190px;
        }
        QPushButton#DangerAction:hover { background: #6a1b21; }

        QLineEdit {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 8px;
        }
        QPushButton#BrowseButton {
            background: #e5e7eb;
            border: none;
            border-radius: 10px;
            padding: 8px 12px;
        }
        QPushButton#BrowseButton:hover { background: #dbe0e8; }

        QProgressBar#ProgressBar {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            height: 16px;
            text-align: center;
        }
        QProgressBar#ProgressBar::chunk {
            background: #0096ff;
            border-radius: 8px;
            width: 10px;
            margin: 1px;
        }
    """,
)


DARK = Theme(
    name="dark",
    toggle_label="Light Theme",
    qss="""
        QWidget { background: #0e1020; color: #e5e7eb; font-family: 'Segoe UI'; }
        QLabel#HeaderTitle { font-size: 38px; font-weight: 700; color: #ffd700; }
        QLabel#HeaderVersion { font-size: 14px; color: #9ca3af; }
        QLabel#SubTitle { font-size: 22px; font-weight: 700; color: #ffd700; }
        QLabel#StatusLine { font-size: 13px; color: #cbd5e1; }

        QCheckBox { spacing: 10px; font-size: 13px; }
        QCheckBox::indicator { width: 16px; height: 16px; }

        QPushButton#ThemeToggle {
            background: #ffa500; color: #1f2937; border: none;
            padding: 10px 18px; border-radius: 18px; font-weight: 600;
        }
        QPushButton#ThemeToggle:hover { background: #e69500; }

        QPushButton#LicenceButton {
            background: #ffa500; color: #1f2937; border: none;
            padding: 10px 18px; border-radius: 18px; font-weight: 600;
        }
        QPushButton#LicenceButton:hover { background: #e69500; }

        QPushButton#PrimaryAction {
            background: #ffa500; color: #1f2937; border: none;
            padding: 14px 26px; border-radius: 26px; font-size: 14px;
            font-weight: 700; min-width: 150px;
        }
        QPushButton#PrimaryAction:hover { background: #e69500; }

        QPushButton#DangerAction {
            background: #7a1f25; color: white; border: none;
            padding: 12px 26px; border-radius: 22px; font-size: 13px;
            font-weight: 700; min-width: 190px;
        }
        QPushButton#DangerAction:hover { background: #6a1b21; }

        QLineEdit {
            background: #0a0c18;
            border: 1px solid #2b2f44;
            border-radius: 10px;
            padding: 8px;
        }
        QPushButton#BrowseButton {
            background: #1d2136;
            border: none;
            border-radius: 10px;
            padding: 8px 12px;
            color: #e5e7eb;
        }
        QPushButton#BrowseButton:hover { background: #262b4a; }

        QProgressBar#ProgressBar {
            background: #0a0c18;
            border: 1px solid #2b2f44;
            border-radius: 10px;
            height: 16px;
            text-align: center;
        }
        QProgressBar#ProgressBar::chunk {
            background: #0096ff;
            border-radius: 8px;
            width: 10px;
            margin: 1px;
        }
    """,
)
