import os
import cv2
import subprocess
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QSize, QRect, QPoint, QMimeData
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QIcon,
    QCursor, QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QCheckBox, QFrame, QScrollArea, QDialog, QFileDialog, QMessageBox,
    QGridLayout, QSizePolicy, QToolButton, QMenu
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from video_combiner import format_duration, format_file_size, get_media_properties

class CircularOrderBadge(QWidget):
    """
    Renders a circular badge with the order number (1, 2, 3...) in bold white text
    over an attractive vibrant accent background.
    """
    def __init__(self, number=1, size=32, parent=None):
        super().__init__(parent)
        self.number = number
        self.badge_size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
    def set_number(self, num):
        self.number = num
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = (self.badge_size // 2) - 1
        
        # Outer shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 15, 20, 180))
        painter.drawEllipse(center, radius + 1, radius + 1)
        
        # Vibrant purple/indigo circle
        painter.setBrush(QColor(93, 95, 239))
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
        painter.drawEllipse(center, radius, radius)
        
        # Text
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.number))


class VideoGalleryCard(QFrame):
    """
    Visual card representing a processed video in the gallery.
    Displays drag handle, thumbnail, duration pill, filename, resolution, download datetime,
    selection checkbox, order badge, and reorder controls. Supports drag-and-drop.
    """
    selection_changed = pyqtSignal(object, bool) # (card, is_selected)
    move_up_requested = pyqtSignal(object)       # (card)
    move_down_requested = pyqtSignal(object)     # (card)
    remove_requested = pyqtSignal(object)        # (card)
    play_requested = pyqtSignal(str)             # (video_path)
    card_drag_started = pyqtSignal(object)       # (card)
    
    def __init__(self, video_data, parent=None):
        super().__init__(parent)
        self.video_data = video_data  # dict from get_media_properties
        self.is_selected = True
        self.order_index = 1
        self.drag_start_pos = None
        self.is_drag_active = False
        
        self.setObjectName("galleryCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(False)
        
        self.init_ui()
        self.update_style()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)
        
        # 0. Drag Grip Handle
        self.lbl_grip = QLabel("⠿")
        self.lbl_grip.setToolTip("Click and drag to reorder")
        self.lbl_grip.setCursor(Qt.CursorShape.SizeAllCursor)
        self.lbl_grip.setStyleSheet("""
            color: #707085;
            font-size: 20px;
            font-weight: bold;
            padding: 0 4px;
        """)
        main_layout.addWidget(self.lbl_grip)
        
        # 1. Left: Thumbnail container with Badge & Duration overlay
        thumb_container = QWidget()
        thumb_container.setFixedSize(140, 80)
        thumb_layout = QVBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        # Thumbnail Image Label
        self.lbl_thumb = QLabel(thumb_container)
        self.lbl_thumb.setFixedSize(140, 80)
        self.lbl_thumb.setStyleSheet("border-radius: 6px; background-color: #0b0b0e;")
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_thumbnail_image(self.video_data.get("thumbnail"))
        
        # Duration Pill on Thumbnail bottom right
        dur_text = format_duration(self.video_data.get("duration", 0))
        self.lbl_dur = QLabel(dur_text, thumb_container)
        self.lbl_dur.setStyleSheet("""
            background-color: rgba(15, 15, 20, 0.85);
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        """)
        self.lbl_dur.adjustSize()
        self.lbl_dur.move(140 - self.lbl_dur.width() - 6, 80 - self.lbl_dur.height() - 6)
        
        # Selection Order Badge in Top-Left of thumbnail
        self.order_badge = CircularOrderBadge(number=self.order_index, size=28, parent=thumb_container)
        self.order_badge.move(6, 6)
        self.order_badge.setVisible(self.is_selected)
        
        main_layout.addWidget(thumb_container)
        
        # 2. Middle: Metadata Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 2, 0, 2)
        
        # File Name
        self.lbl_name = QLabel(self.video_data.get("name", "video.mp4"))
        self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        self.lbl_name.setWordWrap(False)
        info_layout.addWidget(self.lbl_name)
        
        # Technical details & Download/Creation Datetime
        w = self.video_data.get("width", 0)
        h = self.video_data.get("height", 0)
        fps = int(round(self.video_data.get("fps", 30)))
        sz = format_file_size(self.video_data.get("size_bytes", 0))
        dt_str = self.video_data.get("datetime_str", "")
        dt_display = f"  •  📅 {dt_str}" if dt_str else ""
        
        self.lbl_details = QLabel(f"{w}x{h} @ {fps}fps  •  {sz}{dt_display}")
        self.lbl_details.setStyleSheet("color: #a0a0ba; font-size: 12px;")
        info_layout.addWidget(self.lbl_details)
        
        # Status Tag & Preview
        h_status = QHBoxLayout()
        h_status.setSpacing(6)
        
        self.lbl_status = QLabel("✓ Ready to Merge")
        self.lbl_status.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: bold;")
        h_status.addWidget(self.lbl_status)
        
        btn_quick_play = QPushButton("▶ Preview")
        btn_quick_play.setFixedSize(72, 24)
        btn_quick_play.setStyleSheet("""
            QPushButton {
                background-color: #212129;
                border: 1px solid #3a3a4c;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                color: #e2e2e9;
            }
            QPushButton:hover {
                background-color: #5d5fef;
                color: white;
                border-color: #5d5fef;
            }
        """)
        btn_quick_play.clicked.connect(lambda: self.play_requested.emit(self.video_data.get("path")))
        h_status.addWidget(btn_quick_play)
        h_status.addStretch()
        
        info_layout.addLayout(h_status)
        main_layout.addLayout(info_layout, 1)
        
        # 3. Right: Reorder & Selection controls
        right_ctrls = QVBoxLayout()
        right_ctrls.setSpacing(6)
        right_ctrls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Checkbox
        self.chk_select = QCheckBox("Select")
        self.chk_select.setChecked(self.is_selected)
        self.chk_select.setStyleSheet("font-weight: bold; color: #e2e2e9;")
        self.chk_select.toggled.connect(self.on_checkbox_toggled)
        right_ctrls.addWidget(self.chk_select)
        
        # Up / Down buttons
        h_arrows = QHBoxLayout()
        h_arrows.setSpacing(4)
        
        self.btn_up = QToolButton()
        self.btn_up.setText("▲")
        self.btn_up.setToolTip("Move Up")
        self.btn_up.setFixedSize(28, 26)
        self.btn_up.setStyleSheet("""
            QToolButton {
                background-color: #212129;
                border: 1px solid #30303e;
                border-radius: 4px;
                color: #e2e2e9;
                font-size: 11px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #353545;
                border-color: #5d5fef;
            }
        """)
        self.btn_up.clicked.connect(lambda: self.move_up_requested.emit(self))
        h_arrows.addWidget(self.btn_up)
        
        self.btn_down = QToolButton()
        self.btn_down.setText("▼")
        self.btn_down.setToolTip("Move Down")
        self.btn_down.setFixedSize(28, 26)
        self.btn_down.setStyleSheet("""
            QToolButton {
                background-color: #212129;
                border: 1px solid #30303e;
                border-radius: 4px;
                color: #e2e2e9;
                font-size: 11px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #353545;
                border-color: #5d5fef;
            }
        """)
        self.btn_down.clicked.connect(lambda: self.move_down_requested.emit(self))
        h_arrows.addWidget(self.btn_down)
        
        # Remove button
        self.btn_remove = QToolButton()
        self.btn_remove.setText("✕")
        self.btn_remove.setToolTip("Remove from list")
        self.btn_remove.setFixedSize(28, 26)
        self.btn_remove.setStyleSheet("""
            QToolButton {
                background-color: #212129;
                border: 1px solid #30303e;
                border-radius: 4px;
                color: #ea5656;
                font-size: 11px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #db4444;
                color: white;
            }
        """)
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        h_arrows.addWidget(self.btn_remove)
        
        right_ctrls.addLayout(h_arrows)
        main_layout.addLayout(right_ctrls)
        
    def set_thumbnail_image(self, thumbnail_rgb):
        if thumbnail_rgb is not None:
            h, w, c = thumbnail_rgb.shape
            bytes_per_line = c * w
            q_img = QImage(thumbnail_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img).scaled(
                140, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
            )
            cx = (pixmap.width() - 140) // 2
            cy = (pixmap.height() - 80) // 2
            cropped = pixmap.copy(cx, cy, 140, 80)
            self.lbl_thumb.setPixmap(cropped)
        else:
            self.lbl_thumb.setText("🎬 Video")
            
    def set_order_index(self, index):
        self.order_index = index
        self.order_badge.set_number(index)
        self.order_badge.setVisible(self.is_selected)
        
    def set_selected(self, selected, trigger_signal=True):
        self.is_selected = selected
        self.chk_select.blockSignals(True)
        self.chk_select.setChecked(selected)
        self.chk_select.blockSignals(False)
        self.order_badge.setVisible(selected)
        self.update_style()
        if trigger_signal:
            self.selection_changed.emit(self, selected)
            
    def on_checkbox_toggled(self, checked):
        self.is_selected = checked
        self.order_badge.setVisible(checked)
        self.update_style()
        self.selection_changed.emit(self, checked)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_start_pos is not None:
            distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if distance >= 8:
                # Start Drag-and-Drop
                self.start_card_drag()
                return
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        # Click on card toggles selection if not clicked on buttons/grip
        child = self.childAt(event.pos())
        if child not in [self.chk_select, self.btn_up, self.btn_down, self.btn_remove, self.lbl_grip] and not isinstance(child, QPushButton):
            self.set_selected(not self.is_selected)
        super().mouseReleaseEvent(event)
        
    def start_card_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-dola-card-path", self.video_data["path"].encode("utf-8"))
        drag.setMimeData(mime)
        
        # Render semi-transparent pixmap of card for drag feedback
        pixmap = self.grab()
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 180))
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, 25))
        
        self.card_drag_started.emit(self)
        drag.exec(Qt.DropAction.MoveAction)
        
    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame#galleryCard {
                    background-color: #161622;
                    border: 2px solid #5d5fef;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#galleryCard {
                    background-color: #121217;
                    border: 1px solid #282833;
                    border-radius: 8px;
                }
                QFrame#galleryCard:hover {
                    background-color: #181820;
                    border-color: #38384a;
                }
            """)


class GalleryBoardWidget(QWidget):
    """
    Board container that hosts cards and handles Drag-and-Drop reordering.
    """
    card_reordered = pyqtSignal(int, int) # (from_index, to_index)
    files_dropped = pyqtSignal(list)      # (list_of_file_paths)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.cards_layout = QVBoxLayout(self)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        
        self.drop_indicator_idx = -1
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-dola-card-path") or event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-dola-card-path"):
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasFormat("application/x-dola-card-path"):
            card_path = event.mimeData().data("application/x-dola-card-path").data().decode("utf-8")
            
            # Find source card index
            gallery_widget = self.parentWidget()
            while gallery_widget and not isinstance(gallery_widget, VideoGalleryWidget):
                gallery_widget = gallery_widget.parentWidget()
                
            if gallery_widget:
                src_idx = -1
                for idx, c in enumerate(gallery_widget.cards):
                    if c.video_data["path"] == card_path:
                        src_idx = idx
                        break
                        
                if src_idx != -1:
                    # Calculate target insertion index based on drop position y
                    drop_y = event.position().y()
                    target_idx = len(gallery_widget.cards) - 1
                    
                    for idx, c in enumerate(gallery_widget.cards):
                        c_rect = c.geometry()
                        c_mid = c_rect.y() + c_rect.height() // 2
                        if drop_y < c_mid:
                            target_idx = idx
                            break
                            
                    target_idx = max(0, min(target_idx, len(gallery_widget.cards) - 1))
                    gallery_widget.move_card_to_index(src_idx, target_idx)
                    event.acceptProposedAction()
                    return
                    
        elif event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()


class VideoGalleryWidget(QWidget):
    """
    Gallery container displaying all processed videos.
    Default sorted by download/creation datetime.
    Supports direct drag-and-drop board reordering and automatic order badges.
    """
    order_changed = pyqtSignal()
    play_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.sort_ascending = True
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header controls bar
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 4)
        h_layout.setSpacing(8)
        
        self.lbl_stats = QLabel("0 videos in gallery (0 selected)")
        self.lbl_stats.setStyleSheet("font-weight: bold; color: #e2e2e9; font-size: 13px;")
        h_layout.addWidget(self.lbl_stats)
        h_layout.addStretch()
        
        # Sort by Date button
        self.btn_sort_date = QPushButton("📅 Sort by Date")
        self.btn_sort_date.setToolTip("Sort videos by download/creation datetime")
        self.btn_sort_date.setStyleSheet("background-color: #212129; border: 1px solid #3a3a4c; padding: 4px 10px; font-size: 12px;")
        self.btn_sort_date.clicked.connect(self.toggle_sort_by_date)
        h_layout.addWidget(self.btn_sort_date)
        
        btn_select_all = QPushButton("Select All")
        btn_select_all.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        btn_select_all.clicked.connect(self.select_all)
        h_layout.addWidget(btn_select_all)
        
        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.setStyleSheet("padding: 4px 10px; font-size: 12px;")
        btn_deselect_all.clicked.connect(self.deselect_all)
        h_layout.addWidget(btn_deselect_all)
        
        btn_add_more = QPushButton("+ Add Videos...")
        btn_add_more.setStyleSheet("background-color: #212129; border: 1px solid #3a3a4c; padding: 4px 10px; font-size: 12px;")
        btn_add_more.clicked.connect(self.browse_add_videos)
        h_layout.addWidget(btn_add_more)
        
        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("background-color: #212129; border: 1px solid #3a3a4c; color: #ea5656; padding: 4px 10px; font-size: 12px;")
        btn_clear.clicked.connect(self.clear_gallery)
        h_layout.addWidget(btn_clear)
        
        layout.addWidget(header)
        
        # Drag & Drop Helper Hint Banner
        lbl_hint = QLabel("💡 Tip: Videos are automatically sorted by download datetime. Drag & drop cards on the board to set custom merge order.")
        lbl_hint.setStyleSheet("color: #a0a0ba; font-size: 11px; padding: 2px 4px;")
        layout.addWidget(lbl_hint)
        
        # Scroll area for cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #282833; border-radius: 8px; background-color: #0b0b0e; }")
        
        # Gallery Board with Drag and Drop Support
        self.board = GalleryBoardWidget()
        self.board.files_dropped.connect(self.add_videos)
        self.cards_layout = self.board.cards_layout
        
        self.scroll_area.setWidget(self.board)
        layout.addWidget(self.scroll_area)
        
    def add_video(self, video_path):
        """Adds a single video to the gallery."""
        for c in self.cards:
            if os.path.abspath(c.video_data["path"]) == os.path.abspath(video_path):
                return
                
        try:
            meta = get_media_properties(video_path)
            card = VideoGalleryCard(meta)
            card.selection_changed.connect(self.on_card_selection_changed)
            card.move_up_requested.connect(self.move_card_up)
            card.move_down_requested.connect(self.move_card_down)
            card.remove_requested.connect(self.remove_card)
            card.play_requested.connect(lambda p: self.play_requested.emit(p))
            
            self.cards_layout.insertWidget(len(self.cards), card)
            self.cards.append(card)
        except Exception as e:
            print(f"Failed to add video to gallery {video_path}: {e}")
            
    def add_videos(self, video_paths):
        """Adds multiple videos and applies default sorting by download/creation datetime."""
        for p in video_paths:
            self.add_video(p)
        # Apply default datetime sort
        self.sort_cards_by_date(ascending=True)
        self.recalc_badges()
        
    def sort_cards_by_date(self, ascending=True):
        """Sorts the cards by download/creation timestamp (oldest first by default)."""
        self.cards.sort(key=lambda c: c.video_data.get("timestamp", 0), reverse=not ascending)
        # Re-insert in layout in sorted order
        for idx, card in enumerate(self.cards):
            self.cards_layout.removeWidget(card)
            self.cards_layout.insertWidget(idx, card)
        self.recalc_badges()
        
    def toggle_sort_by_date(self):
        """Toggles between earliest first and newest first."""
        self.sort_ascending = not self.sort_ascending
        order_name = "Earliest First" if self.sort_ascending else "Latest First"
        self.btn_sort_date.setText(f"📅 Date ({order_name})")
        self.sort_cards_by_date(ascending=self.sort_ascending)
        
    def move_card_to_index(self, from_idx, to_idx):
        """Moves a card from from_idx to to_idx in the list and layout (used by board Drag-and-Drop)."""
        if from_idx == to_idx or from_idx < 0 or from_idx >= len(self.cards) or to_idx < 0 or to_idx >= len(self.cards):
            return
            
        card = self.cards.pop(from_idx)
        self.cards.insert(to_idx, card)
        
        # Re-layout cards
        for idx, c in enumerate(self.cards):
            self.cards_layout.removeWidget(c)
            self.cards_layout.insertWidget(idx, c)
            
        self.recalc_badges()
        
    def browse_add_videos(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files to Add", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        if paths:
            self.add_videos(paths)
            
    def on_card_selection_changed(self, card, is_selected):
        self.recalc_badges()
        
    def move_card_up(self, card):
        idx = self.cards.index(card)
        if idx > 0:
            self.move_card_to_index(idx, idx - 1)
            
    def move_card_down(self, card):
        idx = self.cards.index(card)
        if idx < len(self.cards) - 1:
            self.move_card_to_index(idx, idx + 1)
            
    def remove_card(self, card):
        if card in self.cards:
            self.cards.remove(card)
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            self.recalc_badges()
            
    def clear_gallery(self):
        for card in list(self.cards):
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()
        self.recalc_badges()
        
    def select_all(self):
        for c in self.cards:
            c.set_selected(True, trigger_signal=False)
        self.recalc_badges()
        
    def deselect_all(self):
        for c in self.cards:
            c.set_selected(False, trigger_signal=False)
        self.recalc_badges()
        
    def recalc_badges(self):
        """Recalculates 1, 2, 3... order numbers for all selected cards in current sequence."""
        selected_count = 0
        total_duration = 0
        
        current_num = 1
        for card in self.cards:
            if card.is_selected:
                card.set_order_index(current_num)
                current_num += 1
                selected_count += 1
                total_duration += card.video_data.get("duration", 0)
            else:
                card.order_badge.setVisible(False)
                
        dur_str = format_duration(total_duration)
        self.lbl_stats.setText(f"{len(self.cards)} videos in gallery  •  {selected_count} selected to merge (Total: {dur_str})")
        self.order_changed.emit()
        
    def get_selected_video_paths(self):
        """Returns the ordered list of file paths for all selected cards."""
        return [c.video_data["path"] for c in self.cards if c.is_selected]


class VideoPlayerDialog(QDialog):
    """
    Dedicated video player dialog with seek bar, play/pause, volume control,
    and formatted playback timestamps.
    """
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setWindowTitle(f"Video Preview - {os.path.basename(video_path)}")
        self.resize(800, 540)
        
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        
        self.init_ui()
        self.load_video(video_path)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Video Widget
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 6px;")
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget, 1)
        
        # Controls Bar
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet("background-color: #16161c; border-radius: 8px; padding: 6px;")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)
        ctrl_layout.setSpacing(4)
        
        # Timeline Seek Slider + Time Label
        time_layout = QHBoxLayout()
        
        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 0)
        self.slider_seek.sliderMoved.connect(self.set_position)
        time_layout.addWidget(self.slider_seek, 1)
        
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #a0a0ba; font-size: 12px; font-weight: 500;")
        time_layout.addWidget(self.lbl_time)
        
        ctrl_layout.addLayout(time_layout)
        
        # Buttons Row: Play/Pause, Restart, Volume, Close
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setFixedWidth(80)
        self.btn_play.setStyleSheet("background-color: #5d5fef; color: white; font-weight: bold;")
        self.btn_play.clicked.connect(self.toggle_play)
        btn_row.addWidget(self.btn_play)
        
        self.btn_restart = QPushButton("⏮ Replay")
        self.btn_restart.setFixedWidth(80)
        self.btn_restart.clicked.connect(self.restart_video)
        btn_row.addWidget(self.btn_restart)
        
        btn_row.addSpacing(16)
        
        # Volume
        btn_row.addWidget(QLabel("🔊 Volume:"))
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setFixedWidth(100)
        self.slider_vol.valueChanged.connect(self.set_volume)
        btn_row.addWidget(self.slider_vol)
        
        btn_row.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        
        ctrl_layout.addLayout(btn_row)
        layout.addWidget(ctrl_card)
        
        # Connect media player signals
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        
    def load_video(self, path):
        self.player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self.player.play()
        self.btn_play.setText("⏸ Pause")
        
    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶ Play")
        else:
            self.player.play()
            self.btn_play.setText("⏸ Pause")
            
    def restart_video(self):
        self.player.setPosition(0)
        self.player.play()
        self.btn_play.setText("⏸ Pause")
        
    def set_position(self, position):
        self.player.setPosition(position)
        
    def set_volume(self, value):
        self.audio_output.setVolume(value / 100.0)
        
    def on_position_changed(self, pos):
        if not self.slider_seek.isSliderDown():
            self.slider_seek.setValue(pos)
        self.update_time_label()
        
    def on_duration_changed(self, dur):
        self.slider_seek.setRange(0, dur)
        self.update_time_label()
        
    def update_time_label(self):
        curr_sec = self.player.position() / 1000.0
        tot_sec = self.player.duration() / 1000.0
        self.lbl_time.setText(f"{format_duration(curr_sec)} / {format_duration(tot_sec)}")
        
    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)


class MergeSuccessDialog(QDialog):
    """
    Dialog displayed when video merging completes successfully.
    Shows final video metadata and buttons: Preview, Open Folder, Combine Again.
    """
    def __init__(self, output_metadata, parent=None):
        super().__init__(parent)
        self.meta = output_metadata
        self.setWindowTitle("✓ Final Video Ready")
        self.resize(520, 360)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header Badge
        header_card = QFrame()
        header_card.setStyleSheet("background-color: rgba(74, 222, 128, 0.1); border: 1px solid rgba(74, 222, 128, 0.3); border-radius: 8px; padding: 10px;")
        h_box = QHBoxLayout(header_card)
        lbl_icon = QLabel("✓")
        lbl_icon.setStyleSheet("color: #4ade80; font-size: 24px; font-weight: bold;")
        h_box.addWidget(lbl_icon)
        
        title_box = QVBoxLayout()
        lbl_title = QLabel("Final Video Ready!")
        lbl_title.setStyleSheet("color: #4ade80; font-size: 16px; font-weight: bold;")
        lbl_sub = QLabel("All clips have been smoothly combined with extra smooth fade transitions.")
        lbl_sub.setStyleSheet("color: #a0a0ba; font-size: 11px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        h_box.addLayout(title_box)
        layout.addWidget(header_card)
        
        # Details Table
        details_box = QFrame()
        details_box.setStyleSheet("background-color: #16161c; border: 1px solid #282833; border-radius: 8px; padding: 12px;")
        grid = QGridLayout(details_box)
        grid.setSpacing(10)
        
        grid.addWidget(QLabel("Output File:"), 0, 0)
        lbl_file = QLabel(os.path.basename(self.meta.get("path", "combined_video.mp4")))
        lbl_file.setStyleSheet("color: #ffffff; font-weight: bold;")
        grid.addWidget(lbl_file, 0, 1)
        
        grid.addWidget(QLabel("Duration:"), 1, 0)
        grid.addWidget(QLabel(format_duration(self.meta.get("duration", 0))), 1, 1)
        
        grid.addWidget(QLabel("Resolution:"), 2, 0)
        grid.addWidget(QLabel(f"{self.meta.get('width', 0)} x {self.meta.get('height', 0)} @ {int(round(self.meta.get('fps', 30)))} fps"), 2, 1)
        
        grid.addWidget(QLabel("File Size:"), 3, 0)
        grid.addWidget(QLabel(format_file_size(self.meta.get("size_bytes", 0))), 3, 1)
        
        layout.addWidget(details_box)
        
        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_preview = QPushButton("▶ Preview Video")
        btn_preview.setStyleSheet("background-color: #5d5fef; color: white; font-weight: bold; padding: 10px 16px;")
        btn_preview.clicked.connect(self.preview_video)
        btn_layout.addWidget(btn_preview)
        
        btn_folder = QPushButton("📁 Open Folder")
        btn_folder.setStyleSheet("background-color: #212129; border: 1px solid #30303e; font-weight: bold; padding: 10px 16px;")
        btn_folder.clicked.connect(self.open_folder)
        btn_layout.addWidget(btn_folder)
        
        btn_again = QPushButton("Combine Again")
        btn_again.setStyleSheet("background-color: #212129; border: 1px solid #30303e; padding: 10px 16px;")
        btn_again.clicked.connect(self.accept)
        btn_layout.addWidget(btn_again)
        
        layout.addLayout(btn_layout)
        
    def preview_video(self):
        dlg = VideoPlayerDialog(self.meta.get("path"), self)
        dlg.exec()
        
    def open_folder(self):
        path = self.meta.get("path")
        if os.path.exists(path):
            folder = os.path.dirname(os.path.abspath(path))
            if os.name == 'nt':
                subprocess.Popen(f'explorer /select,"{os.path.abspath(path)}"')
            else:
                subprocess.Popen(['xdg-open', folder])
