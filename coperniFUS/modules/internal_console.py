from coperniFUS import *
from coperniFUS.modules.module_base import Module


class EmittingStream(pyqtc.QObject):
    """
    Custom stream handler for QTextEdit
    """

    _text_written = pyqtc.pyqtSignal(str)

    def write(self, text):
        self._text_written.emit(str(text).strip())

    def flush(self):
        pass


class InternalConsoleModule(Module):

    FONT_SIZE = 10

    def __init__(self, parent_viewer, **kwargs) -> None:
        super().__init__(parent_viewer, 'internal_console', **kwargs)

        self.console_widget = pyqtw.QTextEdit()
        self.console_widget.setReadOnly(True)
        
        font = pyqtg.QFont("Fira Code", self.FONT_SIZE)
        self.console_widget.setFont(font)
        self.console_widget.setMinimumWidth(425) # for k-Wave output

        # Redirect stdout and stderr to the log widget
        self.log_stream = EmittingStream()
        self.log_stream._text_written.connect(self.append_console)

    def append_console(self, message):
        self.console_widget.append(message)

    # --- Required module attributes ---

    def init_dock(self):
        # Setting up dock layout
        self.dock = pyqtw.QDockWidget('Console', self.parent_viewer)
        self.parent_viewer.addDockWidget(pyqtc.Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.visibilityChanged.connect(self._on_console_dock_visibility_change)
        self.dock_widget = pyqtw.QWidget(self.dock)
        self.dock.setWidget(self.dock_widget)
        self.dock_layout = pyqtw.QGridLayout()
        self.dock_widget.setLayout(self.dock_layout)

        self.dock_layout.addWidget(self.console_widget, 0, 0, 1, 1) # Y, X, w, h

        self.clear_console_btn = pyqtw.QPushButton('Clear console')
        self.clear_console_btn.clicked.connect(self.clear_console)
        self.dock_layout.addWidget(self.clear_console_btn, 1, 0, 1, 1)

    # --- Module specific attributes ---
    
    def clear_console(self):
        self.console_widget.clear()
    
    def _on_console_dock_visibility_change(self, visible):
        if visible:
            sys.stdout = self.log_stream
            sys.stderr = self.log_stream
        else:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
