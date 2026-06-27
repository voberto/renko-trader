import sys
from PySide6.QtWidgets import QApplication

# Custom modules
from config.config import config_return
from GUI.GUI import Dialog_WinMain


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dict_config = {}
    dict_config = config_return()
    dialog = Dialog_WinMain(dict_config)
    dialog.show()
    sys.exit(app.exec())
