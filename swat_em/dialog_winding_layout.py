from qtpy import uic
from qtpy import QtGui
from qtpy.QtWidgets import QDialog, QTableWidgetItem, QMessageBox
from qtpy.QtGui import QDoubleValidator
import numpy as np
from swat_em.config import get_phase_color, config
from swat_em.analyse import _get_float
import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    __dir__ = sys._MEIPASS  # for pyinstaller
else:
    __dir__ = os.path.dirname(os.path.abspath(__file__))


def get_int_from_str(txt):
    """
    converts txt to a integer number and returns this number
    return None if txt is not a number
    """
    try:
        number = int(txt)
        if number != 0:
            return number
    except:
        return None


class layout(QDialog):
    """
    This is a basic winding editor to define and change the 
    winding layout
    """

    def __init__(self, data):
        self.data = data.copy()
        super().__init__()
        # Set up the user interface from Designer.
        uic.loadUi(os.path.join(__dir__, "ui", "winding_layout.ui"), self)
        self.setWindowTitle("Edit winding layout")

        self.Button_EditMachineData.clicked.connect(self.dialog_machinedata)
        #  self.buttonBox.accepted.connect(self.accept)

        self.lineEditFixTurns.setValidator(QDoubleValidator())

        self.radioTurnsFix.toggled.connect(self.update_radio_turns)
        self.tableWindingLayout.cellChanged.connect(self.update_colors)
        self.tableWindingTurns.cellChanged.connect(self.update_colors)
        self.update_table()
        self.update_table_turns()
        if type(self.data.get_turns()) == type([]):
            self.radioTurnsIndividual.setChecked(True)
        else:
            self.radioTurnsFix.setChecked(True)
            self.lineEditFixTurns.setText(str(self.data.get_turns()))

        self.update_lineEdits(
            self.data.get_num_slots(),
            self.data.get_num_phases(),
            2 * self.data.get_num_polepairs(),
            self.data.get_num_layers(),
        )

    def dialog_machinedata(self):
        """
        User can change Q, m, P, layers
        """
        dialog = machinedata(self.data)
        ret = dialog.run()
        make_update = False
        if ret:
            if ret["Q"] != self.data.get_num_slots():
                make_update = True
            if ret["layers"] != self.data.get_num_layers():
                make_update = True
                for km in range(len(self.data.get_phases())):
                    for ks in range(1, len(self.data.get_phases()[km])):
                        self.data.get_phases()[km][ks] = []
            self.data.set_machinedata(Q=ret["Q"], m=ret["m"], p=ret["P"] / 2)
            self.update_lineEdits(
                self.data.get_num_slots(),
                self.data.get_num_phases(),
                2 * self.data.get_num_polepairs(),
                ret["layers"],
            )
            if make_update:
                self.data.set_phases(self.read_layout())
                self.update_table(layers=ret["layers"])
                self.update_table_turns()

    def update_radio_turns(self):
        if self.radioTurnsFix.isChecked():
            self.tableWindingTurns.setEnabled(False)
            self.lineEditFixTurns.setEnabled(True)
        else:
            self.tableWindingTurns.setEnabled(True)
            self.lineEditFixTurns.setEnabled(False)
            self.update_colors()

    def update_lineEdits(self, Q, m, P, layers):
        self.lineEdit_Q.setText(str(Q))
        self.lineEdit_m.setText(str(m))
        self.lineEdit_P.setText(str(P))
        if layers == 1:
            self.radioButton_slayer.setChecked(True)
        else:
            self.radioButton_dlayer.setChecked(True)

    def update_table(self, layers=None):
        self.table = self.tableWindingLayout
        self.table.blockSignals(True)
        self.table.setColumnCount(self.data.get_num_slots())

        head = ["Layer 1", "Layer 2"]
        if not layers:
            layers = self.data.get_num_layers()
        self.table.setRowCount(layers)
        self.table.setVerticalHeaderLabels(head[:layers])

        l, ls, lcol = self.data.get_layers()
        for k1 in range(np.shape(l)[0]):
            for k2 in range(np.shape(l)[1]):
                self.table.setItem(k1, k2, QTableWidgetItem(ls[k1, k2]))
                item = self.table.item(k1, k2)
                if item:
                    item.setBackground(QtGui.QColor(lcol[k1, k2]))

        for k1 in range(self.data.get_num_slots()):
            self.table.resizeColumnToContents(k1)
        self.table.blockSignals(False)

    def update_table_turns(self):
        table = self.tableWindingTurns
        Nx = self.tableWindingLayout.columnCount()
        Ny = self.tableWindingLayout.rowCount()
        table.setRowCount(Ny)
        table.setColumnCount(Nx)

        head = ["Layer 1", "Layer 2"]
        layers = self.data.get_num_layers()
        table.setRowCount(layers)
        table.setVerticalHeaderLabels(head[:layers])

        phases = self.data.get_phases()
        turns = self.data.get_turns()

        for km, ph in enumerate(phases):
            col = get_phase_color(km)
            for kl in range(len(ph)):
                layer = ph[kl]
                for i, cs in enumerate(layer):
                    if type(turns) == type([]):
                        item = QTableWidgetItem(str(turns[km][kl][i]))
                    else:
                        item = QTableWidgetItem(str(turns))
                    item.setBackground(QtGui.QColor(col))
                    if cs > 0:
                        table.setItem(kl, cs - 1, item)
                    else:
                        table.setItem(kl, abs(cs) - 1, item)

        # test if there are cells without a value (occures if Q is changed)
        for k1 in range(self.data.get_num_layers()):
            for k2 in range(self.data.get_num_slots()):
                item = table.item(k1, k2)
                if item == None:
                    item = QTableWidgetItem("0")
                    table.setItem(k1, k2, item)

        for k1 in range(self.data.get_num_slots()):
            table.resizeColumnToContents(k1)

    def read_layout(self):
        """
        Read layout from table
        """
        S = []
        for layer in [0, 1]:
            for k in range(self.data.get_num_slots()):
                item = self.table.item(layer, k)
                if item:
                    txt = str(item.text())
                    num = get_int_from_str(txt)
                    if num:
                        phase = num
                        sign = 1 if phase > 0 else -1
                        while len(S) < abs(phase):
                            S.append([[], []])
                        S[abs(phase) - 1][layer].append((k + 1) * sign)
        return S

    def read_turns(self):
        """
        Read layout from table
        """
        table = self.tableWindingTurns
        if self.radioTurnsFix.isChecked():
            return None
        else:
            S = []
            for layer in range(table.rowCount()):
                for k in range(self.data.get_num_slots()):
                    item = self.tableWindingLayout.item(layer, k)  # phase
                    item2 = table.item(layer, k)  # turns
                    if item:
                        txt = str(item.text())
                        num = get_int_from_str(txt)
                        if num:
                            phase = num
                            sign = 1 if phase > 0 else -1
                            while len(S) < abs(phase):
                                S.append([[], []])
                            fl = _get_float(item2.text())
                            if fl is not None:
                                S[abs(phase) - 1][layer].append(fl)
                            else:
                                S[abs(phase) - 1][layer].append(0.0)
        return S

    def update_colors(self):
        """
        Update the colors in the table if the user defines phases here
        Also there are some tests for the winding
        """
        error = []
        warning = []

        for layer in [0, 1]:
            for k in range(self.data.get_num_slots()):
                item = self.table.item(layer, k)
                item2 = self.tableWindingTurns.item(layer, k)
                if item:
                    txt = str(item.text())
                    num = get_int_from_str(txt)
                    if num:
                        phase = abs(num)
                        col = get_phase_color(phase - 1)
                        item.setBackground(QtGui.QColor(col))
                        if not self.radioTurnsFix.isChecked():
                            item2.setBackground(QtGui.QColor(col))
                            fl = _get_float(item2.text())
                            if fl is None:
                                item2.setText("0")
                    else:
                        item.setBackground(QtGui.QColor("white"))
                        if not self.radioTurnsFix.isChecked():
                            item2.setBackground(QtGui.QColor("white"))
                            fl = _get_float(item2.text())
                            if fl is None:
                                item2.setText("0")

        # Test for errors
        S = self.read_layout()
        T = self.read_turns()
        for k in range(len(S)):
            S[k] = [item for sublist in S[k] for item in sublist]  # flatten layers
            if T is not None:
                T[k] = [item for sublist in T[k] for item in sublist]  # flatten layers

        # test if the number of positve and negative coil sides are equal
        for k in range(len(S)):
            s = S[k]
            pos = 0
            neg = 0
            for w in s:
                if w > 0:
                    pos += 1
                elif w < 0:
                    neg += 1
            if pos != neg:
                error.append(
                    "Phase {} has {} postive and {} negative coil sides".format(
                        k + 1, pos, neg
                    )
                )

        # Test if theta is 0 for all phases
        if T is not None:
            theta = []
            for km in range(len(S)):
                theta.append(0.0)
                for kp in range(len(S[km])):
                    sign = 1 if S[km][kp] > 0 else -1
                    theta[km] += sign * T[km][kp]
            for i, k in enumerate(theta):
                if abs(k) > 1e-3:
                    txt = "Theta (SUM(Turns*SignOfCoilSides)) of Phase {} is not zero. Check number of turns if there is no error listed regarding the coil sides:<br>".format(
                        i + 1
                    )
                    error.append(txt)

        # test if all phases have the same number of coil sides
        l = [len(s) for s in S]
        if len(set(l)) != 1:
            txt = "Not all phases have the same number of coil sides:<br>"
            for k in range(len(S)):
                txt += "Phase {} hat {} coilsides<br>".format(k + 1, l[k])
            error.append(txt)

        if len(S) > self.data.get_num_phases():
            error.append(
                "There are {} phases but in main window only m = {} is set".format(
                    len(S), self.data.get_num_phases()
                )
            )

        # print errors
        txt_error = '<span style=" color:#ff0000;" >'
        for e in error:
            txt_error += str(e) + "<br>"
        txt_error += "</span>"
        self.textBrowser_output.setHtml(txt_error)

    def accept(self):
        """overwrite the dialog signal for exiting the exec_ command;
        only exit when all user inputs are correct and validated"""
        error = None
        if self.radioTurnsFix.isChecked():
            txt = self.lineEditFixTurns.text()
            turns = _get_float(txt)
            if turns == None:
                QMessageBox.critical(
                    self, "Error", '"{}" is not a valid number of turns'.format(txt)
                )
                error = True
            if type(self.data.get_turns()) == type([]):
                ret = QMessageBox.question(
                    self,
                    "Overwrite number of turns",
                    "In the previous winding there are individual number of turns. Is it ok to loose them?",
                    QMessageBox.Yes | QMessageBox.Cancel,
                )
                if ret != QMessageBox.Yes:
                    error = False

        if error is None:
            super().accept()  # call accept Dialog from Qdialog (end of exec_)

    def run(self):
        ok = self.exec_()
        if ok:
            if self.radioButton_overwrite_winding.isChecked():
                overwrite = True
            else:
                overwrite = False
            phases = self.read_layout()

            if self.radioTurnsFix.isChecked():
                txt = self.lineEditFixTurns.text()
                turns = _get_float(txt)
            else:
                turns = self.read_turns()

            layer1 = False
            layer2 = False  # test if single or double layer winding
            for s in phases:
                if len(s[0]) > 0:
                    layer1 = True
                if len(s[1]) > 0:
                    layer2 = True
            if layer1 and layer2:
                layers = 2
            else:
                layers = 1

            Q = self.data.get_num_slots()
            p = self.data.get_num_polepairs()
            m = self.data.get_num_phases()
            w = self.data.get_coilspan()
            ret = {
                "phases": phases,
                "Q": Q,
                "P": 2 * p,
                "m": m,
                "w": w,
                "layers": layers,
                "overwrite": overwrite,
                "turns": turns,
            }
            return ret
        else:
            return None


class machinedata(QDialog):
    """
    User can change Q, m, P, layers
    """

    def __init__(self, data):
        self.data = data
        super().__init__()
        uic.loadUi(os.path.join(__dir__, "ui", "MachineData.ui"), self)
        self.setWindowTitle("Change machine data")
        self.data = data
        self.spinBox_Q.setValue(self.data.get_num_slots())
        self.spinBox_m.setValue(self.data.get_num_phases())
        self.spinBox_P.setValue(2 * self.data.get_num_polepairs())
        if self.data.get_num_layers() == 1:
            self.radioButton_slayer.setChecked(True)
        else:
            self.radioButton_dlayer.setChecked(True)

    def run(self):
        ok = self.exec_()
        if ok:
            if self.radioButton_slayer.isChecked():
                layers = 1
            elif self.radioButton_dlayer.isChecked():
                layers = 2
            Q = self.spinBox_Q.value()
            P = self.spinBox_P.value()
            m = self.spinBox_m.value()
            if Q < self.data.get_num_slots():
                buttonReply = QMessageBox.question(
                    self,
                    "Warning",
                    """The defined number of slots is lower than the number of slots in the actual winding. \
Is it ok to loose some informations of the actual winding layout?""",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if buttonReply != QMessageBox.Yes:
                    return None

            if layers < self.data.get_num_layers():
                buttonReply = QMessageBox.question(
                    self,
                    "Warning",
                    """The defined number of layers is lower than the number of layers in the actual winding. \
Is it ok to loose some informations of the actual winding layout?""",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if buttonReply != QMessageBox.Yes:
                    return None

            ret = {"Q": Q, "P": P, "m": m, "layers": layers}
            return ret
        else:
            return None
