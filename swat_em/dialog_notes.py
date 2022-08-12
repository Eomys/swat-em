from qtpy import uic, QtGui
from qtpy.QtWidgets import QDialog
import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    __dir__ = sys._MEIPASS  # for pyinstaller
else:
    __dir__ = os.path.dirname(os.path.abspath(__file__))


class get_notes(QDialog):
    def __init__(self, init_text=""):
        self.init_text = init_text
        super().__init__()
        uic.loadUi(os.path.join(__dir__, "ui", "Notes.ui"), self)

    def run(self):
        self.plainTextEdit.setPlainText(self.init_text)
        self.plainTextEdit.moveCursor(QtGui.QTextCursor.End)

        ok = self.exec_()
        if ok:
            return str(self.plainTextEdit.toPlainText())
        else:
            return None
