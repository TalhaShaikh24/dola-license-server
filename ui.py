import os
import cv2
import numpy as np
import datetime
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush, QIcon, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QSlider, QComboBox, QProgressBar, QTextEdit,
    QFileDialog, QMessageBox, QTabWidget, QGroupBox, QSplitter, QDialog,
    QCheckBox, QStackedWidget
)
from remover import WatermarkRemoverWorker, get_video_preview_frame, create_mask_for_frame
from video_combiner import VideoCombinerWorker, get_media_properties, format_duration, format_file_size
from combiner_widgets import (
    VideoGalleryCard, VideoGalleryWidget, VideoPlayerDialog, MergeSuccessDialog, CircularOrderBadge
)
from licensing.license_client import license_client
from licensing.auth_dialog import AuthDialog

# Modern QSS stylesheet for dark premium look
DARK_STYLESHEET = """
QMainWindow {
    background-color: #0f0f12;
}
QWidget {
    color: #e2e2e9;
    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    font-size: 13px;
}
QFrame#sidebar {
    background-color: #16161c;
    border-right: 1px solid #282833;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #282833;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    background-color: #121217;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    left: 8px;
    color: #5d5fef;
}
QPushButton {
    background-color: #212129;
    border: 1px solid #30303e;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
    color: #e2e2e9;
}
QPushButton:hover {
    background-color: #2d2d39;
    border-color: #404052;
}
QPushButton:pressed {
    background-color: #181820;
}
QPushButton:disabled {
    background-color: #16161c;
    border-color: #202029;
    color: #606070;
}
QPushButton#action-btn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5d5fef, stop:1 #7274f8);
    color: white;
    border: none;
    font-weight: bold;
    font-size: 13px;
}
QPushButton#action-btn:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7274f8, stop:1 #8e90ff);
}
QPushButton#action-btn:pressed {
    background-color: #494bd6;
}
QPushButton#action-btn:disabled {
    background-color: #212129;
    color: #606070;
    border: 1px solid #282833;
}
QPushButton#combine-btn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7928ca, stop:1 #ff0080);
    color: white;
    border: none;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 16px;
    border-radius: 6px;
}
QPushButton#combine-btn:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8a3bd9, stop:1 #ff2a93);
}
QPushButton#combine-btn:pressed {
    background-color: #671cae;
}
QPushButton#combine-btn:disabled {
    background-color: #212129;
    color: #606070;
    border: 1px solid #282833;
}
QPushButton#cancel-btn {
    background-color: #db4444;
    color: white;
    border: none;
    font-weight: bold;
}
QPushButton#cancel-btn:hover {
    background-color: #ea5656;
}
QPushButton#cancel-btn:pressed {
    background-color: #b73333;
}
QLineEdit, QTextEdit {
    background-color: #0b0b0e;
    border: 1px solid #282833;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e2e2e9;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #5d5fef;
}
QProgressBar {
    background-color: #0b0b0e;
    border: 1px solid #282833;
    border-radius: 6px;
    text-align: center;
    color: white;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5d5fef, stop:1 #8e90ff);
    border-radius: 5px;
}
QSlider::groove:horizontal {
    border: 1px solid #282833;
    height: 6px;
    background: #0b0b0e;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #5d5fef;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #30303e;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #e2e2e9;
    border-color: #5d5fef;
}
QComboBox {
    background-color: #0b0b0e;
    border: 1px solid #282833;
    border-radius: 6px;
    padding: 6px 10px;
}
QComboBox:on {
    border-color: #5d5fef;
}
QComboBox QAbstractItemView {
    background-color: #16161c;
    border: 1px solid #282833;
    selection-background-color: #5d5fef;
    selection-color: white;
}
QTabBar::tab {
    background-color: transparent;
    border-bottom: 2px solid transparent;
    padding: 10px 14px;
    font-weight: 500;
    color: #a0a0ba;
}
QTabBar::tab:hover {
    color: #e2e2e9;
}
QTabBar::tab:selected {
    color: #5d5fef;
    border-bottom: 2px solid #5d5fef;
    font-weight: bold;
}
QTabWidget::pane {
    border: none;
}
QDialog {
    background-color: #121217;
}
"""

class ROISelectionCanvas(QWidget):
    """
    Custom widget that displays a video preview frame and allows the user to
    interactively select/draw/drag a Region of Interest (ROI) for watermark removal.
    """
    roi_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.pixmap = None
        
        # Bounding box in raw image pixel coords: [x, y, w, h]
        self.roi_rect = {"x": 0, "y": 0, "width": 0, "height": 0, "ref_width": 100, "ref_height": 100}
        self.raw_image_width = 100
        self.raw_image_height = 100
        
        # Interactive state
        self.active_handle = None  # 'tl', 'tr', 'bl', 'br', 'move', 'draw'
        self.drag_start = QPoint()
        self.drag_rect_start = QRect()
        self.handle_size = 8
        self.aspect_ratio_locked = False
        
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
    def set_frame(self, frame_rgb):
        """
        Loads an RGB image (numpy array) to display on the canvas.
        """
        if frame_rgb is None:
            return
            
        self.image = frame_rgb
        h, w, c = frame_rgb.shape
        self.raw_image_width = w
        self.raw_image_height = h
        
        # Convert numpy array to QImage
        bytes_per_line = c * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.pixmap = QPixmap.fromImage(q_img)
        
        # Initialize default watermark box at bottom-right if not already set or out of bounds
        if self.roi_rect["width"] == 0 or self.roi_rect["height"] == 0 or \
           self.roi_rect["ref_width"] != w or self.roi_rect["ref_height"] != h:
            
            bw = int(w * 0.16)
            bh = int(h * 0.05)
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
        
    def widget_to_image_coords(self, wx, wy):
        scale, x_off, y_off, w_sc, h_sc = self.get_scaling_metrics()
        
        ix = (wx - x_off) / scale
        iy = (wy - y_off) / scale
        
        ix = max(0, min(int(ix), self.raw_image_width - 1))
        iy = max(0, min(int(iy), self.raw_image_height - 1))
        
        return ix, iy
        
    def image_to_widget_coords(self, ix, iy):
        scale, x_off, y_off, _, _ = self.get_scaling_metrics()
        wx = int(ix * scale) + x_off
        wy = int(iy * scale) + y_off
        return wx, wy
        
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
                
        box_rect = QRect(wx, wy, ww, wh)
        if box_rect.contains(int(mx), int(my)):
            self.active_handle = 'move'
            self.drag_start = QPoint(int(mx), int(my))
            self.drag_rect_start = QRect(wx, wy, ww, wh)
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            return
            
        _, _, _, w_sc, h_sc = self.get_scaling_metrics()
        if x_off <= mx <= x_off + w_sc and y_off <= my <= y_off + h_sc:
            self.active_handle = 'draw'
            self.drag_start = QPoint(int(mx), int(my))
            self.drag_rect_start = QRect(int(mx), int(my), 0, 0)
            
    def mouseMoveEvent(self, event):
        if self.pixmap is None:
            return
            
        pos = event.position()
        mx, my = int(pos.x()), int(pos.y())
        
        scale, x_off, y_off, w_sc, h_sc = self.get_scaling_metrics()
        wx = int(self.roi_rect["x"] * scale) + x_off
        wy = int(self.roi_rect["y"] * scale) + y_off
        ww = int(self.roi_rect["width"] * scale)
        wh = int(self.roi_rect["height"] * scale)
        
        if self.active_handle is None:
            handles = self.get_handles_widget_rects(wx, wy, ww, wh)
            if handles['tl'].contains(mx, my) or handles['br'].contains(mx, my):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handles['tr'].contains(mx, my) or handles['bl'].contains(mx, my):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif QRect(wx, wy, ww, wh).contains(mx, my):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                
        if self.active_handle is None:
            return
            
        dx = mx - self.drag_start.x()
        dy = my - self.drag_start.y()
        
        orig_rect = self.drag_rect_start
        new_wx, new_wy, new_ww, new_wh = orig_rect.x(), orig_rect.y(), orig_rect.width(), orig_rect.height()
        
        if self.active_handle == 'move':
            new_wx = orig_rect.x() + dx
            new_wy = orig_rect.y() + dy
            new_wx = max(x_off, min(new_wx, x_off + w_sc - new_ww))
            new_wy = max(y_off, min(new_wy, y_off + h_sc - new_wh))
            
        elif self.active_handle == 'draw':
            x1 = min(self.drag_start.x(), mx)
            y1 = min(self.drag_start.y(), my)
            x2 = max(self.drag_start.x(), mx)
            y2 = max(self.drag_start.y(), my)
            
            x1 = max(x_off, min(x1, x_off + w_sc))
            y1 = max(y_off, min(y1, y_off + h_sc))
            x2 = max(x_off, min(x2, x_off + w_sc))
            y2 = max(y_off, min(y2, y_off + h_sc))
            
            new_wx = x1
            new_wy = y1
            new_ww = x2 - x1
            new_wh = y2 - y1
            
        elif self.active_handle == 'tl':
            new_wx = orig_rect.x() + dx
            new_wy = orig_rect.y() + dy
            new_ww = (orig_rect.x() + orig_rect.width()) - new_wx
            new_wh = (orig_rect.y() + orig_rect.height()) - new_wy
            
        elif self.active_handle == 'tr':
            new_wy = orig_rect.y() + dy
            new_ww = orig_rect.width() + dx
            new_wh = (orig_rect.y() + orig_rect.height()) - new_wy
            
        elif self.active_handle == 'bl':
            new_wx = orig_rect.x() + dx
            new_ww = (orig_rect.x() + orig_rect.width()) - new_wx
            new_wh = orig_rect.height() + dy
            
        elif self.active_handle == 'br':
            new_ww = orig_rect.width() + dx
            new_wh = orig_rect.height() + dy
            
        if self.active_handle in ['tl', 'tr', 'bl', 'br']:
            if new_ww < 10:
                new_ww = 10
                if self.active_handle in ['tl', 'bl']:
                    new_wx = orig_rect.x() + orig_rect.width() - 10
            if new_wh < 10:
                new_wh = 10
                if self.active_handle in ['tl', 'tr']:
                    new_wy = orig_rect.y() + orig_rect.height() - 10
                    
            if new_wx < x_off:
                new_ww -= (x_off - new_wx)
                new_wx = x_off
            if new_wy < y_off:
                new_wh -= (y_off - new_wy)
                new_wy = y_off
            if new_wx + new_ww > x_off + w_sc:
                new_ww = x_off + w_sc - new_wx
            if new_wy + new_wh > y_off + h_sc:
                new_wh = y_off + h_sc - new_wy
                
        ix, iy = self.widget_to_image_coords(new_wx, new_wy)
        iw = int(new_ww / scale)
        ih = int(new_wh / scale)
        
        ix = max(0, min(ix, self.raw_image_width - 1))
        iy = max(0, min(iy, self.raw_image_height - 1))
        iw = max(5, min(iw, self.raw_image_width - ix))
        ih = max(5, min(ih, self.raw_image_height - iy))
        
        self.roi_rect = {
            "x": ix,
            "y": iy,
            "width": iw,
            "height": ih,
            "ref_width": self.raw_image_width,
            "ref_height": self.raw_image_height
        }
        
        self.update()
        self.roi_changed.emit()
        
    def mouseReleaseEvent(self, event):
        self.active_handle = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(11, 11, 14))
        
        if self.pixmap is not None and not self.pixmap.isNull():
            scale, x_off, y_off, w_sc, h_sc = self.get_scaling_metrics()
            
            painter.drawPixmap(x_off, y_off, w_sc, h_sc, self.pixmap)
            
            wx = int(self.roi_rect["x"] * scale) + x_off
            wy = int(self.roi_rect["y"] * scale) + y_off
            ww = int(self.roi_rect["width"] * scale)
            wh = int(self.roi_rect["height"] * scale)
            
            painter.fillRect(QRect(wx, wy, ww, wh), QColor(93, 95, 239, 45))
            
            pen = QPen(QColor(93, 95, 239, 255), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(wx, wy, ww, wh)
            
            handles = self.get_handles_widget_rects(wx, wy, ww, wh)
            painter.setPen(QPen(QColor(93, 95, 239, 255), 1))
            painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
            
            for handle_name, rect in handles.items():
                painter.drawRect(rect)
        else:
            pen = QPen(QColor(48, 48, 62, 255), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            margin = 20
            painter.drawRoundedRect(
                margin, margin, self.width() - margin * 2, self.height() - margin * 2,
                8.0, 8.0
            )
            
            painter.setPen(QColor(160, 160, 186, 255))
            text = "Video Frame Preview\n\nLoad a video to position the watermark box.\nClick and drag to adjust region, or corners to resize.\n\nWatermark box will automatically align at bottom-right by default."
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                text
            )


class PreviewDialog(QDialog):
    """
    Dialog window displaying side-by-side comparison crops.
    """
    def __init__(self, frame_bgr, roi, threshold=200, dilation=2, radius=3, method="Telea", mask_mode="Static Text", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Watermark Removal Live Preview")
        self.resize(780, 320)
        
        layout = QVBoxLayout(self)
        h_layout = QHBoxLayout()
        
        h, w = frame_bgr.shape[:2]
        ref_w = roi.get("ref_width", w)
        ref_h = roi.get("ref_height", h)
        
        rx1 = roi["x"] / ref_w
        ry1 = roi["y"] / ref_h
        rx2 = (roi["x"] + roi["width"]) / ref_w
        ry2 = (roi["y"] + roi["height"]) / ref_h
        
        x1 = max(0, min(int(rx1 * w), w - 1))
        y1 = max(0, min(int(ry1 * h), h - 1))
        x2 = max(x1 + 5, min(int(rx2 * w), w))
        y2 = max(y1 + 5, min(int(ry2 * h), h))
        
        margin_x = 12
        margin_y = 12
        cx1 = max(0, x1 - margin_x)
        cy1 = max(0, y1 - margin_y)
        cx2 = min(w, x2 + margin_x)
        cy2 = min(h, y2 + margin_y)
        
        crop_bgr = frame_bgr[cy1:cy2, cx1:cx2]
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        
        if mask_mode == "Full Box":
            mask_full = create_mask_for_frame(frame_bgr.shape, roi, threshold, dilation, None)
        else:
            mask_full = create_mask_for_frame(frame_bgr.shape, roi, threshold, dilation, frame_bgr)
        crop_mask = mask_full[cy1:cy2, cx1:cx2]
        crop_mask_rgb = cv2.cvtColor(crop_mask, cv2.COLOR_GRAY2RGB)
        
        method_cv = cv2.INPAINT_TELEA if method == "Telea" else cv2.INPAINT_NS
        inpainted_full = cv2.inpaint(frame_bgr, mask_full, radius, method_cv)
        crop_inpainted_bgr = inpainted_full[cy1:cy2, cx1:cx2]
        crop_inpainted_rgb = cv2.cvtColor(crop_inpainted_bgr, cv2.COLOR_BGR2RGB)
        
        def np_to_pixmap(arr):
            ch, cw = arr.shape[:2]
            q_img = QImage(arr.data, cw, ch, cw * 3, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(q_img)
            return pix.scaled(240, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            
        lbl_orig = QLabel()
        lbl_orig.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_orig.setPixmap(np_to_pixmap(crop_rgb))
        
        lbl_mask = QLabel()
        lbl_mask.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mask.setPixmap(np_to_pixmap(crop_mask_rgb))
        
        lbl_inp = QLabel()
        lbl_inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_inp.setPixmap(np_to_pixmap(crop_inpainted_rgb))
        
        def get_col(title, widget):
            col = QVBoxLayout()
            lbl_title = QLabel(title)
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_title.setStyleSheet("font-weight: bold; color: #5d5fef; font-size: 14px;")
            col.addWidget(lbl_title)
            col.addWidget(widget)
            return col
            
        h_layout.addLayout(get_col("Original Video", lbl_orig))
        h_layout.addLayout(get_col("Watermark Mask", lbl_mask))
        h_layout.addLayout(get_col("Inpainted Result", lbl_inp))
        
        layout.addLayout(h_layout)
        
        note_lbl = QLabel(f"Note: ROI cropped to selection with {margin_x}px padding and scaled for inspect. Adjust threshold slider if pixels of the watermark are missing.")
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet("color: #a0a0ba; font-size: 11px; margin-top: 8px;")
        layout.addWidget(note_lbl)
        
        btn_close = QPushButton("Apply & Close")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("background-color: #5d5fef; color: white; font-weight: bold; margin-top: 10px;")
        layout.addWidget(btn_close)


class MainWindow(QMainWindow):
    """
    Main application Window. Handles watermark removal, processed videos gallery,
    video reordering with circular order badges, and smooth video combine.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dola AI Watermark Remover & Video Combiner — by Talha Shaikh (talhashaikh.com)")
        self.resize(1150, 720)
        self.setAcceptDrops(True)
        
        # State variables
        self.selected_single_video = ""
        self.selected_batch_folder = ""
        self.selected_batch_output = ""
        self.batch_video_files = []
        self.preview_frame_bgr = None
        self.preview_frame_rgb = None
        self.preview_video_info = None
        
        self.selected_combine_output_dir = ""
        
        # Threads
        self.worker = None
        self.combine_worker = None
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Sidebar Panel (Width 360px)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(360)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        
        # Application Title / Brand
        brand_lbl = QLabel("DOLA AI Watermark Remover")
        brand_lbl.setStyleSheet("font-size: 19px; font-weight: 800; color: #5d5fef; letter-spacing: 0.5px; margin-bottom: 2px;")
        sidebar_layout.addWidget(brand_lbl)
        
        sub_lbl = QLabel("Developed by <a href='https://talhashaikh.com' style='color:#a5b4fc; text-decoration:none; font-weight:bold;'>Talha Shaikh</a> &bull; <a href='https://talhashaikh.com' style='color:#6366f1; text-decoration:none;'>talhashaikh.com</a>")
        sub_lbl.setTextFormat(Qt.TextFormat.RichText)
        sub_lbl.setOpenExternalLinks(True)
        sub_lbl.setStyleSheet("color: #a0a0ba; font-size: 11px; margin-bottom: 8px;")
        sidebar_layout.addWidget(sub_lbl)
        
        # SaaS License Status Bar
        license_container = QWidget()
        license_container.setStyleSheet("background-color: #121217; border: 1px solid #282833; border-radius: 8px; margin-bottom: 10px;")
        license_box = QHBoxLayout(license_container)
        license_box.setContentsMargins(10, 6, 10, 6)
        
        self.license_status_lbl = QLabel(self._get_license_summary_text())
        self.license_status_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #10b981;")
        
        self.btn_manage_license = QPushButton("Account")
        self.btn_manage_license.setStyleSheet("font-size: 11px; padding: 4px 8px; background: #212129; border: 1px solid #30303e; border-radius: 4px; color: #e2e2e9;")
        self.btn_manage_license.clicked.connect(self.open_account_dialog)
        
        license_box.addWidget(self.license_status_lbl, 7)
        license_box.addWidget(self.btn_manage_license, 3)
        sidebar_layout.addWidget(license_container)
        
        # Tabs for Mode: Single vs Batch vs Combine
        self.tabs = QTabWidget()
        
        # -- Tab 1: Single File Mode
        tab_single = QWidget()
        tab_single_layout = QVBoxLayout(tab_single)
        tab_single_layout.setContentsMargins(0, 8, 0, 8)
        
        lbl_file = QLabel("Select Input Video File:")
        lbl_file.setStyleSheet("font-weight: 500; margin-bottom: 2px;")
        tab_single_layout.addWidget(lbl_file)
        
        h_file_select = QHBoxLayout()
        self.txt_single_file = QLabel("No video selected")
        self.txt_single_file.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #a0a0ba;")
        self.txt_single_file.setWordWrap(False)
        self.txt_single_file.setMinimumHeight(35)
        
        btn_browse_single = QPushButton("Browse")
        btn_browse_single.clicked.connect(self.browse_single_file)
        
        h_file_select.addWidget(self.txt_single_file, 8)
        h_file_select.addWidget(btn_browse_single, 2)
        tab_single_layout.addLayout(h_file_select)
        
        tab_single_layout.addStretch()
        self.tabs.addTab(tab_single, "Single Video")
        
        # -- Tab 2: Batch Folder Mode
        tab_batch = QWidget()
        tab_batch_layout = QVBoxLayout(tab_batch)
        tab_batch_layout.setContentsMargins(0, 8, 0, 8)
        
        lbl_batch_in = QLabel("Select Input Directory (Folder):")
        lbl_batch_in.setStyleSheet("font-weight: 500; margin-bottom: 2px;")
        tab_batch_layout.addWidget(lbl_batch_in)
        
        h_batch_in = QHBoxLayout()
        self.txt_batch_in = QLabel("No directory selected")
        self.txt_batch_in.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #a0a0ba;")
        self.txt_batch_in.setMinimumHeight(35)
        
        btn_browse_batch_in = QPushButton("Browse")
        btn_browse_batch_in.clicked.connect(self.browse_batch_in_folder)
        
        h_batch_in.addWidget(self.txt_batch_in, 8)
        h_batch_in.addWidget(btn_browse_batch_in, 2)
        tab_batch_layout.addLayout(h_batch_in)
        
        lbl_batch_out = QLabel("Select Output Directory:")
        lbl_batch_out.setStyleSheet("font-weight: 500; margin-top: 8px; margin-bottom: 2px;")
        tab_batch_layout.addWidget(lbl_batch_out)
        
        h_batch_out = QHBoxLayout()
        self.txt_batch_out = QLabel("No directory selected")
        self.txt_batch_out.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #a0a0ba;")
        self.txt_batch_out.setMinimumHeight(35)
        
        self.btn_browse_batch_out = QPushButton("Browse")
        self.btn_browse_batch_out.clicked.connect(self.browse_batch_out_folder)
        
        h_batch_out.addWidget(self.txt_batch_out, 8)
        h_batch_out.addWidget(self.btn_browse_batch_out, 2)
        tab_batch_layout.addLayout(h_batch_out)
        
        self.lbl_batch_stats = QLabel("0 videos found.")
        self.lbl_batch_stats.setStyleSheet("color: #a0a0ba; font-size: 11px; margin-top: 4px;")
        tab_batch_layout.addWidget(self.lbl_batch_stats)
        
        tab_batch_layout.addStretch()
        self.tabs.addTab(tab_batch, "Folder Batch")
        
        # -- Tab 3: Combine Videos Mode
        tab_combine = QWidget()
        tab_combine_layout = QVBoxLayout(tab_combine)
        tab_combine_layout.setContentsMargins(0, 8, 0, 8)
        
        lbl_combine_desc = QLabel("Merge Processed Videos:")
        lbl_combine_desc.setStyleSheet("font-weight: bold; color: #ff0080;")
        tab_combine_layout.addWidget(lbl_combine_desc)
        
        lbl_combine_info = QLabel("Select clips in the gallery, arrange merge order with numbered badges, and combine with smooth transitions.")
        lbl_combine_info.setWordWrap(True)
        lbl_combine_info.setStyleSheet("color: #a0a0ba; font-size: 11px; margin-bottom: 8px;")
        tab_combine_layout.addWidget(lbl_combine_info)
        
        lbl_combine_out = QLabel("Final Output Folder:")
        lbl_combine_out.setStyleSheet("font-weight: 500; margin-top: 4px; margin-bottom: 2px;")
        tab_combine_layout.addWidget(lbl_combine_out)
        
        h_combine_out = QHBoxLayout()
        self.txt_combine_out = QLabel("Default Output Folder")
        self.txt_combine_out.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #e2e2e9;")
        self.txt_combine_out.setMinimumHeight(35)
        
        btn_browse_combine_out = QPushButton("Browse")
        btn_browse_combine_out.clicked.connect(self.browse_combine_out_folder)
        
        h_combine_out.addWidget(self.txt_combine_out, 8)
        h_combine_out.addWidget(btn_browse_combine_out, 2)
        tab_combine_layout.addLayout(h_combine_out)
        
        tab_combine_layout.addStretch()
        self.tabs.addTab(tab_combine, "🎬 Combine Clips")
        
        sidebar_layout.addWidget(self.tabs)
        
        # 2A. Watermark Removal Settings Group (Visible in Tab 0 & 1)
        self.grp_settings = QGroupBox("Removal Configuration")
        settings_grid = QGridLayout(self.grp_settings)
        settings_grid.setSpacing(10)
        
        settings_grid.addWidget(QLabel("Color Brightness Threshold:"), 0, 0)
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
        
        settings_grid.addWidget(QLabel("Dilation Size (px):"), 1, 0)
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
        
        settings_grid.addWidget(QLabel("Inpainting Radius (px):"), 2, 0)
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
        
        settings_grid.addWidget(QLabel("Inpainting Algorithm:"), 4, 0)
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
        self.chk_overwrite.setStyleSheet("font-weight: bold; color: #db4444;")
        self.chk_overwrite.toggled.connect(self.on_overwrite_toggled)
        settings_grid.addWidget(self.chk_overwrite, 6, 0, 1, 2)
        
        sidebar_layout.addWidget(self.grp_settings)
        
        # 2B. Video Combine Settings Group (Visible in Tab 2)
        self.grp_combine_settings = QGroupBox("Transition & Combine Settings")
        combine_grid = QGridLayout(self.grp_combine_settings)
        combine_grid.setSpacing(10)
        
        combine_grid.addWidget(QLabel("Transition Effect:"), 0, 0)
        self.combo_transition = QComboBox()
        self.combo_transition.addItems([
            "Smooth Fade", "Dissolve", "Fade to Black",
            "Wipe Left", "Wipe Right", "Smooth Slide"
        ])
        combine_grid.addWidget(self.combo_transition, 0, 1)
        
        combine_grid.addWidget(QLabel("Transition Duration:"), 1, 0)
        self.slider_transition_dur = QSlider(Qt.Orientation.Horizontal)
        self.slider_transition_dur.setRange(2, 20)  # 0.2s to 2.0s
        self.slider_transition_dur.setValue(8)      # 0.8s default
        self.slider_transition_dur.valueChanged.connect(self.on_transition_slider_changed)
        self.lbl_transition_val = QLabel("0.8s")
        self.lbl_transition_val.setFixedWidth(32)
        self.lbl_transition_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        h_tdur = QHBoxLayout()
        h_tdur.addWidget(self.slider_transition_dur)
        h_tdur.addWidget(self.lbl_transition_val)
        combine_grid.addLayout(h_tdur, 1, 1)
        
        combine_grid.addWidget(QLabel("Audio Crossfade:"), 2, 0)
        lbl_audio_xfade = QLabel("✓ Enabled (Synchronized)")
        lbl_audio_xfade.setStyleSheet("color: #4ade80; font-weight: bold;")
        combine_grid.addWidget(lbl_audio_xfade, 2, 1)
        
        combine_grid.addWidget(QLabel("Normalization:"), 3, 0)
        lbl_norm = QLabel("✓ Auto (Preserve Aspect Ratio)")
        lbl_norm.setStyleSheet("color: #4ade80;")
        combine_grid.addWidget(lbl_norm, 3, 1)
        
        self.grp_combine_settings.setVisible(False)
        sidebar_layout.addWidget(self.grp_combine_settings)
        
        # 3. Sidebar Actions
        sidebar_layout.addSpacing(10)
        
        self.btn_preview = QPushButton("Show Watermark Preview")
        self.btn_preview.setObjectName("preview-btn")
        self.btn_preview.clicked.connect(self.show_removal_preview)
        self.btn_preview.setEnabled(False)
        sidebar_layout.addWidget(self.btn_preview)
        
        sidebar_layout.addSpacing(8)
        
        self.btn_start = QPushButton("Start Watermark Removal")
        self.btn_start.setObjectName("action-btn")
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_start.setEnabled(False)
        sidebar_layout.addWidget(self.btn_start)
        
        self.btn_combine = QPushButton("✨ Combine All")
        self.btn_combine.setObjectName("combine-btn")
        self.btn_combine.clicked.connect(self.start_combining)
        self.btn_combine.setVisible(False)
        sidebar_layout.addWidget(self.btn_combine)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("cancel-btn")
        self.btn_cancel.clicked.connect(self.cancel_processing)
        self.btn_cancel.setVisible(False)
        sidebar_layout.addWidget(self.btn_cancel)
        
        main_layout.addWidget(sidebar)
        
        # Right Layout: Top Stacked Area (ROI Canvas vs Gallery Widget) + Bottom Progress / Console
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 16, 16, 16)
        right_layout.setSpacing(12)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Stacked Widget
        self.stacked_view = QStackedWidget()
        
        # Page 0: ROI Canvas for watermark removal
        self.canvas = ROISelectionCanvas()
        self.canvas.roi_changed.connect(self.on_roi_changed)
        self.stacked_view.addWidget(self.canvas)
        
        # Page 1: Video Gallery & Reorder Widget
        self.gallery_widget = VideoGalleryWidget()
        self.gallery_widget.order_changed.connect(self.update_action_states)
        self.gallery_widget.play_requested.connect(self.play_video_file)
        self.stacked_view.addWidget(self.gallery_widget)
        
        splitter.addWidget(self.stacked_view)
        
        # Control Progress / Console Logs
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.setSpacing(8)
        
        self.lbl_progress = QLabel("Current Video Progress: 0%")
        self.lbl_progress.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        console_layout.addWidget(self.lbl_progress)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        console_layout.addWidget(self.progress_bar)
        
        self.lbl_batch_progress = QLabel("Overall Batch Progress: 0%")
        self.lbl_batch_progress.setStyleSheet("font-weight: bold; margin-top: 4px; margin-bottom: 2px;")
        self.lbl_batch_progress.setVisible(False)
        console_layout.addWidget(self.lbl_batch_progress)
        
        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setValue(0)
        self.batch_progress_bar.setVisible(False)
        console_layout.addWidget(self.batch_progress_bar)
        
        lbl_console_title = QLabel("Processing Status Logs:")
        lbl_console_title.setStyleSheet("font-weight: bold; color: #a0a0ba; font-size: 11px;")
        console_layout.addWidget(lbl_console_title)
        
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.append("Application initialized.\nReady to load video.")
        console_layout.addWidget(self.txt_log)
        
        console_widget.setFixedHeight(230)
        splitter.addWidget(console_widget)
        
        right_layout.addWidget(splitter)
        main_layout.addWidget(right_panel)
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.setStyleSheet(DARK_STYLESHEET)
        
    # --- GUI Handlers
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
        self.log(f"Mask mode changed to: {mode}")
        
    def on_overwrite_toggled(self, checked):
        if self.tabs.currentIndex() == 1:
            self.txt_batch_out.setEnabled(not checked)
            self.btn_browse_batch_out.setEnabled(not checked)
        self.log(f"Overwrite Original File(s) set to: {checked}")
        self.update_action_states()
        
    def on_roi_changed(self):
        roi = self.canvas.roi_rect
        self.log(f"Watermark region updated: [{roi['x']}, {roi['y']}, {roi['width']}x{roi['height']}] relative to {roi['ref_width']}x{roi['ref_height']}")
        
    def on_tab_changed(self, idx):
        if idx == 0:  # Single Video
            self.stacked_view.setCurrentIndex(0)
            self.grp_settings.setVisible(True)
            self.grp_combine_settings.setVisible(False)
            self.btn_preview.setVisible(True)
            self.btn_start.setVisible(True)
            self.btn_combine.setVisible(False)
            self.lbl_batch_progress.setVisible(False)
            self.batch_progress_bar.setVisible(False)
            if self.selected_single_video:
                self.load_video_preview(self.selected_single_video)
            else:
                self.clear_video_preview()
                
        elif idx == 1:  # Folder Batch
            self.stacked_view.setCurrentIndex(0)
            self.grp_settings.setVisible(True)
            self.grp_combine_settings.setVisible(False)
            self.btn_preview.setVisible(True)
            self.btn_start.setVisible(True)
            self.btn_combine.setVisible(False)
            self.lbl_batch_progress.setVisible(self.is_processing())
            self.batch_progress_bar.setVisible(self.is_processing())
            
            is_overwrite = self.chk_overwrite.isChecked()
            self.txt_batch_out.setEnabled(not is_overwrite)
            self.btn_browse_batch_out.setEnabled(not is_overwrite)
            
            if self.batch_video_files:
                self.load_video_preview(self.batch_video_files[0])
            else:
                self.clear_video_preview()
                
        else:  # Combine Videos
            self.stacked_view.setCurrentIndex(1)
            self.grp_settings.setVisible(False)
            self.grp_combine_settings.setVisible(True)
            self.btn_preview.setVisible(False)
            self.btn_start.setVisible(False)
            self.btn_combine.setVisible(True)
            self.lbl_batch_progress.setVisible(self.is_processing())
            self.batch_progress_bar.setVisible(self.is_processing())
            
        self.update_action_states()
        
    def update_action_states(self):
        is_proc = self.is_processing()
        
        if is_proc:
            self.btn_preview.setEnabled(False)
            self.btn_start.setVisible(False)
            self.btn_combine.setVisible(False)
            self.btn_cancel.setVisible(True)
            self.tabs.setEnabled(False)
            self.grp_settings.setEnabled(False)
            self.grp_combine_settings.setEnabled(False)
            self.gallery_widget.setEnabled(False)
            return
            
        self.btn_cancel.setVisible(False)
        self.tabs.setEnabled(True)
        self.grp_settings.setEnabled(True)
        self.grp_combine_settings.setEnabled(True)
        self.gallery_widget.setEnabled(True)
        
        curr_tab = self.tabs.currentIndex()
        if curr_tab == 0:  # Single Mode
            self.btn_start.setVisible(True)
            self.btn_combine.setVisible(False)
            has_input = bool(self.selected_single_video)
            self.btn_preview.setEnabled(has_input and self.preview_frame_bgr is not None)
            self.btn_start.setEnabled(has_input and self.preview_frame_bgr is not None)
            
        elif curr_tab == 1:  # Batch Mode
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
            self.log(f"Preview frame loaded. Video: {info['width']}x{info['height']} @ {info['fps']:.2f}fps")
            self.update_action_states()
        except Exception as e:
            self.log(f"Error loading preview: {str(e)}")
            self.clear_video_preview()
            self.update_action_states()
            QMessageBox.critical(self, "Preview Error", f"Could not load preview frame from video:\n{str(e)}")
            
    def play_video_file(self, video_path):
        """Opens dedicated VideoPlayerDialog for instant playback."""
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
        
        if self.tabs.currentIndex() == 2:  # Combine Mode
            # Add all dropped video files to gallery
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
            self.tabs.setCurrentIndex(1)
            self.set_batch_input_folder(first_path)
        else:
            ext = os.path.splitext(first_path)[1].lower()
            if ext in supported_exts:
                if self.tabs.currentIndex() == 0:
                    self.set_single_video_file(first_path)
                else:
                    self.log(f"Reference video dropped: {os.path.basename(first_path)}")
                    parent_dir = os.path.dirname(first_path)
                    self.set_batch_input_folder(parent_dir)
                    self.load_video_preview(first_path)
            else:
                QMessageBox.warning(self, "Invalid File Type", "Please drop a video file (.mp4, .avi, .mov, etc.) or a directory folder.")
                
    # --- File/Folder Dialogue selectors
    def set_single_video_file(self, path):
        self.selected_single_video = path
        self.txt_single_file.setText(os.path.basename(path))
        self.txt_single_file.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #e2e2e9;")
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
        self.txt_batch_in.setText(path)
        self.txt_batch_in.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #e2e2e9;")
        
        supported_exts = ('.mp4', '.avi', '.mov', '.mkv', '.wmv')
        self.batch_video_files = []
        try:
            for item in os.listdir(path):
                full_item = os.path.join(path, item)
                if os.path.isfile(full_item) and item.lower().endswith(supported_exts):
                    self.batch_video_files.append(full_item)
            
            self.lbl_batch_stats.setText(f"{len(self.batch_video_files)} video(s) found in directory.")
            self.log(f"Batch folder scanned. Found {len(self.batch_video_files)} video files.")
            
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
            self.txt_batch_out.setText(out_default)
            self.txt_batch_out.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #e2e2e9;")
            
        self.update_action_states()
        
    def browse_batch_in_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Input Batch Folder", "")
        if path:
            self.set_batch_input_folder(path)
            
    def browse_batch_out_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if path:
            self.selected_batch_output = path
            self.txt_batch_out.setText(path)
            self.txt_batch_out.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #e2e2e9;")
            self.update_action_states()
            
    def browse_combine_out_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Combine Output Folder", "")
        if path:
            self.selected_combine_output_dir = path
            self.txt_combine_out.setText(path)
            self.txt_combine_out.setStyleSheet("background-color: #0b0b0e; border: 1px solid #282833; border-radius: 6px; padding: 8px 10px; color: #e2e2e9;")
            
    # --- Watermark Processing triggers
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
            
        is_batch = self.tabs.currentIndex() == 1
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
        self.lbl_progress.setText("Current Video Progress: 0%")
        
        if is_batch:
            self.lbl_batch_progress.setVisible(True)
            self.batch_progress_bar.setVisible(True)
            self.lbl_batch_progress.setText("Overall Batch Progress: 0%")
        else:
            self.lbl_batch_progress.setVisible(False)
            self.batch_progress_bar.setVisible(False)
            
        self.log("\n====================================")
        self.log(f"Starting watermark removal. Total videos: {len(video_paths)}")
        if is_overwrite:
            self.log("Mode: OVERWRITE in-place (original files will be replaced)")
        else:
            self.log(f"Output destination: {output_dest}")
        
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
        """Called as watermark removal outputs files; feeds them into Combine Gallery."""
        if output_paths:
            self.gallery_widget.add_videos(output_paths)
            self.log(f"✓ Added {len(output_paths)} processed video(s) to Combine Gallery.")
            # If batch or single completed, automatically switch to Combine tab to show workflow
            self.tabs.setCurrentIndex(2)
            
    def on_worker_progress(self, pct):
        self.progress_bar.setValue(pct)
        self.lbl_progress.setText(f"Current Video Progress: {pct}%")
        
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
        
        self.log("\n====================================")
        self.log(message)
        
        if success:
            # Report usage analytics asynchronously
            is_batch = (self.tabs.currentIndex() == 1)
            count = len(self.batch_video_files) if is_batch else 1
            op_type = "watermark_batch" if is_batch else "watermark_single"
            details = f"Batch of {count} videos" if is_batch else os.path.basename(self.selected_single_video or "video")
            license_client.log_usage_async(op_type, count=count, details=details)

            QMessageBox.information(
                self, "Watermark Removal Complete",
                f"{message}\n\nYour processed videos are ready in the 'Combine Clips' gallery."
            )
        else:
            QMessageBox.warning(self, "Process Incomplete", message)
            
    # --- Combine Videos triggers
    def start_combining(self):
        if self.is_processing():
            return
            
        selected_paths = self.gallery_widget.get_selected_video_paths()
        
        # Edge cases check
        if len(selected_paths) == 0:
            QMessageBox.warning(self, "No Videos Selected", "Please select at least 2 videos to combine.")
            return
            
        if len(selected_paths) < 2:
            QMessageBox.warning(self, "Insufficient Videos", "Select at least 2 videos to combine.")
            return
            
        # Verify file presence
        for p in selected_paths:
            if not os.path.exists(p):
                QMessageBox.critical(self, "Missing Video File", f"Cannot combine because video is missing:\n{p}")
                return
                
        # Determine output directory
        if self.selected_combine_output_dir and os.path.exists(self.selected_combine_output_dir):
            out_dir = self.selected_combine_output_dir
        elif self.selected_batch_output and os.path.exists(self.selected_batch_output):
            out_dir = self.selected_batch_output
        else:
            first_dir = os.path.dirname(os.path.abspath(selected_paths[0]))
            out_dir = first_dir
            
        # Generate unique timestamped output file
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_filename = f"combined_{now_str}.mp4"
        out_path = os.path.join(out_dir, out_filename)
        
        # Transition config
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
        
        # UI preparation
        self.progress_bar.setValue(0)
        self.batch_progress_bar.setValue(0)
        self.lbl_progress.setText("Current Step: Initializing...")
        self.lbl_batch_progress.setText("Overall Merge Progress: 0%")
        self.lbl_batch_progress.setVisible(True)
        self.batch_progress_bar.setVisible(True)
        
        self.log("\n====================================")
        self.log(f"Starting Video Combine operation. Selected clips: {len(selected_paths)}")
        for i, p in enumerate(selected_paths, 1):
            self.log(f"  [{i}] {os.path.basename(p)}")
        self.log(f"Transition: {trans_name} ({trans_dur:.1f}s)")
        self.log(f"Output File: {out_path}")
        
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
        self.lbl_progress.setText(f"Current Step: {pct}%")
        
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
        
        self.log("\n====================================")
        self.log(message)
        
        if success and meta and os.path.exists(meta.get("path", "")):
            # Report combine analytics asynchronously
            num_clips = meta.get("video_count", 2)
            out_name = os.path.basename(meta.get("path", "merged.mp4"))
            license_client.log_usage_async("video_combine", count=num_clips, details=f"Combined {num_clips} clips into {out_name}")

            # Show rich Success Dialog
            dlg = MergeSuccessDialog(meta, self)
            dlg.exec()
        elif not success:
            QMessageBox.warning(self, "Combine Error", message)
            
    # --- Universal Cancel
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
            return "🟢 Active Session"
        u = license_client.user_data
        plan = u.get("plan_type", "")
        if plan == "lifetime":
            return "👑 Lifetime License"
        elif plan == "7_days":
            return "⏳ Trial (7 Days)"
        elif plan == "1_month":
            return "⚡ Monthly Plan"
        elif plan == "1_year":
            return "🌟 Annual Plan"
        elif plan == "custom":
            return "🛡️ Custom Plan"
        return "🟢 Active Plan"

    def open_account_dialog(self):
        auth_dlg = AuthDialog(self)
        auth_dlg.tabs.setCurrentIndex(2)  # Switch to Settings / Account tab
        auth_dlg.exec()
        self.license_status_lbl.setText(self._get_license_summary_text())
