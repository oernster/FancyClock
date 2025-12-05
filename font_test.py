import sys
import os
from PySide6.QtWidgets import QApplication, QLabel

def main():
    if sys.platform == "win32":
        os.environ['QT_QPA_PLATFORM'] = 'windows:fontengine=freetype'
    
    app = QApplication(sys.argv)
    label = QLabel("Hello, World!")
    label.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()