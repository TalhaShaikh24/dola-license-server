import os
import cv2
import numpy as np
import datetime
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush, QIcon, QDragEnterEvent,
    QDropEvent, QFont, QCursor
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSlider, QComboBox, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QTabWidget, QGroupBox, QSplitter, QDialog,
    QCheckBox, QStackedWidget, QFrame, QSizePolicy, QScrollArea
)
from remover import WatermarkRemoverWorker, get_video_preview_frame, create_mask_for_frame
from video_combiner import VideoCombinerWorker, get_media_properties, format_duration, format_file_size
from combiner_widgets import (
    VideoGalleryCard, VideoGalleryWidget, VideoPlayerDialog, MergeSuccessDialog, CircularOrderBadge
)
from licensing.license_client import license_client
from licensing.auth_dialog import AuthDialog
from licensing.svg_icons import get_svg_icon, get_svg_pixmap

# =========================================================================
#  FLAWLESS ULTRA-PREMIUM THEMES (ZERO WHITE GLITCHES, PIXEL PERFECT)
# =========================================================================

DARK_THEME = """
QMainWindow {
    background-color: #0b0f19;
}
QWidget {
    background-color: transparent;
    color: #f1f5f9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}
QWidget#customTitleBar {
    background-color: #0d1322;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
QWidget#mainSidebar {
    background-color: #111827;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
QFrame#canvasContainer {
    background-color: #060911;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
}
QFrame#hudCard {
    background-color: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
}
QFrame#dropCard {
    background-color: rgba(255, 255, 255, 0.02);
    border: 1px dashed rgba(99, 102, 241, 0.35);
    border-radius: 8px;
}
QFrame#dropCard:hover {
    border-color: #6366f1;
    background-color: rgba(99, 102, 241, 0.05);
}

/* Mode Tab Buttons */
QPushButton.mode-tab-btn {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #94a3b8;
}
QPushButton.mode-tab-btn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
}
QPushButton.mode-tab-btn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    border: 1px solid #818cf8;
    color: #ffffff;
    font-weight: 700;
}

/* Action Buttons */
QPushButton.btn-primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton.btn-primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
}
QPushButton.btn-primary:disabled {
    background: #1e293b;
    color: #475569;
}

QPushButton.btn-combine {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8b5cf6, stop:1 #ec4899);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton.btn-combine:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c3aed, stop:1 #db2777);
}
QPushButton.btn-combine:disabled {
    background: #1e293b;
    color: #475569;
}

QPushButton.btn-subtle {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 6px 12px;
    color: #cbd5e1;
    font-weight: 600;
}
QPushButton.btn-subtle:hover {
    background-color: rgba(255, 255, 255, 0.09);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.2);
}

QPushButton.btn-danger {
    background-color: #e11d48;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton.btn-danger:hover {
    background-color: #be123c;
}

/* Window Buttons */
QPushButton#titleBarBtnMin, QPushButton#titleBarBtnMax, QPushButton#titleBarBtnClose {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #94a3b8;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#titleBarBtnMin:hover, QPushButton#titleBarBtnMax:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
}
QPushButton#titleBarBtnClose:hover {
    background-color: #e11d48;
    color: #ffffff;
}

/* Settings Box */
QGroupBox {
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #818cf8;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    background-color: rgba(15, 23, 42, 0.4);
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 8px;
    background-color: transparent;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #818cf8);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #6366f1;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #e0e7ff;
}

/* Combos */
QComboBox {
    background-color: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 6px 10px;
    color: #f1f5f9;
}
QComboBox:hover {
    border-color: #6366f1;
}
QComboBox QAbstractItemView {
    background-color: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.15);
    selection-background-color: #6366f1;
    selection-color: #ffffff;
    color: #f1f5f9;
}

/* Progress Bar */
QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 4px;
    height: 7px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a855f7);
    border-radius: 4px;
}

/* Console Logs */
QTextEdit {
    background-color: #060911;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    color: #94a3b8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 6px;
}

/* Checkbox */
QCheckBox {
    font-size: 12px;
    color: #f87171;
    font-weight: 600;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #f87171;
    background: transparent;
}
QCheckBox::indicator:checked {
    background-color: #e11d48;
}
"""

LIGHT_THEME = """
QMainWindow {
    background-color: #f1f5f9;
}
QWidget {
    background-color: transparent;
    color: #0f172a;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}
QWidget#customTitleBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QWidget#mainSidebar {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
QFrame#canvasContainer {
    background-color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QFrame#hudCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QFrame#dropCard {
    background-color: #f8fafc;
    border: 1px dashed #6366f1;
    border-radius: 8px;
}
QFrame#dropCard:hover {
    border-color: #4f46e5;
    background-color: #eef2ff;
}

/* Mode Tab Buttons */
QPushButton.mode-tab-btn {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #64748b;
}
QPushButton.mode-tab-btn:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}
QPushButton.mode-tab-btn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    border: 1px solid #4f46e5;
    color: #ffffff;
    font-weight: 700;
}

/* Action Buttons */
QPushButton.btn-primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton.btn-primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #4338ca);
}
QPushButton.btn-primary:disabled {
    background: #cbd5e1;
    color: #94a3b8;
}

QPushButton.btn-combine {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8b5cf6, stop:1 #ec4899);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton.btn-combine:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c3aed, stop:1 #db2777);
}
QPushButton.btn-combine:disabled {
    background: #cbd5e1;
    color: #94a3b8;
}

QPushButton.btn-subtle {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    color: #334155;
    font-weight: 600;
}
QPushButton.btn-subtle:hover {
    background-color: #f1f5f9;
    color: #0f172a;
    border-color: #94a3b8;
}

QPushButton.btn-danger {
    background-color: #e11d48;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton.btn-danger:hover {
    background-color: #be123c;
}

/* Window Buttons */
QPushButton#titleBarBtnMin, QPushButton#titleBarBtnMax, QPushButton#titleBarBtnClose {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #64748b;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#titleBarBtnMin:hover, QPushButton#titleBarBtnMax:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}
QPushButton#titleBarBtnClose:hover {
    background-color: #e11d48;
    color: #ffffff;
}

/* Settings Box */
QGroupBox {
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #4f46e5;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 8px;
    background-color: transparent;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #e2e8f0;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #818cf8);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #6366f1;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

/* Combos */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0f172a;
}
QComboBox:hover {
    border-color: #6366f1;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
    color: #0f172a;
}

/* Progress Bar */
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 4px;
    height: 7px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a855f7);
    border-radius: 4px;
}

/* Console Logs */
QTextEdit {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    color: #334155;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 6px;
}

/* Checkbox */
QCheckBox {
    font-size: 12px;
    color: #dc2626;
    font-weight: 600;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #dc2626;
    background: transparent;
}
QCheckBox::indicator:checked {
    background-color: #dc2626;
}
"""

class ROISelectionCanvas(QWidget):
    """Interactive canvas widget to render video preview frames and allow drag/resize ROI."""
    roi_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.pixmap = None
        
        self.roi_rect = {"x": 0, "y": 0, "width": 0, "height": 0, "ref_width": 100, "ref_height": 100}
        self.raw_image_width = 100
        self.raw_image_height = 100
        
        self.active_handle = None
        self.drag_start = QPoint()
        self.drag_rect_start = QRect()
        self.handle_size = 10
        
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
    def set_frame(self, frame_rgb):
        if frame_rgb is None:
            return
            
        self.image = frame_rgb
        h, w, c = frame_rgb.shape
        self.raw_image_width = w
        self.raw_image_height = h
        
        bytes_per_line = c * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.pixmap = QPixmap.fromImage(q_img)
        
        if self.roi_rect["width"] == 0 or self.roi_rect["height"] == 0 or \
           self.roi_rect["ref_width"] != w or self.roi_rect["ref_height"] != h:
            
            bw = int(w * 0.18)
            bh = int(h * 0.06)
            bx = w - bw - int(w * 0.03)
            by = h - bh - int(h * 0.03)
            
            self.roi_rect = {
                "x": max(0, bx),
                "y": max(0, by),
                "width": max(10, bw),
                "height": max(10, bh),
                "ref_width": w,
                "ref_height": h
            }
            
        self.update()
        self.roi_changed.emit()
        
    def get_scaling_metrics(self):
        if self.pixmap is None or self.pixmap.isNull():
            return 1.0, 0, 0, 0, 0
            
        w_wid, h_wid = self.width(), self.height()
        w_img, h_img = self.pixmap.width(), self.pixmap.height()
        
        scale = min(w_wid / w_img, h_wid / h_img)
        w_scaled = int(w_img * scale)
        h_scaled = int(h_img * scale)
        
        x_offset = (w_wid - w_scaled) // 2
        y_offset = (h_wid - h_scaled) // 2
        
        return scale, x_offset, y_offset, w_scaled, h_scaled
        
    def get_handles_widget_rects(self, wx, wy, ww, wh):
        hs = self.handle_size
        hs_half = hs // 2
        return {
            'tl': QRect(wx - hs_half, wy - hs_half, hs, hs),
            'tr': QRect(wx + ww - hs_half, wy - hs_half, hs, hs),
            'bl': QRect(wx - hs_half, wy + wh - hs_half, hs, hs),
            'br': QRect(wx + ww - hs_half, wy + wh - hs_half, hs, hs)
        }
        
    def mousePressEvent(self, event):
        if self.pixmap is None:
            return
            
        pos = event.position()
        mx, my = pos.x(), pos.y()
        
        scale, x_off, y_off, _, _ = self.get_scaling_metrics()
        wx = int(self.roi_rect["x"] * scale) + x_off
        wy = int(self.roi_rect["y"] * scale) + y_off
        ww = int(self.roi_rect["width"] * scale)
        wh = int(self.roi_rect["height"] * scale)
        
        handles = self.get_handles_widget_rects(wx, wy, ww, wh)
        for handle_name, rect in handles.items():
            if rect.contains(int(mx), int(my)):
                self.active_handle = handle_name
                self.drag_start = QPoint(int(mx), int(my))
                self.drag_rect_start = QRect(wx, wy, ww, wh)
                return
                
        roi_box = QRect(wx, wy, ww, wh)
        if roi_box.contains(int(mx), int(my)):
            self.active_handle = 'move'
            self.drag_start = QPoint(int(mx), int(my))
            self.drag_rect_start = QRect(wx, wy, ww, wh)
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            return
            
        self.active_handle = 'draw'
        self.drag_start = QPoint(int(mx), int(my))
        
        ix = (mx - x_off) / scale
        iy = (my - y_off) / scale
        ix = max(0, min(int(ix), self.raw_image_width - 1))
        iy = max(0, min(int(iy), self.raw_image_height - 1))
        
        self.roi_rect = {
            "x": ix, "y": iy, "width": 1, "height": 1,
            "ref_width": self.raw_image_width, "ref_height": self.raw_image_height
        }
        self.update()
        
    def mouseMoveEvent(self, event):
        if self.pixmap is None:
            return
            
        pos = event.position()
        mx, my = pos.x(), pos.y()
        scale, x_off, y_off, _, _ = self.get_scaling_metrics()
        
        if self.active_handle is None:
            wx = int(self.roi_rect["x"] * scale) + x_off
            wy = int(self.roi_rect["y"] * scale) + y_off
            ww = int(self.roi_rect["width"] * scale)
            wh = int(self.roi_rect["height"] * scale)
            
            handles = self.get_handles_widget_rects(wx, wy, ww, wh)
            if handles['tl'].contains(int(mx), int(my)) or handles['br'].contains(int(mx), int(my)):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handles['tr'].contains(int(mx), int(my)) or handles['bl'].contains(int(mx), int(my)):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif QRect(wx, wy, ww, wh).contains(int(mx), int(my)):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            return
            
        dx = mx - self.drag_start.x()
        dy = my - self.drag_start.y()
        
        if self.active_handle == 'move':
            new_wx = self.drag_rect_start.x() + dx
            new_wy = self.drag_rect_start.y() + dy
            
            ix = (new_wx - x_off) / scale
            iy = (new_wy - y_off) / scale
            
            ix = max(0, min(int(ix), self.raw_image_width - self.roi_rect["width"]))
            iy = max(0, min(int(iy), self.raw_image_height - self.roi_rect["height"]))
            
            self.roi_rect["x"] = ix
            self.roi_rect["y"] = iy
            
        elif self.active_handle in ('tl', 'tr', 'bl', 'br'):
            r = self.drag_rect_start
            x1, y1, x2, y2 = r.left(), r.top(), r.right(), r.bottom()
            
            if self.active_handle == 'tl':
                x1 += dx; y1 += dy
            elif self.active_handle == 'tr':
                x2 += dx; y1 += dy
            elif self.active_handle == 'bl':
                x1 += dx; y2 += dy
            elif self.active_handle == 'br':
                x2 += dx; y2 += dy
                
            fx1, fx2 = min(x1, x2), max(x1, x2)
            fy1, fy2 = min(y1, y2), max(y1, y2)
            
            ix1 = max(0, min(int((fx1 - x_off) / scale), self.raw_image_width - 1))
            iy1 = max(0, min(int((fy1 - x_off) / scale), self.raw_image_height - 1))
            ix2 = max(0, min(int((fx2 - x_off) / scale), self.raw_image_width - 1))
            iy2 = max(0, min(int((fy2 - y_off) / scale), self.raw_image_height - 1))
            
            self.roi_rect["x"] = ix1
            self.roi_rect["y"] = iy1
            self.roi_rect["width"] = max(8, ix2 - ix1)
            self.roi_rect["height"] = max(8, iy2 - iy1)
            
        elif self.active_handle == 'draw':
            ix_start = (self.drag_start.x() - x_off) / scale
            iy_start = (self.drag_start.y() - y_off) / scale
            ix_cur = (mx - x_off) / scale
            iy_cur = (my - y_off) / scale
            
            x1, x2 = min(ix_start, ix_cur), max(ix_start, ix_cur)
            y1, y2 = min(iy_start, iy_cur), max(iy_start, iy_cur)
            
            self.roi_rect["x"] = max(0, min(int(x1), self.raw_image_width - 1))
            self.roi_rect["y"] = max(0, min(int(y1), self.raw_image_height - 1))
            self.roi_rect["width"] = max(6, min(int(x2 - x1), self.raw_image_width - self.roi_rect["x"]))
            self.roi_rect["height"] = max(6, min(int(y2 - y1), self.raw_image_height - self.roi_rect["y"]))
            
        self.update()
        self.roi_changed.emit()
        
    def mouseReleaseEvent(self, event):
        self.active_handle = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.pixmap is None or self.pixmap.isNull():
            painter.fillRect(self.rect(), QColor("#060911"))
            
            painter.setPen(QPen(QColor("rgba(99, 102, 241, 0.4)"), 1.5, Qt.PenStyle.DashLine))
            inner_rect = self.rect().adjusted(24, 24, -24, -24)
            painter.drawRoundedRect(inner_rect, 10, 10)
            
            painter.setPen(QColor("#f8fafc"))
            painter.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            painter.drawText(self.rect().adjusted(0, -25, 0, 0), Qt.AlignmentFlag.AlignCenter, "Video Frame Preview")
            
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect().adjusted(0, 25, 0, 0), Qt.AlignmentFlag.AlignCenter, "Drag & Drop video file here, or click Browse to load")
            
            painter.setFont(QFont("Segoe UI", 10))
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect().adjusted(0, 60, 0, 0), Qt.AlignmentFlag.AlignCenter, "Click and drag to adjust the watermark removal box")
            return
            
        scale, x_off, y_off, w_sc, h_sc = self.get_scaling_metrics()
        painter.drawPixmap(x_off, y_off, w_sc, h_sc, self.pixmap)
        
        # Draw ROI Box
        rx = int(self.roi_rect["x"] * scale) + x_off
        ry = int(self.roi_rect["y"] * scale) + y_off
        rw = int(self.roi_rect["width"] * scale)
        rh = int(self.roi_rect["height"] * scale)
        
        painter.fillRect(QRect(rx, ry, rw, rh), QColor(99, 102, 241, 60))
        
        pen = QPen(QColor("#6366f1"), 2)
        painter.setPen(pen)
        painter.drawRect(rx, ry, rw, rh)
        
        dim_str = f"{self.roi_rect['width']} × {self.roi_rect['height']} px"
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.fillRect(QRect(rx, max(0, ry - 20), 105, 18), QColor("#1e1b4b"))
        painter.setPen(QColor("#e0e7ff"))
        painter.drawText(QRect(rx + 6, max(0, ry - 18), 95, 14), Qt.AlignmentFlag.AlignLeft, dim_str)
        
        handles = self.get_handles_widget_rects(rx, ry, rw, rh)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#4f46e5"), 1.5))
        for rect in handles.values():
            painter.drawEllipse(rect)


class CustomTitleBar(QWidget):
    """Ultra-clean header with window controls, creator branding, and light/dark theme switch."""
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.parent_window = parent
        self.drag_position = None
        self.setFixedHeight(44)
        self.setObjectName("customTitleBar")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(10)

        # App Icon & Title
        png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        target_img = png_path if os.path.exists(png_path) else ico_path
        
        icon_lbl = QLabel()
        if os.path.exists(target_img):
            pix = QPixmap(target_img).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            pix.setDevicePixelRatio(2.0)
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setPixmap(get_svg_pixmap("sparkles", "#818cf8", 18))
        layout.addWidget(icon_lbl)

        title_lbl = QLabel("DOLA AI Watermark Remover & Video Combiner")
        title_lbl.setStyleSheet("font-weight: 800; font-size: 13px; letter-spacing: 0.3px;")
        layout.addWidget(title_lbl)

        # Creator Link
        credit_lbl = QLabel("&bull; Developed by <a href='https://talhashaikh.com' style='color:#818cf8; text-decoration:none; font-weight:bold;'>Talha Shaikh</a>")
        credit_lbl.setTextFormat(Qt.TextFormat.RichText)
        credit_lbl.setOpenExternalLinks(True)
        credit_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(credit_lbl)

        layout.addStretch()

        # Theme Toggle Button
        self.btn_theme = QPushButton("☀️ Light")
        self.btn_theme.setProperty("class", "btn-subtle")
        self.btn_theme.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self.btn_theme.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_theme.clicked.connect(self.parent_window.toggle_theme)
        layout.addWidget(self.btn_theme)

        # Account / License Pill
        self.btn_license_pill = QPushButton(self.parent_window._get_license_summary_text())
        self.btn_license_pill.setIcon(get_svg_icon("shield-check", "#10b981", 13))
        self.btn_license_pill.setProperty("class", "btn-subtle")
        self.btn_license_pill.setStyleSheet("font-size: 11px; padding: 4px 10px; color:#10b981; font-weight:700;")
        self.btn_license_pill.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_license_pill.clicked.connect(self.parent_window.open_account_dialog)
        layout.addWidget(self.btn_license_pill)

        # Window Controls
        self.btn_min = QPushButton("―")
        self.btn_min.setFixedSize(36, 30)
        self.btn_min.setObjectName("titleBarBtnMin")
        self.btn_min.setToolTip("Minimize")
        self.btn_min.clicked.connect(self.parent_window.showMinimized)

        self.btn_max = QPushButton("🗖")
        self.btn_max.setFixedSize(36, 30)
        self.btn_max.setObjectName("titleBarBtnMax")
        self.btn_max.setToolTip("Maximize / Restore")
        self.btn_max.clicked.connect(self._toggle_maximize)

        self.btn_close = QPushButton()
        self.btn_close.setIcon(get_svg_icon("close", "#94a3b8", 13))
        self.btn_close.setFixedSize(38, 30)
        self.btn_close.setObjectName("titleBarBtnClose")
        self.btn_close.setToolTip("Close Application")
        self.btn_close.clicked.connect(self.parent_window.close)

        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

    def _toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.btn_max.setText("🗖")
        else:
            self.parent_window.showMaximized()
            self.btn_max.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.btn_max.setText("🗖")
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            event.accept()


class MainWindow(QMainWindow):
    """
    Main Video Studio Application. Sleek single unified sidebar, pixel-perfect dark & light
    themes, live video preview with ROI, and high-performance video combiner.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dola AI Watermark Remover & Video Combiner — Talha Shaikh")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.resize(1200, 760)
        self.setAcceptDrops(True)
        
        self.current_theme = "dark"
        
        # State variables
        self.selected_single_video = ""
        self.selected_batch_folder = ""
        self.selected_batch_output = ""
        self.batch_video_files = []
        self.preview_frame_bgr = None
        self.preview_frame_rgb = None
        self.preview_video_info = None
        self.selected_combine_output_dir = ""
        
        # Workers
        self.worker = None
        self.combine_worker = None
        
        self.init_ui()
        self.apply_theme("dark")
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # 1. Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        root_layout.addWidget(self.title_bar)
        
        # 2. Main Body (Sidebar + Viewport)
        body_widget = QWidget()
        main_layout = QHBoxLayout(body_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        root_layout.addWidget(body_widget)
        
        # =====================================================================
        # SINGLE UNIFIED SIDEBAR (Width: 380px)
        # =====================================================================
        self.sidebar = QWidget()
        self.sidebar.setObjectName("mainSidebar")
        self.sidebar.setFixedWidth(380)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_layout.setSpacing(12)

        # Mode Selector Buttons (Single / Batch / Combine)
        h_modes = QHBoxLayout()
        h_modes.setSpacing(6)

        self.btn_mode_single = QPushButton("Single Video")
        self.btn_mode_single.setIcon(get_svg_icon("sparkles", "#818cf8", 14))
        self.btn_mode_single.setProperty("class", "mode-tab-btn")
        self.btn_mode_single.setCheckable(True)
        self.btn_mode_single.setChecked(True)
        self.btn_mode_single.clicked.connect(lambda: self.switch_mode(0))
        h_modes.addWidget(self.btn_mode_single)

        self.btn_mode_batch = QPushButton("Folder Batch")
        self.btn_mode_batch.setIcon(get_svg_icon("film", "#60a5fa", 14))
        self.btn_mode_batch.setProperty("class", "mode-tab-btn")
        self.btn_mode_batch.setCheckable(True)
        self.btn_mode_batch.clicked.connect(lambda: self.switch_mode(1))
        h_modes.addWidget(self.btn_mode_batch)

        self.btn_mode_combine = QPushButton("Combiner")
        self.btn_mode_combine.setIcon(get_svg_icon("film", "#f43f5e", 14))
        self.btn_mode_combine.setProperty("class", "mode-tab-btn")
        self.btn_mode_combine.setCheckable(True)
        self.btn_mode_combine.clicked.connect(lambda: self.switch_mode(2))
        h_modes.addWidget(self.btn_mode_combine)

        sidebar_layout.addLayout(h_modes)

        # Scrollable Configuration Controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 4, 4, 4)
        sc_layout.setSpacing(12)

        # --- Stacked Mode Inputs ---
        self.stacked_inputs = QStackedWidget()

        # Page 0: Single Video Inputs
        page_single = QWidget()
        p0_layout = QVBoxLayout(page_single)
        p0_layout.setContentsMargins(0, 0, 0, 0)
        p0_layout.setSpacing(8)

        lbl_s_title = QLabel("Select Input Video File:")
        lbl_s_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p0_layout.addWidget(lbl_s_title)

        drop_card_s = QFrame()
        drop_card_s.setObjectName("dropCard")
        dc_layout_s = QHBoxLayout(drop_card_s)
        dc_layout_s.setContentsMargins(10, 8, 10, 8)
        
        self.txt_single_file = QLabel("No video selected")
        self.txt_single_file.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.txt_single_file.setWordWrap(False)
        
        btn_browse_single = QPushButton("Browse")
        btn_browse_single.setProperty("class", "btn-subtle")
        btn_browse_single.clicked.connect(self.browse_single_file)
        
        dc_layout_s.addWidget(self.txt_single_file, 7)
        dc_layout_s.addWidget(btn_browse_single, 3)
        p0_layout.addWidget(drop_card_s)
        self.stacked_inputs.addWidget(page_single)

        # Page 1: Batch Folder Inputs
        page_batch = QWidget()
        p1_layout = QVBoxLayout(page_batch)
        p1_layout.setContentsMargins(0, 0, 0, 0)
        p1_layout.setSpacing(8)

        lbl_b_in = QLabel("Select Input Folder:")
        lbl_b_in.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p1_layout.addWidget(lbl_b_in)

        drop_card_b = QFrame()
        drop_card_b.setObjectName("dropCard")
        dc_layout_b = QHBoxLayout(drop_card_b)
        dc_layout_b.setContentsMargins(10, 8, 10, 8)
        
        self.txt_batch_in = QLabel("No folder selected")
        self.txt_batch_in.setStyleSheet("font-size: 11px; color: #94a3b8;")
        btn_b_in = QPushButton("Browse")
        btn_b_in.setProperty("class", "btn-subtle")
        btn_b_in.clicked.connect(self.browse_batch_in_folder)
        dc_layout_b.addWidget(self.txt_batch_in, 7)
        dc_layout_b.addWidget(btn_b_in, 3)
        p1_layout.addWidget(drop_card_b)

        lbl_b_out = QLabel("Output Destination Folder:")
        lbl_b_out.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p1_layout.addWidget(lbl_b_out)

        drop_card_bo = QFrame()
        drop_card_bo.setObjectName("dropCard")
        dc_layout_bo = QHBoxLayout(drop_card_bo)
        dc_layout_bo.setContentsMargins(10, 8, 10, 8)

        self.txt_batch_out = QLabel("no_watermarks/")
        self.txt_batch_out.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.btn_browse_batch_out = QPushButton("Browse")
        self.btn_browse_batch_out.setProperty("class", "btn-subtle")
        self.btn_browse_batch_out.clicked.connect(self.browse_batch_out_folder)
        dc_layout_bo.addWidget(self.txt_batch_out, 7)
        dc_layout_bo.addWidget(self.btn_browse_batch_out, 3)
        p1_layout.addWidget(drop_card_bo)

        self.lbl_batch_stats = QLabel("0 videos found.")
        self.lbl_batch_stats.setStyleSheet("color: #818cf8; font-size: 11px; font-weight: 600;")
        p1_layout.addWidget(self.lbl_batch_stats)
        self.stacked_inputs.addWidget(page_batch)

        # Page 2: Combine Mode Inputs
        page_comb = QWidget()
        p2_layout = QVBoxLayout(page_comb)
        p2_layout.setContentsMargins(0, 0, 0, 0)
        p2_layout.setSpacing(8)

        lbl_c_desc = QLabel("Merge Videos Gallery:")
        lbl_c_desc.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_c_desc.setStyleSheet("color: #ec4899;")
        p2_layout.addWidget(lbl_c_desc)

        lbl_c_info = QLabel("Select clips in the gallery, arrange order with circular numbered badges, and click combine.")
        lbl_c_info.setWordWrap(True)
        lbl_c_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        p2_layout.addWidget(lbl_c_info)

        lbl_c_out = QLabel("Combined Output Destination:")
        lbl_c_out.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p2_layout.addWidget(lbl_c_out)

        drop_card_c = QFrame()
        drop_card_c.setObjectName("dropCard")
        dc_layout_c = QHBoxLayout(drop_card_c)
        dc_layout_c.setContentsMargins(10, 8, 10, 8)

        self.txt_combine_out = QLabel("Default Destination")
        self.txt_combine_out.setStyleSheet("font-size: 11px; color: #94a3b8;")
        btn_c_out = QPushButton("Browse")
        btn_c_out.setProperty("class", "btn-subtle")
        btn_c_out.clicked.connect(self.browse_combine_out_folder)
        dc_layout_c.addWidget(self.txt_combine_out, 7)
        dc_layout_c.addWidget(btn_c_out, 3)
        p2_layout.addWidget(drop_card_c)
        self.stacked_inputs.addWidget(page_comb)

        sc_layout.addWidget(self.stacked_inputs)

        # --- Watermark Settings Group (Visible in Single & Batch modes) ---
        self.grp_settings = QGroupBox("Removal Algorithm Configuration")
        settings_grid = QGridLayout(self.grp_settings)
        settings_grid.setSpacing(10)
        settings_grid.setContentsMargins(10, 16, 10, 12)

        settings_grid.addWidget(QLabel("Color Threshold:"), 0, 0)
        self.slider_thresh = QSlider(Qt.Orientation.Horizontal)
        self.slider_thresh.setRange(100, 255)
        self.slider_thresh.setValue(200)
        self.slider_thresh.valueChanged.connect(self.on_slider_thresh_changed)
        self.lbl_thresh_val = QLabel("200")
        self.lbl_thresh_val.setFixedWidth(28)
        self.lbl_thresh_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        h_thresh = QHBoxLayout()
        h_thresh.addWidget(self.slider_thresh)
        h_thresh.addWidget(self.lbl_thresh_val)
        settings_grid.addLayout(h_thresh, 0, 1)

        settings_grid.addWidget(QLabel("Dilation Size:"), 1, 0)
        self.slider_dilation = QSlider(Qt.Orientation.Horizontal)
        self.slider_dilation.setRange(0, 10)
        self.slider_dilation.setValue(2)
        self.slider_dilation.valueChanged.connect(self.on_slider_dilation_changed)
        self.lbl_dilation_val = QLabel("2")
        self.lbl_dilation_val.setFixedWidth(28)
        self.lbl_dilation_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        h_dil = QHBoxLayout()
        h_dil.addWidget(self.slider_dilation)
        h_dil.addWidget(self.lbl_dilation_val)
        settings_grid.addLayout(h_dil, 1, 1)

        settings_grid.addWidget(QLabel("Inpaint Radius:"), 2, 0)
        self.slider_radius = QSlider(Qt.Orientation.Horizontal)
        self.slider_radius.setRange(1, 15)
        self.slider_radius.setValue(3)
        self.slider_radius.valueChanged.connect(self.on_slider_radius_changed)
        self.lbl_radius_val = QLabel("3")
        self.lbl_radius_val.setFixedWidth(28)
        self.lbl_radius_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        h_rad = QHBoxLayout()
        h_rad.addWidget(self.slider_radius)
        h_rad.addWidget(self.lbl_radius_val)
        settings_grid.addLayout(h_rad, 2, 1)

        settings_grid.addWidget(QLabel("Masking Mode:"), 3, 0)
        self.combo_mask_mode = QComboBox()
        self.combo_mask_mode.addItems(["Static Text", "Dynamic Text", "Full Box"])
        self.combo_mask_mode.currentIndexChanged.connect(self.on_mask_mode_changed)
        settings_grid.addWidget(self.combo_mask_mode, 3, 1)

        settings_grid.addWidget(QLabel("Algorithm:"), 4, 0)
        self.combo_method = QComboBox()
        self.combo_method.addItems(["Telea", "Navier-Stokes"])
        settings_grid.addWidget(self.combo_method, 4, 1)

        settings_grid.addWidget(QLabel("CPU Threads:"), 5, 0)
        self.combo_threads = QComboBox()
        cores = os.cpu_count() or 4
        for i in range(1, cores + 1):
            self.combo_threads.addItem(str(i))
        self.combo_threads.setCurrentText(str(max(1, cores // 2)))
        settings_grid.addWidget(self.combo_threads, 5, 1)

        self.chk_overwrite = QCheckBox("Overwrite Original File(s)")
        self.chk_overwrite.toggled.connect(self.on_overwrite_toggled)
        settings_grid.addWidget(self.chk_overwrite, 6, 0, 1, 2)
        sc_layout.addWidget(self.grp_settings)

        # --- Video Combine Settings Group (Visible in Combine mode) ---
        self.grp_combine_settings = QGroupBox("Transition & Merging")
        combine_grid = QGridLayout(self.grp_combine_settings)
        combine_grid.setSpacing(10)
        combine_grid.setContentsMargins(10, 16, 10, 12)

        combine_grid.addWidget(QLabel("Transition:"), 0, 0)
        self.combo_transition = QComboBox()
        self.combo_transition.addItems([
            "Smooth Fade", "Dissolve", "Fade to Black",
            "Wipe Left", "Wipe Right", "Smooth Slide"
        ])
        combine_grid.addWidget(self.combo_transition, 0, 1)

        combine_grid.addWidget(QLabel("Duration:"), 1, 0)
        self.slider_transition_dur = QSlider(Qt.Orientation.Horizontal)
        self.slider_transition_dur.setRange(2, 20)
        self.slider_transition_dur.setValue(8)
        self.slider_transition_dur.valueChanged.connect(self.on_transition_slider_changed)
        self.lbl_transition_val = QLabel("0.8s")
        self.lbl_transition_val.setFixedWidth(32)
        self.lbl_transition_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        h_tdur = QHBoxLayout()
        h_tdur.addWidget(self.slider_transition_dur)
        h_tdur.addWidget(self.lbl_transition_val)
        combine_grid.addLayout(h_tdur, 1, 1)

        combine_grid.addWidget(QLabel("Audio Crossfade:"), 2, 0)
        lbl_ax = QLabel("✓ Auto (Crossfaded)")
        lbl_ax.setStyleSheet("color: #10b981; font-weight: bold;")
        combine_grid.addWidget(lbl_ax, 2, 1)

        self.grp_combine_settings.setVisible(False)
        sc_layout.addWidget(self.grp_combine_settings)

        sc_layout.addStretch()
        scroll.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll)

        # Action Buttons
        self.btn_preview = QPushButton("Preview Removal Result")
        self.btn_preview.setIcon(get_svg_icon("sparkles", "#818cf8", 15))
        self.btn_preview.setProperty("class", "btn-subtle")
        self.btn_preview.clicked.connect(self.show_removal_preview)
        self.btn_preview.setEnabled(False)
        sidebar_layout.addWidget(self.btn_preview)

        self.btn_start = QPushButton("Start Watermark Removal")
        self.btn_start.setIcon(get_svg_icon("sparkles", "#ffffff", 16))
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_start.setEnabled(False)
        sidebar_layout.addWidget(self.btn_start)

        self.btn_combine = QPushButton("Merge Selected Videos")
        self.btn_combine.setIcon(get_svg_icon("film", "#ffffff", 16))
        self.btn_combine.setProperty("class", "btn-combine")
        self.btn_combine.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_combine.clicked.connect(self.start_combining)
        self.btn_combine.setVisible(False)
        sidebar_layout.addWidget(self.btn_combine)

        self.btn_cancel = QPushButton("Cancel Active Task")
        self.btn_cancel.setIcon(get_svg_icon("close", "#ffffff", 14))
        self.btn_cancel.setProperty("class", "btn-danger")
        self.btn_cancel.clicked.connect(self.cancel_processing)
        self.btn_cancel.setVisible(False)
        sidebar_layout.addWidget(self.btn_cancel)

        main_layout.addWidget(self.sidebar)

        # =====================================================================
        # RIGHT PANEL: VIEWPORT & PROGRESS HUD CARD
        # =====================================================================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Viewport Stack (Canvas & Gallery)
        canvas_card = QFrame()
        canvas_card.setObjectName("canvasContainer")
        canvas_card_layout = QVBoxLayout(canvas_card)
        canvas_card_layout.setContentsMargins(4, 4, 4, 4)

        self.stacked_view = QStackedWidget()
        self.canvas = ROISelectionCanvas()
        self.canvas.roi_changed.connect(self.on_roi_changed)
        self.stacked_view.addWidget(self.canvas)

        self.gallery_widget = VideoGalleryWidget()
        self.gallery_widget.order_changed.connect(self.update_action_states)
        self.gallery_widget.play_requested.connect(self.play_video_file)
        self.stacked_view.addWidget(self.gallery_widget)
        canvas_card_layout.addWidget(self.stacked_view)

        splitter.addWidget(canvas_card)

        # Modern Glass Progress HUD Card
        self.hud_card = QFrame()
        self.hud_card.setObjectName("hudCard")
        hud_layout = QVBoxLayout(self.hud_card)
        hud_layout.setContentsMargins(16, 14, 16, 14)
        hud_layout.setSpacing(8)

        # Top Row of HUD
        h_hud_top = QHBoxLayout()
        self.lbl_hud_status = QLabel("Ready")
        self.lbl_hud_status.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        self.lbl_hud_pct = QLabel("0%")
        self.lbl_hud_pct.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_hud_pct.setStyleSheet("color: #6366f1;")
        
        h_hud_top.addWidget(self.lbl_hud_status)
        h_hud_top.addStretch()
        h_hud_top.addWidget(self.lbl_hud_pct)
        hud_layout.addLayout(h_hud_top)

        # Progress Bars
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        hud_layout.addWidget(self.progress_bar)

        self.lbl_batch_progress = QLabel("Overall Batch Progress: 0%")
        self.lbl_batch_progress.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_batch_progress.setVisible(False)
        hud_layout.addWidget(self.lbl_batch_progress)

        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setValue(0)
        self.batch_progress_bar.setTextVisible(False)
        self.batch_progress_bar.setVisible(False)
        hud_layout.addWidget(self.batch_progress_bar)

        # Activity Logs Console
        h_log_header = QHBoxLayout()
        lbl_console_title = QLabel("PROCESSING LOGS")
        lbl_console_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #64748b; letter-spacing: 0.6px;")
        
        btn_clear_log = QPushButton("Clear")
        btn_clear_log.setProperty("class", "btn-subtle")
        btn_clear_log.setStyleSheet("padding: 2px 6px; font-size: 10px;")
        btn_clear_log.clicked.connect(lambda: self.txt_log.clear())
        
        h_log_header.addWidget(lbl_console_title)
        h_log_header.addStretch()
        h_log_header.addWidget(btn_clear_log)
        hud_layout.addLayout(h_log_header)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.append("Application initialized. Ready to process video.")
        self.txt_log.setFixedHeight(75)
        hud_layout.addWidget(self.txt_log)

        self.hud_card.setFixedHeight(210)
        splitter.addWidget(self.hud_card)

        right_layout.addWidget(splitter)
        main_layout.addWidget(right_panel)

    # --- Mode Switching (Single vs Batch vs Combine) ---
    def switch_mode(self, mode_idx: int):
        self.btn_mode_single.setChecked(mode_idx == 0)
        self.btn_mode_batch.setChecked(mode_idx == 1)
        self.btn_mode_combine.setChecked(mode_idx == 2)

        self.stacked_inputs.setCurrentIndex(mode_idx)
        self.stacked_view.setCurrentIndex(1 if mode_idx == 2 else 0)

        self.grp_settings.setVisible(mode_idx != 2)
        self.grp_combine_settings.setVisible(mode_idx == 2)

        self.btn_start.setVisible(mode_idx != 2)
        self.btn_combine.setVisible(mode_idx == 2)
        self.btn_preview.setVisible(mode_idx != 2)

        self.update_action_states()

    # --- Theme Switching (Dark / Light) ---
    def toggle_theme(self):
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_theme)

    def apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        if theme_name == "light":
            self.setStyleSheet(LIGHT_THEME)
            self.title_bar.btn_theme.setText("🌙 Dark")
        else:
            self.setStyleSheet(DARK_THEME)
            self.title_bar.btn_theme.setText("☀️ Light")

    # --- Sliders & Settings Handlers ---
    def on_slider_thresh_changed(self, val):
        self.lbl_thresh_val.setText(str(val))
        
    def on_slider_dilation_changed(self, val):
        self.lbl_dilation_val.setText(str(val))
        
    def on_slider_radius_changed(self, val):
        self.lbl_radius_val.setText(str(val))
        
    def on_transition_slider_changed(self, val):
        sec = val / 10.0
        self.lbl_transition_val.setText(f"{sec:.1f}s")
        
    def on_mask_mode_changed(self, index):
        mode = self.combo_mask_mode.currentText()
        is_full_box = (mode == "Full Box")
        self.slider_thresh.setEnabled(not is_full_box)
        self.lbl_thresh_val.setEnabled(not is_full_box)
        self.log(f"Mask mode: {mode}")
        
    def on_overwrite_toggled(self, checked):
        if self.stacked_inputs.currentIndex() == 1:
            self.txt_batch_out.setEnabled(not checked)
            self.btn_browse_batch_out.setEnabled(not checked)

    def on_roi_changed(self):
        pass

    def update_action_states(self):
        is_proc = self.is_processing()
        
        if is_proc:
            self.btn_preview.setEnabled(False)
            self.btn_start.setVisible(False)
            self.btn_combine.setVisible(False)
            self.btn_cancel.setVisible(True)
            self.sidebar.setEnabled(False)
            self.gallery_widget.setEnabled(False)
            return
            
        self.btn_cancel.setVisible(False)
        self.sidebar.setEnabled(True)
        self.gallery_widget.setEnabled(True)
        
        curr_idx = self.stacked_inputs.currentIndex()
        if curr_idx == 0:  # Single Mode
            self.btn_start.setVisible(True)
            self.btn_combine.setVisible(False)
            has_input = bool(self.selected_single_video)
            self.btn_preview.setEnabled(has_input and self.preview_frame_bgr is not None)
            self.btn_start.setEnabled(has_input and self.preview_frame_bgr is not None)
            
        elif curr_idx == 1:  # Batch Mode
            self.btn_start.setVisible(True)
            self.btn_combine.setVisible(False)
            has_files = len(self.batch_video_files) > 0
            is_overwrite = self.chk_overwrite.isChecked()
            has_output = is_overwrite or bool(self.selected_batch_output)
            self.btn_preview.setEnabled(has_files and self.preview_frame_bgr is not None)
            self.btn_start.setEnabled(has_files and has_output and self.preview_frame_bgr is not None)
            
        else:  # Combine Mode
            self.btn_start.setVisible(False)
            self.btn_combine.setVisible(True)
            selected_paths = self.gallery_widget.get_selected_video_paths()
            self.btn_combine.setEnabled(len(selected_paths) >= 2)
            
    def is_processing(self):
        is_rem_running = self.worker is not None and self.worker.isRunning()
        is_comb_running = self.combine_worker is not None and self.combine_worker.isRunning()
        return is_rem_running or is_comb_running
        
    def log(self, text):
        self.txt_log.append(text)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def clear_video_preview(self):
        self.preview_frame_bgr = None
        self.preview_frame_rgb = None
        self.preview_video_info = None
        self.canvas.pixmap = None
        self.canvas.image = None
        self.canvas.update()
        
    def load_video_preview(self, path):
        try:
            self.log(f"Extracting preview frame from: {os.path.basename(path)}...")
            frame_rgb, info = get_video_preview_frame(path)
            self.preview_frame_rgb = frame_rgb
            self.preview_frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            self.preview_video_info = info
            self.canvas.set_frame(frame_rgb)
            self.log(f"Preview frame loaded: {info['width']}x{info['height']} @ {info['fps']:.2f}fps")
            self.lbl_hud_status.setText(f"Loaded: {os.path.basename(path)}")
            self.update_action_states()
        except Exception as e:
            self.log(f"Error loading preview: {str(e)}")
            self.clear_video_preview()
            self.update_action_states()
            QMessageBox.critical(self, "Preview Error", f"Could not load preview frame from video:\n{str(e)}")
            
    def play_video_file(self, video_path):
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "File Not Found", f"Video file does not exist:\n{video_path}")
            return
        dlg = VideoPlayerDialog(video_path, self)
        dlg.exec()
        
    # --- Drag & Drop Handlers
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
            
        file_paths = [u.toLocalFile() for u in urls if u.toLocalFile()]
        if not file_paths:
            return
            
        first_path = file_paths[0]
        supported_exts = ('.mp4', '.avi', '.mov', '.mkv', '.wmv')
        
        if self.stacked_inputs.currentIndex() == 2:  # Combine Mode
            added = []
            for p in file_paths:
                if os.path.isdir(p):
                    for itm in os.listdir(p):
                        full = os.path.join(p, itm)
                        if os.path.isfile(full) and itm.lower().endswith(supported_exts):
                            added.append(full)
                elif os.path.isfile(p) and p.lower().endswith(supported_exts):
                    added.append(p)
            if added:
                self.gallery_widget.add_videos(added)
                self.log(f"Added {len(added)} dropped video(s) to Combine Gallery.")
            return
            
        if os.path.isdir(first_path):
            self.switch_mode(1)
            self.set_batch_input_folder(first_path)
        else:
            ext = os.path.splitext(first_path)[1].lower()
            if ext in supported_exts:
                if self.stacked_inputs.currentIndex() == 0:
                    self.set_single_video_file(first_path)
                else:
                    parent_dir = os.path.dirname(first_path)
                    self.set_batch_input_folder(parent_dir)
                    self.load_video_preview(first_path)
            else:
                QMessageBox.warning(self, "Invalid File Type", "Please drop a video file (.mp4, .avi, .mov, etc.) or a directory folder.")
                
    # --- File/Folder Selectors
    def set_single_video_file(self, path):
        self.selected_single_video = path
        self.txt_single_file.setText(os.path.basename(path))
        self.load_video_preview(path)
        
    def browse_single_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        if path:
            self.set_single_video_file(path)
            
    def set_batch_input_folder(self, path):
        self.selected_batch_folder = path
        self.txt_batch_in.setText(os.path.basename(path) or path)
        
        supported_exts = ('.mp4', '.avi', '.mov', '.mkv', '.wmv')
        self.batch_video_files = []
        try:
            for item in os.listdir(path):
                full_item = os.path.join(path, item)
                if os.path.isfile(full_item) and item.lower().endswith(supported_exts):
                    self.batch_video_files.append(full_item)
            
            self.lbl_batch_stats.setText(f"{len(self.batch_video_files)} video(s) found.")
            self.log(f"Batch folder scanned: Found {len(self.batch_video_files)} video files.")
            
            if self.batch_video_files:
                self.load_video_preview(self.batch_video_files[0])
            else:
                self.clear_video_preview()
        except Exception as e:
            self.log(f"Error scanning folder: {str(e)}")
            QMessageBox.critical(self, "Scan Error", f"Could not read directory contents:\n{str(e)}")
            
        if not self.selected_batch_output:
            out_default = os.path.join(path, "no_watermarks")
            self.selected_batch_output = out_default
            self.txt_batch_out.setText(os.path.basename(out_default))
            
        self.update_action_states()
        
    def browse_batch_in_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Input Batch Folder", "")
        if path:
            self.set_batch_input_folder(path)
            
    def browse_batch_out_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if path:
            self.selected_batch_output = path
            self.txt_batch_out.setText(os.path.basename(path))
            self.update_action_states()
            
    def browse_combine_out_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Combine Output Folder", "")
        if path:
            self.selected_combine_output_dir = path
            self.txt_combine_out.setText(os.path.basename(path))
            
    # --- Watermark Processing Triggers
    def show_removal_preview(self):
        if self.preview_frame_bgr is None:
            return
            
        roi = self.canvas.roi_rect
        thresh = self.slider_thresh.value()
        dilation = self.slider_dilation.value()
        radius = self.slider_radius.value()
        method = self.combo_method.currentText()
        mask_mode = self.combo_mask_mode.currentText()
        
        dlg = PreviewDialog(self.preview_frame_bgr, roi, thresh, dilation, radius, method, mask_mode, self)
        dlg.exec()
        
    def start_processing(self):
        if self.is_processing():
            return
            
        is_batch = self.stacked_inputs.currentIndex() == 1
        is_overwrite = self.chk_overwrite.isChecked()
        
        if is_batch:
            if not self.batch_video_files:
                QMessageBox.warning(self, "Missing Files", "No videos found in the selected batch input directory.")
                return
            if not is_overwrite and not self.selected_batch_output:
                QMessageBox.warning(self, "Missing Output", "Please select an output folder to save the processed videos.")
                return
            if not is_overwrite and not os.path.exists(self.selected_batch_output):
                os.makedirs(self.selected_batch_output, exist_ok=True)
                
            video_paths = self.batch_video_files
            output_dest = self.selected_batch_output if not is_overwrite else ""
            
        else:  # Single File Mode
            if not self.selected_single_video:
                QMessageBox.warning(self, "Missing Input", "Please select a video file to process.")
                return
                
            if is_overwrite:
                output_dest = self.selected_single_video
            else:
                file_name = os.path.basename(self.selected_single_video)
                name_part, ext = os.path.splitext(file_name)
                default_out_name = f"{name_part}_no_watermark{ext}"
                
                output_dest, _ = QFileDialog.getSaveFileName(
                    self, "Save Processed Video", default_out_name,
                    "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
                )
                
                if not output_dest:
                    return
                
            video_paths = [self.selected_single_video]
            
        self.progress_bar.setValue(0)
        self.batch_progress_bar.setValue(0)
        self.lbl_hud_pct.setText("0%")
        self.lbl_hud_status.setText("Processing: Starting...")
        
        if is_batch:
            self.lbl_batch_progress.setVisible(True)
            self.batch_progress_bar.setVisible(True)
        else:
            self.lbl_batch_progress.setVisible(False)
            self.batch_progress_bar.setVisible(False)
            
        self.log("\n====================================")
        self.log(f"Starting watermark removal. Total videos: {len(video_paths)}")
        
        roi = self.canvas.roi_rect
        thresh = self.slider_thresh.value()
        dilation = self.slider_dilation.value()
        radius = self.slider_radius.value()
        method = self.combo_method.currentText()
        mask_mode = self.combo_mask_mode.currentText()
        cpu_threads = int(self.combo_threads.currentText())
        
        self.worker = WatermarkRemoverWorker(
            video_paths=video_paths,
            output_dir=output_dest,
            roi=roi,
            threshold=thresh,
            dilation_size=dilation,
            inpaint_radius=radius,
            inpaint_method=method,
            is_batch=is_batch,
            mask_mode=mask_mode,
            is_overwrite=is_overwrite,
            cpu_threads=cpu_threads
        )
        
        self.worker.progress_changed.connect(self.on_worker_progress)
        self.worker.batch_progress_changed.connect(self.on_worker_batch_progress)
        self.worker.status_changed.connect(self.on_worker_status)
        self.worker.videos_processed.connect(self.on_watermark_videos_processed)
        self.worker.finished.connect(self.on_worker_finished)
        
        self.update_action_states()
        self.worker.start()
        
    def on_watermark_videos_processed(self, output_paths):
        if output_paths:
            self.gallery_widget.add_videos(output_paths)
            self.log(f"✓ Added {len(output_paths)} processed video(s) to Combine Gallery.")
            self.switch_mode(2)
            
    def on_worker_progress(self, pct):
        self.progress_bar.setValue(pct)
        self.lbl_hud_pct.setText(f"{pct}%")
        self.lbl_hud_status.setText(f"Removing Watermark: {pct}%")
        
    def on_worker_batch_progress(self, pct):
        self.batch_progress_bar.setValue(pct)
        self.lbl_batch_progress.setText(f"Overall Batch Progress: {pct}%")
        
    def on_worker_status(self, status_text):
        self.log(status_text)
        
    def on_worker_finished(self, success, message):
        self.worker = None
        self.update_action_states()
        
        self.progress_bar.setValue(0)
        self.batch_progress_bar.setValue(0)
        self.lbl_hud_pct.setText("100%" if success else "0%")
        self.lbl_hud_status.setText("Completed Successfully" if success else "Processing Stopped")
        
        self.log("\n====================================")
        self.log(message)
        
        if success:
            is_batch = (self.stacked_inputs.currentIndex() == 1)
            count = len(self.batch_video_files) if is_batch else 1
            op_type = "watermark_batch" if is_batch else "watermark_single"
            details = f"Batch of {count} videos" if is_batch else os.path.basename(self.selected_single_video or "video")
            license_client.log_usage_async(op_type, count=count, details=details)

            QMessageBox.information(
                self, "Watermark Removal Complete",
                f"{message}\n\nYour processed videos are ready in the 'Combiner' gallery."
            )
        else:
            QMessageBox.warning(self, "Process Incomplete", message)
            
    # --- Combine Videos Triggers
    def start_combining(self):
        if self.is_processing():
            return
            
        selected_paths = self.gallery_widget.get_selected_video_paths()
        if len(selected_paths) < 2:
            QMessageBox.warning(self, "Insufficient Videos", "Select at least 2 videos in the gallery to combine.")
            return
            
        for p in selected_paths:
            if not os.path.exists(p):
                QMessageBox.critical(self, "Missing Video File", f"Cannot combine because video is missing:\n{p}")
                return
                
        if self.selected_combine_output_dir and os.path.exists(self.selected_combine_output_dir):
            out_dir = self.selected_combine_output_dir
        elif self.selected_batch_output and os.path.exists(self.selected_batch_output):
            out_dir = self.selected_batch_output
        else:
            out_dir = os.path.dirname(os.path.abspath(selected_paths[0]))
            
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_filename = f"combined_{now_str}.mp4"
        out_path = os.path.join(out_dir, out_filename)
        
        trans_name = self.combo_transition.currentText()
        trans_map = {
            "Smooth Fade": "fade",
            "Dissolve": "dissolve",
            "Fade to Black": "fadeblack",
            "Wipe Left": "wipeleft",
            "Wipe Right": "wiperight",
            "Smooth Slide": "smoothleft"
        }
        trans_type = trans_map.get(trans_name, "fade")
        trans_dur = self.slider_transition_dur.value() / 10.0
        
        self.progress_bar.setValue(0)
        self.batch_progress_bar.setValue(0)
        self.lbl_hud_pct.setText("0%")
        self.lbl_hud_status.setText("Merging Videos...")
        self.lbl_batch_progress.setVisible(True)
        self.batch_progress_bar.setVisible(True)
        
        self.log("\n====================================")
        self.log(f"Starting Video Combine. Total clips: {len(selected_paths)}")
        
        self.combine_worker = VideoCombinerWorker(
            video_paths=selected_paths,
            output_path=out_path,
            transition_duration=trans_dur,
            transition_type=trans_type
        )
        
        self.combine_worker.progress_changed.connect(self.on_combine_step_progress)
        self.combine_worker.overall_progress_changed.connect(self.on_combine_overall_progress)
        self.combine_worker.status_changed.connect(self.on_combine_status)
        self.combine_worker.finished.connect(self.on_combine_finished)
        
        self.update_action_states()
        self.combine_worker.start()
        
    def on_combine_step_progress(self, pct):
        self.progress_bar.setValue(pct)
        self.lbl_hud_pct.setText(f"{pct}%")
        self.lbl_hud_status.setText(f"Combining Step: {pct}%")
        
    def on_combine_overall_progress(self, pct):
        self.batch_progress_bar.setValue(pct)
        self.lbl_batch_progress.setText(f"Overall Merge Progress: {pct}%")
        
    def on_combine_status(self, text):
        self.log(text)
        
    def on_combine_finished(self, success, message, meta):
        self.combine_worker = None
        self.update_action_states()
        
        self.progress_bar.setValue(0)
        self.batch_progress_bar.setValue(0)
        self.lbl_hud_pct.setText("100%" if success else "0%")
        self.lbl_hud_status.setText("Merge Complete" if success else "Merge Stopped")
        
        self.log("\n====================================")
        self.log(message)
        
        if success and meta and os.path.exists(meta.get("path", "")):
            num_clips = meta.get("video_count", 2)
            out_name = os.path.basename(meta.get("path", "merged.mp4"))
            license_client.log_usage_async("video_combine", count=num_clips, details=f"Combined {num_clips} clips into {out_name}")

            dlg = MergeSuccessDialog(meta, self)
            dlg.exec()
        elif not success:
            QMessageBox.warning(self, "Combine Error", message)
            
    def cancel_processing(self):
        active_worker = self.worker if (self.worker and self.worker.isRunning()) else self.combine_worker
        if active_worker and active_worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Cancel",
                "Are you sure you want to stop the active operation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.log("Cancelling operation...")
                active_worker.cancel()

    # --- SaaS Licensing Helpers
    def _get_license_summary_text(self) -> str:
        if not license_client.user_data:
            return "Active Session"
        u = license_client.user_data
        plan = u.get("plan_type", "")
        if plan == "lifetime":
            return "Lifetime Pro"
        elif plan == "7_days":
            return "Trial (7 Days)"
        elif plan == "1_month":
            return "Monthly Plan"
        elif plan == "1_year":
            return "Annual Plan"
        elif plan == "custom":
            return "Custom Plan"
        return "Active License"

    def open_account_dialog(self):
        auth_dlg = AuthDialog(self)
        auth_dlg.tabs.setCurrentIndex(2)
        auth_dlg.exec()
        self.title_bar.btn_license_pill.setText(self._get_license_summary_text())

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Exit DOLA AI Video Studio",
            "Are you sure you want to exit?\n\nAny active video processing will be safely terminated.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


class PreviewDialog(QDialog):
    """Modern modal dialog displaying live removal preview comparison."""
    def __init__(self, frame_bgr, roi_dict, threshold, dilation, radius, method, mask_mode, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Watermark Inpainting Preview")
        self.resize(900, 520)
        self.setStyleSheet("background-color: #0b0f19; color: #f8fafc;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title_lbl = QLabel("Live Inpainting Preview")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title_lbl)
        
        grid = QGridLayout()
        grid.setSpacing(14)
        
        h, w = frame_bgr.shape[:2]
        rx, ry, rw, rh = roi_dict["x"], roi_dict["y"], roi_dict["width"], roi_dict["height"]
        pad = 20
        x1 = max(0, rx - pad)
        y1 = max(0, ry - pad)
        x2 = min(w, rx + rw + pad)
        y2 = min(h, ry + rh + pad)
        crop_bgr = frame_bgr[y1:y2, x1:x2].copy()
        
        crop_roi = {
            "x": rx - x1,
            "y": ry - y1,
            "width": rw,
            "height": rh
        }
        
        # 1. Original
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        lbl_orig_img = QLabel()
        lbl_orig_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_orig_img.setPixmap(self._to_pixmap(crop_rgb))
        grid.addWidget(QLabel("1. Original Frame:"), 0, 0)
        grid.addWidget(lbl_orig_img, 1, 0)
        
        # 2. Mask
        mask = create_mask_for_frame(crop_bgr, crop_roi, threshold, dilation, mask_mode)
        mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        lbl_mask_img = QLabel()
        lbl_mask_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mask_img.setPixmap(self._to_pixmap(mask_rgb))
        grid.addWidget(QLabel("2. Generated Detection Mask:"), 0, 1)
        grid.addWidget(lbl_mask_img, 1, 1)
        
        # 3. Clean Inpainted Result
        inpaint_flag = cv2.INPAINT_TELEA if method == "Telea" else cv2.INPAINT_NS
        res_bgr = cv2.inpaint(crop_bgr, mask, radius, inpaint_flag)
        res_rgb = cv2.cvtColor(res_bgr, cv2.COLOR_BGR2RGB)
        lbl_res_img = QLabel()
        lbl_res_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_res_img.setPixmap(self._to_pixmap(res_rgb))
        grid.addWidget(QLabel("3. Clean Inpainted Output:"), 0, 2)
        grid.addWidget(lbl_res_img, 1, 2)
        
        layout.addLayout(grid)
        
        h_btn = QHBoxLayout()
        h_btn.addStretch()
        btn_close = QPushButton("Close Preview")
        btn_close.setProperty("class", "btn-primary")
        btn_close.clicked.connect(self.accept)
        h_btn.addWidget(btn_close)
        layout.addLayout(h_btn)
        
    def _to_pixmap(self, img_rgb):
        h, w, c = img_rgb.shape
        q_img = QImage(img_rgb.data, w, h, c * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img)
        return pix.scaled(260, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
