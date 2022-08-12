# -*- coding: utf-8 -*-

from qtpy import uic
from qtpy.QtWidgets import QDialog, QApplication, QMessageBox, QTableWidgetItem
from qtpy.QtGui import QIntValidator
from qtpy import QtGui
from qtpy import QtCore
import numpy as np
import sys
import os

import pyqtgraph as pg
import pyqtgraph.exporters

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOptions(antialias=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from swat_em import wdggenerator
from swat_em import datamodel
from swat_em.config import config, get_phase_color, get_line_color
from swat_em.report import num2str

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    __dir__ = sys._MEIPASS  # for pyinstaller
else:
    __dir__ = os.path.dirname(os.path.abspath(__file__))


class CombSniffer(QDialog):
    def __init__(self):
        super().__init__()

        # Set up the user interface from Designer.
        uic.loadUi(os.path.join(__dir__, "ui", "CombSniffer.ui"), self)

        self.plot_keys = [
            "idx",
            "Q",
            "P",
            "m",
            "q",
            "w",
            "sigma_d",
            "kw1",
            "a",
            "t",
            "r1",
            "lcmQP",
        ]

        for k in self.plot_keys:
            self.comboBox_xaxis.addItem(str(k))
            self.comboBox_yaxis.addItem(str(k))

        self.comboBox_xaxis.setCurrentIndex(6)  # sigma_d
        self.comboBox_yaxis.setCurrentIndex(7)  # kw1

        self.change_Qfix()
        self.change_Pfix()

        self.radioButton_Qfix.toggled.connect(self.change_Qfix)
        self.radioButton_Pfix.toggled.connect(self.change_Pfix)
        self.Button_find.clicked.connect(self.calc)
        self.Button_cp2clipboard_image.clicked.connect(self.cp2clipboard)
        self.comboBox_xaxis.currentIndexChanged.connect(self.update_plot)
        self.comboBox_yaxis.currentIndexChanged.connect(self.update_plot)
        self.checkBox_show_indices.toggled.connect(self.plot_indices)

        self.tableWidget.itemSelectionChanged.connect(self.on_table_selection)

        self.progressBar.setValue(0)

        self.init_plot()
        self.reset_data()

    def change_Qfix(self):
        if self.radioButton_Qfix.isChecked():
            self.spinBox_Q.setEnabled(True)
            self.spinBox_Q1.setEnabled(False)
            self.spinBox_Q2.setEnabled(False)
        else:
            self.spinBox_Q.setEnabled(False)
            self.spinBox_Q1.setEnabled(True)
            self.spinBox_Q2.setEnabled(True)

    def change_Pfix(self):
        if self.radioButton_Pfix.isChecked():
            self.spinBox_P.setEnabled(True)
            self.spinBox_P1.setEnabled(False)
            self.spinBox_P2.setEnabled(False)
        else:
            self.spinBox_P.setEnabled(False)
            self.spinBox_P1.setEnabled(True)
            self.spinBox_P2.setEnabled(True)

    def calc(self):

        # TODO: Clear all data in Comboboxes, plots and tables
        self.reset_data()

        if self.radioButton_Qfix.isChecked():
            Qrange = [self.spinBox_Q.value()]
        else:
            Qrange = list(range(self.spinBox_Q1.value(), self.spinBox_Q2.value() + 1))

        if self.radioButton_Pfix.isChecked():
            Prange = [self.spinBox_P.value()]
        else:
            Prange = list(
                range(self.spinBox_P1.value(), self.spinBox_P2.value() + 1, 2)
            )

        m = self.spinBox_m.value()

        layers = []
        if self.checkBox_singlelayer.isChecked():
            layers.append(1)
        if self.checkBox_doublelayer.isChecked():
            layers.append(2)
        if self.checkBox_emptyslots.isChecked():
            allow_empty_slots = True
        else:
            allow_empty_slots = False
        if allow_empty_slots:
            es = -1
        else:
            es = 0

        Qlist = []
        Plist = []
        wlist = []
        layerslist = []
        for Q_ in Qrange:
            for P_ in Prange:
                for l_ in layers:
                    if l_ == 2:
                        w = Q_ / P_
                        if w >= 2:
                            for w_ in range(1, int(w) + 1):
                                Qlist.append(Q_)
                                Plist.append(P_)
                                wlist.append(w_)
                                layerslist.append(l_)
                        else:
                            Qlist.append(Q_)
                            Plist.append(P_)
                            wlist.append(-1)
                            layerslist.append(l_)
                    else:
                        Qlist.append(Q_)
                        Plist.append(P_)
                        wlist.append(-1)
                        layerslist.append(l_)

        num_combinations = len(Qlist)
        #  print('Num combinations:', num_combinations)
        #  print('Qlist', Qlist)
        #  print('Plist', Plist)
        #  print('wlist', wlist)
        #  print('layerslist', layerslist)

        self.progressBar.setValue(0)
        self.wdg_list = []
        self.bc_list = []
        for k in range(num_combinations):
            wdg = datamodel()
            wdg.genwdg(
                Qlist[k],
                Plist[k],
                m=m,
                layers=layerslist[k],
                w=wlist[k],
                empty_slots=es,
                analyse=False,
            )
            kw1 = wdg.get_fundamental_windingfactor()
            #  print('Q', Qlist[k])
            #  print('P', Plist[k])
            #  print('w', wlist[k])
            #  print('layers', layerslist[k])
            #  print('kw1', kw1)

            if kw1 is not None:
                if kw1[0] > 0.01:
                    bc, bc_str = wdg.get_basic_characteristics()
                    if bc["sym"]:
                        self.wdg_list.append(wdg)
                        self.bc_list.append(bc)
            self.progressBar.setValue(100 / num_combinations * (k + 1))

        self.data = {}
        self.data["idx"] = list(range(len(self.wdg_list)))
        self.data["Q"] = [wdg.get_num_slots() for wdg in self.wdg_list]
        self.data["P"] = [2 * wdg.get_num_polepairs() for wdg in self.wdg_list]
        self.data["m"] = [wdg.get_num_phases() for wdg in self.wdg_list]
        self.data["q"] = [bc["q"] for bc in self.bc_list]
        self.data["w"] = []
        for wdg in self.wdg_list:
            w = wdg.get_coilspan()
            if type(w) == type([]):
                self.data["w"].append(np.mean(w))
            else:
                self.data["w"].append(w)

        self.data["kw1"] = [bc["kw1"][0] for bc in self.bc_list]
        self.data["sigma_d"] = [bc["sigma_d"] for bc in self.bc_list]
        self.data["a"] = [bc["a"] for bc in self.bc_list]
        self.data["t"] = [bc["t"] for bc in self.bc_list]
        self.data["r1"] = [bc["r"][0] for bc in self.bc_list]
        self.data["lcmQP"] = [bc["lcmQP"] for bc in self.bc_list]

        # make shure that keys for data are the same as the
        # items in the combo boxes of the axis to plot
        assert set(self.data.keys()) == set(self.plot_keys)

        self.update_data_in_gui()
        #  print('data', data)
        #  print('fertig')
        #  print('kw1:', kw1)

    def update_data_in_gui(self):
        self.update_plot()
        self.fill_table()
        self.textBrowser_wdginfo.setHtml(
            "{} valid windings found!<br><br>Click on a point in the \
        graphic window to get more informations!".format(
                len(self.wdg_list)
            )
        )

    def reset_data(self):
        """
        resetting all data before generating windings
        """
        self.data = {}
        self.fig.clear()
        self.indices_text = []
        self.scatter_marker_index = None
        self.textBrowser_wdginfo.setHtml('Click on "Find Winding"')
        self.tableWindingLayout.clear()
        self.tableWindingLayout.setRowCount(0)
        self.tableWindingLayout.setColumnCount(0)

        self.tableWidget.blockSignals(True)
        self.tableWidget.clear()
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(0)
        self.tableWidget.blockSignals(False)

    def init_plot(self):
        """
        generate figure in the gui
        """
        self.layout = self.mplvl
        self.widget = self.mplwidget
        self.fig = pg.PlotWidget()
        self.layout.addWidget(self.fig)
        self.fig.showGrid(x=True, y=True)

    def update_plot(self):
        """
        plot new data
        """
        self.fig.clear()
        # skip if there is no data to plot
        if len(self.data) == 0:
            return

        x_key = str(self.comboBox_xaxis.currentText())
        y_key = str(self.comboBox_yaxis.currentText())
        self.fig.setLabel("bottom", x_key)
        self.fig.setLabel("left", y_key)

        penlist = [pg.mkPen(None)] * len(self.data[x_key])
        size = [10] * len(self.data[x_key])

        self.scatter = pg.ScatterPlotItem()
        self.scatter.setData(self.data[x_key], self.data[y_key])
        self.scatter.setSize(size)
        self.scatter.setPen(penlist)
        self.scatter.sigClicked.connect(self.on_plot_click)
        self.fig.addItem(self.scatter)
        self.plot_indices()
        self.fig.autoRange()
        self.fig.show()

    def plot_marker(self, idx):
        """
        highlight point at index 'idx'
        """
        penlist = [pg.mkPen(None)] * len(self.scatter.getData()[0])
        size = [10] * len(penlist)
        if idx is not None:
            penlist[idx] = pg.mkPen(get_line_color(1), width=2)
            size[idx] = 15
        self.scatter.setPen(penlist)

    def plot_indices(self):
        """
        plot the index numbers of all points as strings
        """
        # skip if there is no data to plot
        if len(self.data) == 0:
            return

        if self.checkBox_show_indices.isChecked():
            x_key = str(self.comboBox_xaxis.currentText())
            y_key = str(self.comboBox_yaxis.currentText())
            for k in range(len(self.data[x_key])):
                txt = pg.TextItem(str(k), anchor=(0.0, 0.0))
                txt.setPos(self.data[x_key][k], self.data[y_key][k])
                txt.setColor("k")
                self.fig.addItem(txt, ignoreBounds=True)
                self.indices_text.append(txt)
        else:
            for txt in self.indices_text:
                self.fig.removeItem(txt)

    def on_plot_click(self, plot, points):
        """
        User clicked on the plot
        """
        idx = []
        for point in points:
            x, y = point.pos()
            idx1 = x == self.scatter.getData()[0]
            idx2 = y == self.scatter.getData()[1]
            i = np.logical_and(idx1, idx2)
            idx.append(np.where(i == True))
        idx = np.array(idx).flatten()
        idx = list(set(idx))

        # if there is one ore more points selected
        if len(idx) > 1:
            DIALOG = select_index(self.wdg_list, idx)
            idx = DIALOG.run()
            if idx is None:
                return
        else:
            idx = idx[0]
        self.combination_selected_in_table(idx)
        self.scatter_marker_index = idx
        self.plot_marker(idx)
        self.table_marker(idx)

    def cp2clipboard(self):
        """
        copy figure as bitmap to clipboard
        """
        img = self.widget.grab()
        QApplication.clipboard().setImage(img.toImage())

    def combination_selected_in_table(self, sel):
        """
        user selected a cell/winding combination
        """
        d = self.wdg_list[sel]
        bc, bc_text = d.get_basic_characteristics()
        self.textBrowser_wdginfo.setHtml(bc_text)

        table = self.tableWindingLayout
        table.clear()
        table.setRowCount(d.get_num_layers())
        table.setColumnCount(d.get_num_slots())

        l, ls, lcol = d.get_layers()
        for k1 in range(np.shape(l)[0]):
            for k2 in range(np.shape(l)[1]):
                table.setItem(k1, k2, QTableWidgetItem(ls[k1, k2]))
                item = table.item(k1, k2)
                if item:
                    item.setBackground(QtGui.QColor(lcol[k1, k2]))
                table.item(k1, k2).setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                )

        for k1 in range(d.get_num_slots()):
            table.resizeColumnToContents(k1)

    def fill_table(self):
        """
        fill table after generating winding combinations
        """
        # skip if there is no data to plot
        if len(self.data) == 0:
            return

        table = self.tableWidget
        table.clear()
        table.setRowCount(len(self.data["Q"]))
        table.setColumnCount(len(self.data))
        table.setSortingEnabled(True)

        myFont = QtGui.QFont()
        myFont.setBold(True)
        for i, key in enumerate(self.plot_keys):

            table_header_item = QTableWidgetItem(key)
            table_header_item.setFont(myFont)
            table.setHorizontalHeaderItem(i, table_header_item)

            for k in range(len(self.data[key])):
                txt = num2str(self.data[key][k], maxlen=8)
                table.setItem(k, i, QTableWidgetItem(txt))

                #  item = QTableWidgetItem()
                #  item.setData(QtCore.Qt.DisplayRole, self.data[key][k])
                #  self.table.setItem(k, i, item)

                table.item(k, i).setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                )  # note editable
            table.resizeColumnToContents(i)

    def on_table_selection(self):
        """
        user selected a winding in the table
        """
        #  row = mi.row()

        table = self.tableWidget
        row = table.currentRow()
        idx = int(table.item(row, 0).text())
        self.combination_selected_in_table(idx)
        self.scatter_marker_index = idx
        self.plot_marker(idx)

    def table_marker(self, idx):
        """
        Select winding in the table after selecting a point in the plot
        """
        table = self.tableWidget
        for row in range(table.rowCount()):
            i = int(table.item(row, 0).text())
            if i == idx:
                table.setCurrentCell(row, 0)
                break

    def run(self):
        ok = self.exec_()
        if ok:
            if self.scatter_marker_index is not None:

                if self.radioButton_overwrite_winding.isChecked():
                    overwrite = True
                else:
                    overwrite = False
                wdg = self.wdg_list[self.scatter_marker_index]
                w = self.data["w"][self.scatter_marker_index]
                if int(w) != w:
                    w = -1
                ret = {
                    "Q": wdg.get_num_slots(),
                    "P": 2 * wdg.get_num_polepairs(),
                    "m": wdg.get_num_phases(),
                    "w": w,
                    "layers": wdg.get_num_layers(),
                    "overwrite": overwrite,
                    "Qes": wdg.get_num_empty_slots(),
                }
                return ret
        return None


class select_index(QDialog):
    """
    Dialog for selecting an index of a winding while clicking on more
    than one point in the plot
    """

    def __init__(self, wdg_list, indices):
        super().__init__()
        uic.loadUi(os.path.join(__dir__, "ui", "CombSnifferSelIndix.ui"), self)
        self.wdg_list = wdg_list
        self.indices = indices
        self.listWidget.currentRowChanged.connect(self.index_changed)
        self.fill_table()

    def fill_table(self):
        """
        Show all selected indices
        """
        self.listWidget.blockSignals(True)
        for i in self.indices:
            self.listWidget.addItem(str(i))
        self.listWidget.blockSignals(False)
        self.listWidget.setCurrentRow(0)

    def index_changed(self):
        """
        User changed index
        """
        i = self.listWidget.currentRow()
        i = self.indices[i]
        bc, bc_text = self.wdg_list[i].get_basic_characteristics()
        self.textBrowser_wdginfo.setHtml(bc_text)

    def run(self):
        ok = self.exec_()
        if ok:
            i = self.listWidget.currentRow()
            return self.indices[i]
        else:
            return None
