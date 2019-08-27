from PyQt5 import uic
from PyQt5.QtWidgets import QDialog
import os
import sys
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    __dir__ = sys._MEIPASS   # for pyinstaller
else:
    __dir__ = os.path.dirname(os.path.abspath(__file__))



    
class get_notes(QDialog):
    def __init__(self, init_text = ''):
        self.init_text = init_text
        super().__init__()
        uic.loadUi(os.path.join(__dir__, 'ui', 'Notes.ui'), self)



    def run(self):
        self.plainTextEdit.setPlainText(self.init_text)
        
        ok = self.exec_()
        if ok:
            print(str(self.plainTextEdit.toPlainText()))
            return str(self.plainTextEdit.toPlainText())
        else:
            return None
