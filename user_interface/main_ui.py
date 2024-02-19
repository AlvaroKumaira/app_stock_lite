import logging
import os
from datetime import datetime
from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QWidget, QFileDialog
from PyQt5.QtCore import QPropertyAnimation, Qt, QPoint
from .design import Ui_MainWindow
from .logic import BuscaLogic

logger = logging.getLogger(__name__)


class MainWindowLogic(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.create_df_thread = None
        self.update_excel_thread = None
        self.update_inv_thread = None
        self.setupUi(self)
        self.view.setCurrentIndex(0)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._dragging = False
        self._drag_position = QPoint()
        self.search_logic = BuscaLogic(self)

        self.progressBar.hide()
        self.progress_sug.hide()
        self.progressBar_search.hide()
        self.progressBar_2.hide()

        # Define a dictionary mapping buttons to view indexes
        button_to_view = {
            self.search_button: 4
        }

        # Connect each button to the switch_view function
        for button, view_index in button_to_view.items():
            button.clicked.connect(lambda _, v=view_index: self.switch_view(v))

        # Connect other buttons normally
        self.close_button.clicked.connect(self.close)
        self.minimize_button.clicked.connect(self.showMinimized)

        # Define the drag logic
        self.utility_frame.mousePressEvent = self.utility_frame_mousePressEvent
        self.utility_frame.mouseMoveEvent = self.utility_frame_mouseMoveEvent
        self.utility_frame.mouseReleaseEvent = self.utility_frame_mouseReleaseEvent

    def switch_view(self, index):
        self.view.setCurrentIndex(index)

    def utility_frame_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def utility_frame_mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_position)
            event.accept()

    def utility_frame_mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()
