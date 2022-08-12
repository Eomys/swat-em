from qtpy import uic
from qtpy import QtGui
from qtpy.QtWidgets import QTreeWidgetItem, QDialog, QFileDialog
from swat_em import datamodel, project
import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    __dir__ = sys._MEIPASS  # for pyinstaller
else:
    __dir__ = os.path.dirname(os.path.abspath(__file__))


class import_winding(QDialog):
    """
    Dialog for importing windings from a file
    """

    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(__dir__, "ui", "ImportWinding.ui"), self)
        self.ButtonCheckAll.clicked.connect(self.check_all)
        self.ButtonCheckNone.clicked.connect(self.check_none)

    def create_list(self, filename):

        self.models = project()
        self.models.load_from_file(filename)

        self.items = []
        for k in range(self.models.get_num_models()):
            data = self.models.get_model_by_index(k)
            bc, txt = data.get_basic_characteristics()

            # title
            font = QtGui.QFont()
            font.setBold(True)

            self.items.append(QTreeWidgetItem([data.title]))
            self.items[-1].setFont(0, font)

            # Infos
            font = QtGui.QFont()
            font.setItalic(True)

            child = QTreeWidgetItem(
                [
                    "Q: {}, 2p: {}, m: {}".format(
                        data.get_num_slots(),
                        2 * data.get_num_polepairs(),
                        data.get_num_phases(),
                    )
                ]
            )
            child.setFont(0, font)
            self.items[-1].addChild(child)

            l = [str(round(k, 3)) for k in bc["kw1"]]

            child = QTreeWidgetItem(["Winding factor kw1: {}".format(", ".join(l))])
            child.setFont(0, font)
            self.items[-1].addChild(child)

            child = QTreeWidgetItem(["Notes: " + data.get_notes()])
            child.setFont(0, font)
            self.items[-1].addChild(child)

            self.items[-1].setCheckState(0, False)
            self.treeWidget.addTopLevelItem(self.items[-1])

        self.treeWidget.expandToDepth(0)

    def check_all(self):
        for item in self.items:
            item.setCheckState(0, True)

    def check_none(self):
        for item in self.items:
            item.setCheckState(0, False)

    def run(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open winding file", "", "Winding Files (*.wdg)", options=options
        )
        if not filename:
            return None
        self.create_list(filename)
        ok = self.exec_()
        if ok:
            data = []
            for i, item in enumerate(self.items):
                if item.checkState(0):
                    data.append(self.models.get_model_by_index(i))
            return data
        else:
            return None
