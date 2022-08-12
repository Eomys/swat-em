# -*- coding: utf-8 -*-

from qtpy import uic
from qtpy.QtWidgets import QDialog, QApplication, QMessageBox, QTableWidgetItem
from qtpy.QtGui import QIntValidator
from qtpy import QtGui
from qtpy import QtCore

#  from qtpy.QtCore import Qt
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from swat_em import wdggenerator
from swat_em import datamodel
from swat_em.config import config, get_phase_color

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    __dir__ = sys._MEIPASS  # for pyinstaller
else:
    __dir__ = os.path.dirname(os.path.abspath(__file__))


class NewWinding(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(__dir__, "ui", "choose_generator.ui"), self)
        self.generator = None

        self.Button_EditWindingLayout.clicked.connect(lambda: self.ret(generator=0))
        self.Button_GenerateAutomatically.clicked.connect(lambda: self.ret(generator=1))
        self.Button_FindByTable.clicked.connect(lambda: self.ret(generator=2))

    def run(self):
        ok = self.exec_()
        if ok:
            return self.generator
        else:
            return None

    def ret(self, generator):
        """saves the choosen generator and say "ok" to the dialog"""
        self.generator = generator
        self.accept()


class GenWinding2(QDialog):
    def __init__(self):
        super().__init__()

        # Set up the user interface from Designer.
        uic.loadUi(os.path.join(__dir__, "ui", "GenWinding2.ui"), self)
        self.setWindowTitle("Generate winding")

        self.radioButton_slayer.toggled.connect(
            self.change_layers
        )  # disable lineEdit for single phase windings

        # update 'w' and update winding
        self.spinBox_Q.valueChanged.connect(self.QmP_changed)
        self.spinBox_P.valueChanged.connect(self.QmP_changed)
        self.spinBox_m.valueChanged.connect(self.QmP_changed)
        self.spinBox_empty_slots.valueChanged.connect(self.QmP_changed)

        # update winding
        self.radioButton_slayer.toggled.connect(self.update)
        self.spinBox_w.valueChanged.connect(self.update)

        self.update()  # calc initial winding

    def change_layers(self):
        """
        disable lineEdit for single phase windings
        """
        if self.radioButton_slayer.isChecked():
            self.spinBox_w.setEnabled(False)
        else:
            self.spinBox_w.setEnabled(True)

    def QmP_changed(self):
        Q = self.spinBox_Q.value()
        P = self.spinBox_P.value()
        m = self.spinBox_m.value()
        w = Q // P  # take smaller value (integer div.)
        if w <= 0:
            w = 1
        self.spinBox_w.setValue(w)
        self.update()

    def update(self):
        self.Q = self.spinBox_Q.value()
        self.P = self.spinBox_P.value()
        self.m = self.spinBox_m.value()
        self.w = self.spinBox_w.value()
        Qes = self.spinBox_empty_slots.value()

        if self.radioButton_slayer.isChecked():
            self.layers = 1
        elif self.radioButton_dlayer.isChecked():
            self.layers = 2

        self.table = self.tableWindingLayout
        self.table.clear()
        self.textBrowser_wdginfo.clear()

        self.data = datamodel()
        self.data.set_machinedata(Q=self.Q, m=self.m, p=self.P / 2)
        ret = wdggenerator.genwdg(self.Q, self.P, self.m, self.w, self.layers, Qes)
        if ret is None:
            return
        if ret["valid"] == False:
            return

        self.data.set_phases(S=ret["phases"], w=ret["wstep"])
        self.data.set_valid(ret["valid"], ret["error"], ret["info"])
        self.data.set_num_empty_slots(ret["Qes"])
        bc, bc_str = self.data.get_basic_characteristics()
        self.textBrowser_wdginfo.setHtml(bc_str)

        if bc["sym"] and self.data.generator_info["valid"]:
            self.table.setRowCount(self.layers)
            self.table.setColumnCount(self.data.get_num_slots())

            l, ls, lcol = self.data.get_layers()
            for k1 in range(np.shape(l)[0]):
                for k2 in range(np.shape(l)[1]):
                    self.table.setItem(k1, k2, QTableWidgetItem(ls[k1, k2]))
                    item = self.table.item(k1, k2)
                    if item:
                        item.setBackground(QtGui.QColor(lcol[k1, k2]))
                    self.table.item(k1, k2).setFlags(
                        QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                    )

            for k1 in range(self.data.get_num_slots()):
                #  self.table.resizeColumnToContents(k1)
                self.table.setColumnWidth(k1, 25)

    def run(self):
        ok = self.exec_()
        if ok:
            if self.radioButton_overwrite_winding.isChecked():
                overwrite = True
            else:
                overwrite = False
            ret = {
                "Q": self.Q,
                "P": self.P,
                "m": self.m,
                "w": self.w,
                "layers": self.layers,
                "overwrite": overwrite,
                "Qes": self.data.get_num_empty_slots(),
            }
            return ret
        else:
            return None


class GenWindingCombinations(QDialog):
    def __init__(self):
        super().__init__()

        uic.loadUi(os.path.join(__dir__, "ui", "GenCombinations.ui"), self)
        self.setWindowTitle("Generate windings per table")

        self.colorlabel1.setStyleSheet("background-color:#ADD8E6;")
        self.colorlabel2.setStyleSheet("background-color:#E6C3AD;")
        self.colorlabel3.setStyleSheet("background-color:#BCFFBC;")
        self.colorlabel4.setStyleSheet("background-color:#E9AEE2;")

        # update 'w' and update winding
        self.spinBox_Q1.valueChanged.connect(self.generate)
        self.spinBox_Q2.valueChanged.connect(self.generate)
        self.spinBox_P1.valueChanged.connect(self.generate)
        self.spinBox_P2.valueChanged.connect(self.generate)
        self.spinBox_m.valueChanged.connect(self.generate)
        self.radioButton_slayer.toggled.connect(self.generate)
        self.checkBox_toothcoil.toggled.connect(self.generate)
        self.checkBox_empty_slots.toggled.connect(self.generate)

        self.tableCombinations.itemSelectionChanged.connect(self.combination_selected)

        # Fill combobox
        self.comboBox_plotval.addItems(
            [
                "kw1 (winding factor)",
                "q (slots per pole per phase)",
                "t (symmetry)",
                "a (parallel circuit)",
                "lcm(Q,2p) (least common multiple)",
                "r1 (first mode of radial force)",
                "sigma_d (double linked leakage)",
            ]
        )
        self.comboBox_plotval.currentIndexChanged.connect(self.update_table)
        #  self.generate()

    def generate(self):
        """
        Generate possible winding layout for different slot/pole combinations
        """
        self.Q1 = self.spinBox_Q1.value()
        self.Q2 = self.spinBox_Q2.value()
        self.P1 = self.spinBox_P1.value()
        self.P2 = self.spinBox_P2.value()
        self.m = self.spinBox_m.value()
        if self.checkBox_toothcoil.isChecked():
            wstep = 1
        else:
            wstep = -1
        if self.checkBox_empty_slots.isChecked():
            empty_slots = -1
        else:
            empty_slots = 0

        if self.radioButton_slayer.isChecked():
            self.layers = 1
        elif self.radioButton_dlayer.isChecked():
            self.layers = 2

        self.Qlist = []
        for k in range(self.Q1, self.Q2 + 1, 1):
            if k % self.m == 0:
                self.Qlist.append(k)
        #  self.Qlist = list(range(self.Q1, self.Q2+1, self.m))
        self.Plist = list(range(self.P1, self.P2 + 1, 2))

        self.data = []
        for iQ, kQ in enumerate(self.Qlist):
            self.data.append([])
            for iP, kP in enumerate(self.Plist):
                d = datamodel()
                d.set_machinedata(Q=kQ, m=self.m, p=kP / 2)
                ret = wdggenerator.genwdg(
                    kQ, kP, self.m, wstep, self.layers, empty_slots
                )
                if ret:
                    if wstep == 1 and ret["wstep"] != 1:
                        d.set_valid(False, "", "")
                    else:
                        d.set_phases(S=ret["phases"], w=ret["wstep"])
                        d.set_valid(ret["valid"], ret["error"], ret["info"])
                        d.set_num_empty_slots(ret["Qes"])
                        bc, bc_str = d.get_basic_characteristics()

                else:
                    d.set_valid(False, "", "")
                self.data[iQ].append(d)
        self.update_table()

    def update_table(self):
        self.table = self.tableCombinations
        self.table.clear()

        self.table.setRowCount(len(self.Qlist))
        self.table.setColumnCount(len(self.Plist))

        for i in range(len(self.Plist)):
            table_header_item = QTableWidgetItem("2p=" + str(self.Plist[i]))
            myFont = QtGui.QFont()
            myFont.setBold(True)
            table_header_item.setFont(myFont)
            self.table.setHorizontalHeaderItem(i, table_header_item)

        for i in range(len(self.Qlist)):
            table_header_item = QTableWidgetItem("Q=" + str(self.Qlist[i]))
            myFont = QtGui.QFont()
            myFont.setBold(True)
            table_header_item.setFont(myFont)
            self.table.setVerticalHeaderItem(i, table_header_item)

        for iQ, kQ in enumerate(self.Qlist):
            self.data.append([])
            for iP, kP in enumerate(self.Plist):
                if (
                    self.data[iQ][iP].generator_info["valid"]
                    and self.data[iQ][iP].results["basic_char"]["sym"]
                ):
                    bc = self.data[iQ][iP].results["basic_char"]
                    if bc["kw1"][0] > 0.01:
                        idx = self.comboBox_plotval.currentIndex()
                        if idx == 0:
                            txt = str(round(bc["kw1"][0], 3))
                        elif idx == 1:
                            txt = str(bc["q"])
                        elif idx == 2:
                            txt = str(bc["t"])
                        elif idx == 3:
                            txt = str(bc["a"])
                        elif idx == 4:
                            txt = str(bc["lcmQP"])
                        elif idx == 5:
                            txt = str(bc["r"][0])
                        elif idx == 6:
                            txt = str(round(bc["sigma_d"], 3))

                        self.table.setItem(iQ, iP, QTableWidgetItem(txt))
                        q = bc["q"]

                        if self.data[iQ][iP].get_coilspan() == 1:
                            self.table.item(iQ, iP).setBackground(
                                QtGui.QColor("#ADD8E6")
                            )
                        elif q.denominator == 1:
                            self.table.item(iQ, iP).setBackground(
                                QtGui.QColor("#E6C3AD")
                            )
                        else:
                            self.table.item(iQ, iP).setBackground(
                                QtGui.QColor("#BCFFBC")
                            )
                        if self.data[iQ][iP].get_num_empty_slots() != 0:
                            self.table.item(iQ, iP).setBackground(
                                QtGui.QColor("#E9AEE2")
                            )
                        self.table.item(iQ, iP).setFlags(
                            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                        )  # note editable

        self.table.resizeColumnsToContents()

        # reset table with winding layout because there is noting choosed
        self.tableWindingLayout.clear()
        self.tableWindingLayout.setRowCount(0)
        self.tableWindingLayout.setColumnCount(0)

    def combination_selected(self):
        """
        user selected a cell/winding combination
        """
        sel = self.tableCombinations.selectedIndexes()
        if sel:
            sel = sel[0]
            row = sel.row()
            column = sel.column()
            d = self.data[row][column]

            if not d.generator_info["valid"]:
                self.tableWindingLayout.clear()
                return None, None

            bc, bc_text = d.get_basic_characteristics()
            self.textBrowser_wdginfo.setHtml(bc_text)

            self.table = self.tableWindingLayout
            self.table.clear()
            self.table.setRowCount(self.layers)
            self.table.setColumnCount(d.get_num_slots())

            l, ls, lcol = d.get_layers()
            for k1 in range(np.shape(l)[0]):
                for k2 in range(np.shape(l)[1]):
                    self.table.setItem(k1, k2, QTableWidgetItem(ls[k1, k2]))
                    item = self.table.item(k1, k2)
                    if item:
                        item.setBackground(QtGui.QColor(lcol[k1, k2]))
                    self.table.item(k1, k2).setFlags(
                        QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                    )

            for k1 in range(d.get_num_slots()):
                self.table.resizeColumnToContents(k1)
            return row, column
        else:
            return None, None

    def run(self):
        self.generate()
        ok = self.exec_()
        if ok:
            if self.radioButton_overwrite_winding.isChecked():
                overwrite = True
            else:
                overwrite = False
            row, column = self.combination_selected()
            if row is not None:
                ret = {}
                ret["Q"] = self.data[row][column].get_num_slots()
                ret["P"] = 2 * self.data[row][column].get_num_polepairs()
                ret["m"] = self.data[row][column].get_num_phases()
                ret["w"] = self.data[row][column].get_coilspan()
                ret["layers"] = self.layers
                ret["Qes"] = self.data[row][column].get_num_empty_slots()
                ret["overwrite"] = overwrite
                return ret
            else:
                return None
        else:
            return None
