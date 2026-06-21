import os
import sys
import json
import random
import datetime
import winreg
import winsound
import ctypes

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QSystemTrayIcon, QMenu, QDialog, QFormLayout, QSpinBox, QCheckBox,
    QTabWidget, QGridLayout, QFrame, QSizePolicy
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QIcon, QPixmap, QPainterPath, QLinearGradient, QAction
)
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QSize, QPoint, QSettings
)

# ---------------------------------------------------------
# 1. SETTINGS & STATISTICS MANAGER
# ---------------------------------------------------------
class SettingsManager:
    """Manages application configurations and statistics using QSettings."""
    def __init__(self):
        self.settings = QSettings("EyecareApp", "Settings")
        self.init_defaults()
        self.check_day_reset()

    def init_defaults(self):
        if not self.settings.contains("interval_mins"):
            self.settings.setValue("interval_mins", 20)
        if not self.settings.contains("duration_secs"):
            self.settings.setValue("duration_secs", 20)
        if not self.settings.contains("sound_enabled"):
            self.settings.setValue("sound_enabled", True)
        if not self.settings.contains("breaks_completed"):
            self.settings.setValue("breaks_completed", 0)
        if not self.settings.contains("last_date"):
            self.settings.setValue("last_date", datetime.date.today().isoformat())

    def get_interval(self):
        return int(self.settings.value("interval_mins", 20))

    def set_interval(self, mins):
        self.settings.setValue("interval_mins", mins)

    def get_duration(self):
        return int(self.settings.value("duration_secs", 20))

    def set_duration(self, secs):
        self.settings.setValue("duration_secs", secs)

    def get_sound_enabled(self):
        # QSettings might return string "true"/"false" or boolean
        val = self.settings.value("sound_enabled", True)
        if isinstance(val, str):
            return val.lower() == 'true'
        return bool(val)

    def set_sound_enabled(self, enabled):
        self.settings.setValue("sound_enabled", enabled)

    def get_breaks_completed(self):
        return int(self.settings.value("breaks_completed", 0))

    def increment_breaks(self):
        self.check_day_reset()
        current = self.get_breaks_completed()
        self.settings.setValue("breaks_completed", current + 1)

    def reset_breaks(self):
        self.settings.setValue("breaks_completed", 0)

    def check_day_reset(self):
        last_date_str = self.settings.value("last_date", datetime.date.today().isoformat())
        try:
            last_date = datetime.date.fromisoformat(last_date_str)
        except ValueError:
            last_date = datetime.date.today()
        
        if last_date != datetime.date.today():
            self.settings.setValue("breaks_completed", 0)
            self.settings.setValue("last_date", datetime.date.today().isoformat())

    def is_startup_enabled(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "EyecareReminder"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, key_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def set_startup(self, enabled):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_name = "EyecareReminder"
        script_path = os.path.abspath(sys.argv[0])
        # Use pythonw.exe to run without terminal window popping up
        pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
        cmd = f'"{pythonw_exe}" "{script_path}"'
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, key_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Failed to write to registry: {e}")
            return False

# ---------------------------------------------------------
# 2. DYNAMIC TRAY ICON GENERATOR
# ---------------------------------------------------------
class TrayIconGenerator:
    """Generates modern vector-like tray icons programmatically."""
    @staticmethod
    def create_icon(state="active"):
        # Create standard icon sizes (32x32)
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Determine colors based on state
        if state == "active":
            accent_color = QColor(45, 212, 191)  # Teal (#2dd4bf)
            bg_color = QColor(15, 23, 42)       # Dark slate (#0f172a)
            pupil_color = QColor(255, 255, 255)
        elif state == "paused":
            accent_color = QColor(148, 163, 184) # Muted Slate Gray (#94a3b8)
            bg_color = QColor(30, 41, 59)       # Grayer background
            pupil_color = QColor(148, 163, 184)
        else:  # break
            accent_color = QColor(59, 130, 246)  # Blue (#3b82f6)
            bg_color = QColor(15, 23, 42)       # Dark slate
            pupil_color = QColor(255, 255, 255)

        # Draw circular background
        painter.setBrush(bg_color)
        painter.setPen(QPen(accent_color, 2))
        painter.drawEllipse(2, 2, size - 4, size - 4)

        # Draw eye path
        path = QPainterPath()
        # Eye width from x=7 to x=25, height centered at y=16
        # quadTo(controlX, controlY, endX, endY)
        path.moveTo(7, 16)
        path.quadTo(16, 7, 25, 16)  # Upper eyelid
        path.quadTo(16, 25, 7, 16)  # Lower eyelid
        
        painter.setPen(QPen(accent_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Draw Iris / Pupil
        painter.setBrush(accent_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(13, 13, 6, 6)

        # Pupil white reflection
        painter.setBrush(pupil_color)
        painter.drawEllipse(15, 14, 2, 2)

        painter.end()
        return QIcon(pixmap)

# ---------------------------------------------------------
# 3. CIRCULAR PROGRESS BAR
# ---------------------------------------------------------
class CircularProgressBar(QWidget):
    """Custom painted circular countdown timer widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 20.0
        self.max_value = 20.0
        self.setMinimumSize(160, 160)
        self.setMaximumSize(160, 160)

    def set_progress(self, current, maximum):
        self.value = float(current)
        self.max_value = float(maximum)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        thickness = 10
        margin = 12

        rect = QRectF(margin, margin, width - 2 * margin, height - 2 * margin)

        # Draw background track
        bg_pen = QPen(QColor(51, 65, 85), thickness)  # Slate-600
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # Draw active progress arc
        if self.max_value > 0:
            angle = (self.value / self.max_value) * 360
        else:
            angle = 0

        progress_pen = QPen(QColor(45, 212, 191), thickness)  # Teal (#2dd4bf)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)
        # Start at 90 deg (top) and sweep clockwise (-angle)
        painter.drawArc(rect, 90 * 16, int(-angle * 16))

        # Draw center text (seconds remaining)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        text = f"{max(0, int(self.value))}"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.end()

# ---------------------------------------------------------
# 4. GLASSMORPHIC BREAK OVERLAY
# ---------------------------------------------------------
class BreakOverlay(QWidget):
    """Fullscreen translucent eye-break overlay."""
    def __init__(self, duration, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.duration = duration
        self.remaining = float(duration)
        
        # Eyecare tips to display at random
        self.tips = [
            "Look out the window at a distant object.",
            "Blink slowly 10 times to rehydrate your eyes.",
            "Roll your eyes slowly in a circle (both directions).",
            "Stretch your neck, shoulders, and back.",
            "Close your eyes and breathe deeply to relax.",
            "Focus on something far away, then look at your hands, and repeat.",
            "Gently rub your hands together to warm them, then cup over closed eyes."
        ]
        self.current_tip = random.choice(self.tips)

        # Set window properties for fullscreen overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.SubWindow | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Cover the entire screen workspace
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.init_ui()

        # Timer to tick every 100ms for smooth progress
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def init_ui(self):
        # Overall fullscreen background layout
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered glassmorphic card container
        self.card = QFrame(self)
        self.card.setObjectName("BreakCard")
        self.card.setFixedSize(500, 380)
        self.card.setStyleSheet("""
            QFrame#BreakCard {
                background-color: rgba(30, 41, 59, 0.95); /* Slate 800 with 95% opacity */
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 24px;
            }
            QLabel {
                font-family: "Segoe UI", system-ui;
                color: #f8fafc;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 24, 30, 24)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title_label = QLabel("20-20-20 Eye Break", self.card)
        title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)

        # Spacer
        card_layout.addSpacing(10)

        # Circular progress bar
        self.progress_circle = CircularProgressBar(self.card)
        self.progress_circle.set_progress(self.remaining, self.duration)
        
        progress_layout = QHBoxLayout()
        progress_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_circle)
        card_layout.addLayout(progress_layout)

        card_layout.addSpacing(10)

        # Tip header
        tip_header = QLabel("QUICK EXERCISE", self.card)
        tip_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        tip_header.setStyleSheet("color: #2dd4bf; letter-spacing: 1px;") # Teal
        tip_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(tip_header)

        # Calming tip text
        self.tip_label = QLabel(self.current_tip, self.card)
        self.tip_label.setFont(QFont("Segoe UI", 12))
        self.tip_label.setStyleSheet("color: #cbd5e1;")  # Slate-300
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip_label.setWordWrap(True)
        self.tip_label.setMinimumHeight(50)
        card_layout.addWidget(self.tip_label)

        card_layout.addSpacing(15)

        # Control buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        self.snooze_btn = QPushButton("Snooze (5m)", self.card)
        self.snooze_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.snooze_btn.setFixedHeight(38)
        self.snooze_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; /* Blue-500 */
                border: none;
                border-radius: 10px;
                color: #ffffff;
                padding-left: 20px;
                padding-right: 20px;
            }
            QPushButton:hover {
                background-color: #2563eb; /* Blue-600 */
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        self.snooze_btn.clicked.connect(self.snooze_break)
        btn_layout.addWidget(self.snooze_btn)

        self.skip_btn = QPushButton("Skip Break", self.card)
        self.skip_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.skip_btn.setFixedHeight(38)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                color: #f1f5f9;
                padding-left: 20px;
                padding-right: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.skip_btn.clicked.connect(self.skip_break)
        btn_layout.addWidget(self.skip_btn)

        card_layout.addLayout(btn_layout)
        main_layout.addWidget(self.card)

    def paintEvent(self, event):
        # Draw translucent window backdrop (covering the whole screen)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 215)) # Slate 900 with ~84% opacity

    def start_break(self):
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.remaining = float(self.duration)
        self.progress_circle.set_progress(self.remaining, self.duration)
        self.current_tip = random.choice(self.tips)
        self.tip_label.setText(self.current_tip)
        self.timer.start(100) # Tick every 100ms for smooth progress bar

        # Play sound if enabled
        if self.parent_app.settings.get_sound_enabled():
            try:
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass

    def tick(self):
        self.remaining -= 0.1
        if self.remaining <= 0:
            self.complete_break()
        else:
            self.progress_circle.set_progress(self.remaining, self.duration)

    def complete_break(self):
        self.timer.stop()
        self.close()
        self.parent_app.break_finished(success=True)

        if self.parent_app.settings.get_sound_enabled():
            try:
                winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass

    def skip_break(self):
        self.timer.stop()
        self.close()
        self.parent_app.break_finished(success=False)

    def snooze_break(self):
        self.timer.stop()
        self.close()
        self.parent_app.snooze_activated()

    def keyPressEvent(self, event):
        # Standard safety escape
        if event.key() == Qt.Key.Key_Escape:
            self.skip_break()
        else:
            super().keyPressEvent(event)

# ---------------------------------------------------------
# 5. SETTINGS & STATISTICS WINDOW
# ---------------------------------------------------------
class SettingsWindow(QDialog):
    """Configuration and usage dashboard UI."""
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.settings = parent_app.settings

        self.setWindowTitle("Eyecare App Settings & Stats")
        self.setFixedSize(480, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.init_ui()
        self.load_values()

    def init_ui(self):
        # Beautiful dark styling
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a; /* slate 900 */
            }
            QTabWidget::pane {
                border: 1px solid #1e293b; /* slate 800 */
                background-color: #1e293b;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #0f172a;
                color: #94a3b8;
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-family: "Segoe UI";
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #1e293b;
                color: #f8fafc;
                border-bottom: 2px solid #2dd4bf; /* Teal */
            }
            QLabel {
                font-family: "Segoe UI";
                color: #e2e8f0;
                font-size: 13px;
            }
            QSpinBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 6px;
                min-width: 60px;
            }
            QSpinBox:focus {
                border: 1px solid #2dd4bf;
            }
            QCheckBox {
                color: #e2e8f0;
                font-family: "Segoe UI";
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #334155;
                border-radius: 4px;
                background-color: #0f172a;
            }
            QCheckBox::indicator:checked {
                background-color: #2dd4bf;
                border: 1px solid #2dd4bf;
                image: url(data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>);
            }
            QPushButton {
                background-color: #2dd4bf; /* Teal */
                color: #0f172a;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-family: "Segoe UI";
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #14b8a6;
            }
            QPushButton#secondaryBtn {
                background-color: transparent;
                border: 1px solid #475569;
                color: #cbd5e1;
            }
            QPushButton#secondaryBtn:hover {
                background-color: rgba(255,255,255,0.05);
                border-color: #64748b;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        header_lbl = QLabel("Eyecare Dashboard", self)
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet("color: #f8fafc;")
        layout.addWidget(header_lbl)
        
        layout.addSpacing(8)

        # Tab Widget
        self.tabs = QTabWidget(self)
        
        # Tab 1: Settings
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Interval Spinbox
        self.interval_spin = QSpinBox(self)
        self.interval_spin.setRange(1, 180)
        self.interval_spin.setSuffix(" mins")
        form.addRow("Work Interval:", self.interval_spin)

        # Duration Spinbox
        self.duration_spin = QSpinBox(self)
        self.duration_spin.setRange(5, 300)
        self.duration_spin.setSuffix(" secs")
        form.addRow("Break Duration:", self.duration_spin)
        
        settings_layout.addLayout(form)

        # Audio and Startup Options
        options_layout = QVBoxLayout()
        options_layout.setSpacing(10)
        
        self.sound_check = QCheckBox("Enable Sound Alerts", self)
        options_layout.addWidget(self.sound_check)

        self.startup_check = QCheckBox("Launch at Windows Startup", self)
        options_layout.addWidget(self.startup_check)

        settings_layout.addLayout(options_layout)
        settings_layout.addStretch()

        # Tab 2: Statistics
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)
        stats_layout.setContentsMargins(20, 20, 20, 20)
        stats_layout.setSpacing(16)

        # Grid dashboard
        grid = QGridLayout()
        grid.setSpacing(16)

        # Stat Card 1: Completed
        card_completed = QFrame(self)
        card_completed.setStyleSheet("background-color: #0f172a; border-radius: 8px; border: 1px solid #334155;")
        cc_layout = QVBoxLayout(card_completed)
        cc_layout.setContentsMargins(12, 12, 12, 12)
        cc_title = QLabel("BREAKS COMPLETED TODAY", card_completed)
        cc_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        cc_title.setStyleSheet("color: #64748b;")
        self.cc_val = QLabel("0", card_completed)
        self.cc_val.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.cc_val.setStyleSheet("color: #2dd4bf;") # Teal
        cc_layout.addWidget(cc_title)
        cc_layout.addWidget(self.cc_val)
        grid.addWidget(card_completed, 0, 0)

        # Stat Card 2: Time Relaxed
        card_time = QFrame(self)
        card_time.setStyleSheet("background-color: #0f172a; border-radius: 8px; border: 1px solid #334155;")
        ct_layout = QVBoxLayout(card_time)
        ct_layout.setContentsMargins(12, 12, 12, 12)
        ct_title = QLabel("TOTAL EYES RESTED TIME", card_time)
        ct_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        ct_title.setStyleSheet("color: #64748b;")
        self.ct_val = QLabel("0s", card_time)
        self.ct_val.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.ct_val.setStyleSheet("color: #3b82f6;") # Blue
        ct_layout.addWidget(ct_title)
        ct_layout.addWidget(self.ct_val)
        grid.addWidget(card_time, 0, 1)

        stats_layout.addLayout(grid)

        # Reset button
        self.reset_btn = QPushButton("Reset Daily Count", self)
        self.reset_btn.setObjectName("secondaryBtn")
        self.reset_btn.clicked.connect(self.reset_stats)
        
        btn_center = QHBoxLayout()
        btn_center.addWidget(self.reset_btn)
        btn_center.addStretch()
        stats_layout.addLayout(btn_center)
        stats_layout.addStretch()

        self.tabs.addTab(self.settings_tab, "Reminder Options")
        self.tabs.addTab(self.stats_tab, "My Statistics")
        
        layout.addWidget(self.tabs)
        layout.addSpacing(12)

        # Lower buttons
        bottom_btns = QHBoxLayout()
        bottom_btns.addStretch()
        
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.clicked.connect(self.reject)
        bottom_btns.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save & Apply", self)
        self.save_btn.clicked.connect(self.save_values)
        bottom_btns.addWidget(self.save_btn)

        layout.addLayout(bottom_btns)

    def load_values(self):
        self.interval_spin.setValue(self.settings.get_interval())
        self.duration_spin.setValue(self.settings.get_duration())
        self.sound_check.setChecked(self.settings.get_sound_enabled())
        self.startup_check.setChecked(self.settings.is_startup_enabled())
        
        self.update_stats_display()

    def update_stats_display(self):
        breaks = self.settings.get_breaks_completed()
        duration_per_break = self.settings.get_duration()
        total_seconds = breaks * duration_per_break
        
        self.cc_val.setText(str(breaks))
        
        if total_seconds < 60:
            self.ct_val.setText(f"{total_seconds}s")
        else:
            self.ct_val.setText(f"{total_seconds // 60}m {total_seconds % 60}s")

    def save_values(self):
        self.settings.set_interval(self.interval_spin.value())
        self.settings.set_duration(self.duration_spin.value())
        self.settings.set_sound_enabled(self.sound_check.isChecked())
        
        # Registry update
        self.settings.set_startup(self.startup_check.isChecked())
        
        self.parent_app.apply_new_settings()
        self.accept()

    def reset_stats(self):
        self.settings.reset_breaks()
        self.update_stats_display()

# ---------------------------------------------------------
# 6. MAIN SYSTEM TRAY CONTROLLER
# ---------------------------------------------------------
class EyecareApp:
    """Core application coordinator managing timers, system tray, and notifications."""
    def __init__(self):
        self.settings = SettingsManager()

        # Timer states
        self.is_monitoring = True
        self.seconds_remaining = self.settings.get_interval() * 60

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        self.update_tray_icon("active")
        
        # Build tray context menu
        self.menu = QMenu()
        self.setup_menu()
        self.tray_icon.setContextMenu(self.menu)

        # Trigger tray clicks
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # Main background countdown timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.timer_tick)
        
        # Show tray icon
        self.tray_icon.show()

        # Settings Dashboard instance (lazy loaded)
        self.settings_window = None

        # Break Overlay instance
        self.break_overlay = None

        # Display welcoming notification on first run
        self.show_welcome_notification()

        # Start countdown
        self.start_monitoring()

    def setup_menu(self):
        # Slate/Dark menu stylesheet
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b; /* Slate 800 */
                border: 1px solid #334155;
                color: #f1f5f9;
                font-family: "Segoe UI";
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2dd4bf; /* Teal */
                color: #0f172a;
            }
            QMenu::separator {
                height: 1px;
                background-color: #334155;
                margin: 4px 0px;
            }
            QMenu::item:disabled {
                color: #64748b;
            }
        """)

        # Add items
        self.status_action = QAction("Time remaining: --:--", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        self.trigger_action = QAction("Start Eye Break Now", self.menu)
        self.trigger_action.triggered.connect(self.trigger_break_manually)
        self.menu.addAction(self.trigger_action)

        self.pause_action = QAction("Pause Reminders", self.menu)
        self.pause_action.triggered.connect(self.toggle_pause)
        self.menu.addAction(self.pause_action)

        self.menu.addSeparator()

        self.settings_action = QAction("Settings & Statistics...", self.menu)
        self.settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        self.exit_action = QAction("Exit Application", self.menu)
        self.exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(self.exit_action)

    def update_tray_icon(self, state):
        icon = TrayIconGenerator.create_icon(state)
        self.tray_icon.setIcon(icon)

    def start_monitoring(self):
        self.is_monitoring = True
        self.update_tray_icon("active")
        self.pause_action.setText("Pause Reminders")
        self.timer.start(1000)  # Tick every 1 second
        self.update_tooltip()

    def pause_monitoring(self):
        self.is_monitoring = False
        self.update_tray_icon("paused")
        self.pause_action.setText("Resume Reminders")
        self.timer.stop()
        self.status_action.setText("Reminders Paused")
        self.tray_icon.setToolTip("Eyecare - Reminders Paused")

    def toggle_pause(self):
        if self.is_monitoring:
            self.pause_monitoring()
        else:
            self.start_monitoring()

    def apply_new_settings(self):
        # Recalculate remaining seconds
        self.seconds_remaining = self.settings.get_interval() * 60
        self.update_tooltip()
        if not self.is_monitoring:
            self.start_monitoring()

    def update_tooltip(self):
        mins = self.seconds_remaining // 60
        secs = self.seconds_remaining % 60
        time_str = f"{mins:02d}:{secs:02d}"
        
        self.status_action.setText(f"Next break in: {time_str}")
        self.tray_icon.setToolTip(f"Eyecare - {time_str} until eye break")

    def timer_tick(self):
        # Pause the timer if screen is locked
        if self._is_screen_locked():
            return

        if self.seconds_remaining > 0:
            self.seconds_remaining -= 1
            self.update_tooltip()
        else:
            # Postpone break if in a meeting
            if self._is_in_meeting():
                self.seconds_remaining = 300  # Postpone by 5 minutes
                self.tray_icon.setToolTip("Eyecare - Postponed (Meeting Active)")
                self.status_action.setText("Break postponed (meeting active)")
            else:
                self.trigger_break()

    def _is_screen_locked(self):
        try:
            h_desktop = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
            if h_desktop:
                ctypes.windll.user32.CloseDesktop(h_desktop)
                return False
            return True
        except Exception:
            return False

    def _is_in_meeting(self):
        meeting_keywords = [
            "zoom meeting", "zoom webinar", 
            "microsoft teams meeting", "meeting in | microsoft teams", "meeting | microsoft teams",
            "- google meet", "meet - ",
            "webex meeting", "cisco webex"
        ]
        try:
            titles = self._get_window_titles()
            for title in titles:
                title_lower = title.lower()
                for kw in meeting_keywords:
                    if kw in title_lower:
                        return True
        except Exception:
            pass
        return False

    def _get_window_titles(self):
        titles = []
        try:
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible

            def foreach_window(hwnd, lParam):
                if IsWindowVisible(hwnd):
                    length = GetWindowTextLength(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(hwnd, buff, length + 1)
                        titles.append(buff.value)
                return True

            EnumWindows(EnumWindowsProc(foreach_window), 0)
        except Exception:
            pass
        return titles

    def trigger_break(self):
        self.timer.stop()
        self.update_tray_icon("break")
        
        # Open Overlay
        self.break_overlay = BreakOverlay(self.settings.get_duration(), self)
        self.break_overlay.start_break()

    def trigger_break_manually(self):
        self.trigger_break()

    def break_finished(self, success=True):
        self.break_overlay = None
        
        if success:
            self.settings.increment_breaks()
            # If dashboard is currently open, refresh stats
            if self.settings_window and self.settings_window.isVisible():
                self.settings_window.update_stats_display()

        # Reset timer and resume active state
        self.seconds_remaining = self.settings.get_interval() * 60
        self.start_monitoring()

    def snooze_activated(self):
        self.break_overlay = None
        # Snooze sets timer to 5 minutes (300 seconds)
        self.seconds_remaining = 300
        self.start_monitoring()

    def open_settings(self):
        # Create dialog if not existing, or update values
        if not self.settings_window:
            self.settings_window = SettingsWindow(self)
        else:
            self.settings_window.load_values()
        
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def tray_icon_activated(self, reason):
        # Open dashboard on double click
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()

    def show_welcome_notification(self):
        self.tray_icon.showMessage(
            "Eyecare App Running",
            f"Reminding you every {self.settings.get_interval()} mins to look 20 feet away for {self.settings.get_duration()} secs.",
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

    def exit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

# ---------------------------------------------------------
# 7. APPLICATION ENTRY POINT
# ---------------------------------------------------------
def main():
    # Fix High DPI Scaling issues on modern Windows monitors
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Initialize the main tray app controller
    tray_controller = EyecareApp()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
