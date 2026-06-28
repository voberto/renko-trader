from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class cl_Chart(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(300)
        self.setStyleSheet("background-color: #000000; border: 1px solid #333333;")
        
        # Layout for potential future chart drawing engine
        self.layout_chart = QVBoxLayout(self)
        
        self.lbl_placeholder = QLabel("CHART AREA (V2 ENGINE PENDING)")
        self.lbl_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_placeholder.setStyleSheet("color: #555555; font-weight: bold; font-size: 14pt;")
        
        self.layout_chart.addWidget(self.lbl_placeholder)

    def update_data(self, data):
        """
        Placeholder for when tick/brick data arrives.
        """
        pass