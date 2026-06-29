from PySide6.QtWidgets import QPlainTextEdit
from datetime import datetime

class cl_Logger(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self.setMaximumHeight(250)
        self.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #d4d4d4; 
            font-family: 'Consolas', 'Monaco', monospace; 
            font-size: 10pt;
        """)
        self.append_log("Logger initialized.")

    def append_log(self, message: str):
        """
        Adds a new line to the logger with a timestamp.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        full_message = f"[{timestamp}] {message}"
        self.appendPlainText(full_message)
        
        # Auto-scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())