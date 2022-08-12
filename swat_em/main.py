# -*- coding: utf-8 -*-
import sys
import os
from qtpy import uic
from qtpy.QtWidgets import (
    QMainWindow,
    QApplication,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QListWidgetItem,
    QMenu,
    QAction,
    QSplashScreen,
    QGraphicsScene,
)
from qtpy.QtGui import QIntValidator, QDoubleValidator, QIcon, QPixmap, QPainter
from qtpy.QtPrintSupport import QPrintDialog, QPrinter
from qtpy import QtCore

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    __dir__ = sys._MEIPASS  # for pyinstaller
else:
    __dir__ = os.path.dirname(os.path.abspath(__file__))


# Create a splash screen while loading the librarys because this
# takes some time
app = QApplication([])  # temp. app needed for splash
splash_pix = QPixmap(os.path.join(__dir__, "ui", "bitmaps", "splash.png"))
splash = QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
splash.show()

import time
import argparse
import subprocess
import platform
import tempfile
from swat_em import __version__
from swat_em import dialog_genwdg
from swat_em import dialog_about
from swat_em import dialog_notes
from swat_em import dialog_winding_layout
from swat_em import dialog_import_winding
from swat_em import dialog_combination_sniffer
from swat_em import dialog_settings
from swat_em.config import config, save_config, get_config
from swat_em import datamodel, project

# from swat_em import wdggenerator
from swat_em import plots
from swat_em import report
from swat_em.analyse import _get_float

MSG_TIME = 3000  # time in which the message is displayed in the statusbar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.data = datamodel()
        self.project = project()

        # Set up the user interface from Designer.
        uic.loadUi(os.path.join(__dir__, "ui", "MainWindow.ui"), self)
        self.setWindowTitle("SWAT-EM")

        self.DIALOG_GenWinding = dialog_genwdg.GenWinding2()
        self.DIALOG_GenWindingCombinations = dialog_genwdg.GenWindingCombinations()
        self.DIALOG_CombSniffer = dialog_combination_sniffer.CombSniffer()

        # open/close tabs
        self.plot_tabs_actions = {
            "tab_slot": self.actionLayout,
            "tab_layout_polar": self.actionLayout_polar,
            "tab_overhang": self.actionOverhang,
            "tab_star": self.actionSlot_voltage_phasors,
            "tab_wf": self.actionWinding_factor,
            "tab_mmk": self.actionMagneto_motive_force,
            "tab_report": self.actionReport,
        }
        for key, value in self.plot_tabs_actions.items():
            value.triggered.connect(self.plot_tabs_update_from_menu)
        self.plot_tabs_init()
        self.actionShow_all_plots.triggered.connect(self.plot_tabs_show_all)

        # Connect the buttons
        self.Button_exit.clicked.connect(self.close)

        self.projectlist_Button_new.clicked.connect(self.dialog_new_winding)
        self.projectlist_Button_delete.clicked.connect(self.projectlist_delete)
        self.projectlist_Button_clone.clicked.connect(self.projectlist_clone)
        self.projectlist_Button_notes.clicked.connect(self.dialog_get_notes)
        self.save_report_Button.clicked.connect(self.export_to_txt)
        self.actionprint.triggered.connect(self.printer)
        self.actionFull_Screen.triggered.connect(self.toggle_fullscreen)
        self.Button_search.clicked.connect(self.find_in_report)
        self.lineEdit_find.returnPressed.connect(self.find_in_report)
        self.plot_tabs.tabCloseRequested.connect(self.plot_tabs_remove)

        # Connect menu
        self.actionExit.triggered.connect(self.close)
        self.actionNew_winding.triggered.connect(self.dialog_new_winding)
        self.actionGenerate_winding.triggered.connect(self.dialog_GenWinding)
        self.actionGenerate_winding_combinations.triggered.connect(
            self.dialog_GenWindingCombinations
        )
        self.actionCombination_sniffer.triggered.connect(self.dialog_CombSniffer)
        self.actionImport_from_file.triggered.connect(self.dialog_ImportWinding)
        self.actionAdd_Notes.triggered.connect(self.dialog_get_notes)

        self.actionsave.triggered.connect(self.save_to_file)
        self.actionsave_as.triggered.connect(self.save_as_to_file)
        self.actionload.triggered.connect(self.load_from_file)
        self.actionProgram_Info.triggered.connect(dialog_about.about)
        self.actionShow_winding_layout.triggered.connect(self.dialog_EditWindingLayout)
        self.actionSettings.triggered.connect(self.dialog_settings)
        self.actionundo.triggered.connect(self.undo)
        self.actionredo.triggered.connect(self.redo)
        self.actionFind.triggered.connect(self.set_focus_to_find)

        # Connect find in report
        self.lineEdit_find.textChanged.connect(self.find_in_report)

        # Connect project models
        self.project_listWidget.currentRowChanged.connect(self.update_project)
        self.project_listWidget.itemChanged.connect(
            self.projectlist_rename
        )  # item renamed
        self.project_listWidget.model().rowsMoved.connect(self.projectlist_reorder)

        # context-menu on project models
        self.project_listWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.actionNew = QAction(
            "New Winding",
            self.project_listWidget,
            icon=QIcon(os.path.join(__dir__, "ui", "icons", "new.png")),
        )
        self.project_listWidget.addAction(self.actionNew)
        self.actionNew.triggered.connect(self.dialog_new_winding)

        self.actionClone = QAction(
            "clone",
            self.project_listWidget,
            icon=QIcon(os.path.join(__dir__, "ui", "icons", "clone.png")),
        )
        self.project_listWidget.addAction(self.actionClone)
        self.actionClone.triggered.connect(self.projectlist_clone)

        self.actionNotes = QAction(
            "add notes",
            self.project_listWidget,
            icon=QIcon(os.path.join(__dir__, "ui", "icons", "notes.png")),
        )
        self.project_listWidget.addAction(self.actionNotes)
        self.actionNotes.triggered.connect(self.dialog_get_notes)

        self.actionDelete = QAction(
            "delete",
            self.project_listWidget,
            icon=QIcon(os.path.join(__dir__, "ui", "icons", "delete.png")),
        )
        self.project_listWidget.addAction(self.actionDelete)
        self.actionDelete.triggered.connect(self.projectlist_delete)

        # TODO
        self.actionprint_report.triggered.connect(self.create_report)
        self.actionExport_data_to_Excel.triggered.connect(self.export_to_excel)
        self.actionExport_Text_report.triggered.connect(self.export_to_txt)

        self.actionHelp.triggered.connect(self.open_manual)

        self.plot_tabs.currentChanged.connect(
            lambda: self.update_plot_in_GUI(small_update=False)
        )
        self.radioButton_electrical.toggled.connect(self.update_plot_in_GUI)
        self.comboBox_star_harmonics.currentIndexChanged.connect(
            self.update_plot_in_GUI
        )
        self.checkBoxForceX.toggled.connect(self.update_plot_in_GUI)
        self.checkBox_opt_wdg_overhang.toggled.connect(self.update_plot_in_GUI)
        self.checkBox_opt_wdg_overhang_layout_polar.toggled.connect(
            self.update_plot_in_GUI
        )

        #  initial windings  -----------------------------------
        self.data = datamodel()
        self.data.genwdg(Q=12, P=2, m=3, w=-1, layers=1)
        self.data.set_notes(
            "Winding example for a overlapping single layer winding for a 12 slots, 2 poles machine"
        )
        self.data.set_title("12-2 overlapping winding")
        self.project.add_model(self.data)

        self.data = datamodel()
        self.data.genwdg(Q=9, P=8, m=3, w=1, layers=2, turns=10)
        self.data.set_notes(
            "Winding example for a tooth-coil-winding for 9 slots, 8 poles machine"
        )
        self.data.set_title("9-8 tooth-coil winding")
        self.project.add_model(self.data)

        self.project.set_save_state(True)  # only for the initial winding
        self.check_is_saved()

        # Plots
        self.MMK_phase_edit.setValidator(QDoubleValidator(0, 360, 1))
        self.MMK_phase_edit.setText(str(0.000))

        self.MMK_phase_slider.valueChanged.connect(self.update_MMK_phase_edit)
        self.MMK_phase_edit.textEdited.connect(self.update_MMK_phase_slider)
        self.MMK_phase_edit.textChanged.connect(
            lambda: self.update_plot_in_GUI(small_update=True)
        )

        self.fig = {}
        self.fig["tab_slot"] = plots._slot_plot(
            self.mplvl_slot, self.mplwidget_slot, self.data
        )
        self.Button_cp2clipboard_image_layout.clicked.connect(
            self.fig["tab_slot"].cp2clipboard
        )

        self.fig["tab_layout_polar"] = plots._polar_layout_plot(
            self.mplvl_layout_polar, self.mplwidget_layout_polar, self.data
        )
        self.Button_cp2clipboard_image_layout_polar.clicked.connect(
            self.fig["tab_layout_polar"].cp2clipboard
        )

        self.fig["tab_overhang"] = plots._overhang_plot(
            self.mplvl_overhang, self.mplwidget_overhang, self.data
        )
        self.Button_cp2clipboard_image_overhang.clicked.connect(
            self.fig["tab_overhang"].cp2clipboard
        )

        self.fig["tab_star"] = plots._slot_star(
            self.mplvl_star, self.mplwidget_star, self.data, self.tableWidget_star
        )
        self.Button_cp2clipboard_image_star.clicked.connect(
            self.fig["tab_star"].cp2clipboard
        )

        self.fig["tab_wf"] = plots._windingfactor(
            self.mplvl_wf, self.mplwidget_wf, self.data, self.tableWidget_wf
        )
        self.Button_cp2clipboard_image_wf.clicked.connect(
            self.fig["tab_wf"].cp2clipboard
        )

        self.fig["tab_mmk"] = plots._mmk(
            self.mplvl_mmk, self.mplwidget_mmk, self.data, self.tableWidget_mmk
        )
        self.Button_cp2clipboard_image_mmk.clicked.connect(
            self.fig["tab_mmk"].cp2clipboard
        )

        self.report = plots._report(self.reportEdit)
        self.Button_cp2clipboard_image_report.clicked.connect(self.report.cp2clipboard)
        self.highlighter = plots._Report_Highlighter(self.reportEdit)

        self.update_project_list()
        self.project.reset_undo_state()  # init-winding shouldn't undoable
        self.actionundo.setDisabled(True)
        self.actionredo.setDisabled(True)
        self.show()

    def toggle_fullscreen(self):
        if self.windowState() & QtCore.Qt.WindowFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()

    def check_is_saved(self):
        """
        checks if the project ist saved for
        - setting the title of the main window with the filename
        - mark the file-name in the window title with a * if it is not saved
        - disable redu/undo buttons if there are no available states
        """
        if self.project.get_num_undo_state() < 1:
            self.actionundo.setDisabled(True)  # no more states to restore
        if self.project.get_num_redo_state() < 1:
            self.actionredo.setDisabled(True)  # no more states to restore

        fname = self.project.get_filename()
        if fname:
            if not self.project.get_save_state():
                fname = "*" + fname
            self.setWindowTitle(fname + " - SWAT-EM")

    def save_undo_state(self):
        """save the actual state of the project models for undo operation"""
        self.project.save_undo_state()
        self.actionundo.setDisabled(False)
        self.project.reset_redo_state()  # redo states aren't valid any more
        self.actionredo.setDisabled(True)
        self.check_is_saved()

    def undo(self):
        """undo the last operation (restore state)"""
        self.project.save_redo_state()
        self.actionredo.setDisabled(False)
        self.project.undo()
        self.update_project_list()
        self.check_is_saved()

    def redo(self):
        self.project.save_undo_state()
        self.actionundo.setDisabled(False)
        self.project.redo()
        self.update_project_list()
        self.check_is_saved()

    def update_project_list(self, switch_to_new=False):
        """fill the list of all data objects
        if 'switch_to_new = True: mark the last (new) object in project list 
        and show the content of it. If False: The last idx is marked again"""
        self.project_listWidget.blockSignals(True)
        idx = self.project_listWidget.currentRow()  # save current idx
        self.project_listWidget.clear()  # clear existing data
        for i, item in enumerate(self.project.get_titles()):
            widgetitem = QListWidgetItem(item)
            widgetitem.setFlags(widgetitem.flags() | QtCore.Qt.ItemIsEditable)
            self.project_listWidget.addItem(widgetitem)
        self.project_listWidget.blockSignals(False)
        if switch_to_new:
            idx = i
        else:
            idx = i if i < idx else idx
            idx = 0 if idx < 0 else idx
        self.project_listWidget.setCurrentRow(idx)  # last item is current model

    def update_project(self, idx=None):
        """update the clicked data object form the project"""
        if not idx:
            idx = self.project_listWidget.currentRow()
        self.data = self.project.get_model_by_index(idx)
        self.update_data_in_GUI()  # update all data output and figures

    def projectlist_delete(self):
        if self.project_listWidget.count() > 1:
            self.save_undo_state()  # for undo
            idx = self.project_listWidget.currentRow()
            self.project.delete_model_by_index(idx)
            self.statusbar.showMessage("winding deleted", MSG_TIME)
            self.update_project_list()

    def projectlist_clone(self):
        self.save_undo_state()  # for undo
        idx = self.project_listWidget.currentRow()
        self.project.clone_by_index(idx)
        self.statusbar.showMessage("winding cloned", MSG_TIME)
        self.update_project_list(switch_to_new=True)

    def projectlist_rename(self):
        self.save_undo_state()  # for undo
        idx = self.project_listWidget.currentRow()
        newname = self.project_listWidget.item(idx).text()
        self.project.rename_by_index(idx, newname)

    def projectlist_reorder(self, event, start, end, dest, row):
        """
        user moved items in projectlist
        start: index from starting
        row:   index where dropped
        """
        self.save_undo_state()
        if row > start:
            row -= 1
        self.project.move_model(start, row)
        self.update_project_list()

    def update_MMK_phase_edit(self):
        """slider for MMK phase moved"""
        self.MMK_phase_edit.setText(str(self.MMK_phase_slider.value()))

    def update_MMK_phase_slider(self):
        """lineedit for MMK phase changed"""
        f = _get_float(self.MMK_phase_edit.text())
        if f is not None:
            self.MMK_phase_slider.setValue(f)

    def dialog_GenWinding(self):
        """
        calls the dialog to generate a single winding
        """
        ret = self.DIALOG_GenWinding.run()
        if ret:
            self.save_undo_state()
            data = datamodel()
            data.genwdg(
                Q=ret["Q"],
                P=ret["P"],
                m=ret["m"],
                w=ret["w"],
                layers=ret["layers"],
                empty_slots=ret["Qes"],
            )
            if ret["overwrite"]:
                data.set_title(self.data.get_title())  # use existing title
                data.set_notes(self.data.get_notes())  # use existings notes
                self.data = data
                self.project.replace_model_by_index(
                    data, self.project_listWidget.currentRow()
                )
            else:
                self.project.add_model(data)
                self.update_project_list(switch_to_new=True)
            self.update_data_in_GUI()

    def dialog_GenWindingCombinations(self):
        """
        calls the dialog to generate a winding based on a big table of available windings
        """
        ret = self.DIALOG_GenWindingCombinations.run()
        if ret:
            self.save_undo_state()
            data = datamodel()
            data.genwdg(
                Q=ret["Q"],
                P=ret["P"],
                m=ret["m"],
                w=ret["w"],
                layers=ret["layers"],
                empty_slots=ret["Qes"],
            )

            if ret["overwrite"]:
                data.set_title(self.data.get_title())  # use existing title
                data.set_notes(self.data.get_notes())  # use existings notes
                self.data = data
                self.project.replace_model_by_index(
                    data, self.project_listWidget.currentRow()
                )
            else:
                self.project.add_model(data)
                self.update_project_list(switch_to_new=True)
            self.update_data_in_GUI()

    def dialog_CombSniffer(self):
        """
        calls the dialog to generate a winding based on a big table of available windings
        """
        ret = self.DIALOG_CombSniffer.run()
        if ret:
            self.save_undo_state()
            data = datamodel()
            data.genwdg(
                Q=ret["Q"],
                P=ret["P"],
                m=ret["m"],
                w=ret["w"],
                layers=ret["layers"],
                empty_slots=ret["Qes"],
            )

            if ret["overwrite"]:
                data.set_title(self.data.get_title())  # use existing title
                data.set_notes(self.data.get_notes())  # use existings notes
                self.data = data
                self.project.replace_model_by_index(
                    data, self.project_listWidget.currentRow()
                )
            else:
                self.project.add_model(data)
                self.update_project_list(switch_to_new=True)
            self.update_data_in_GUI()

    def dialog_ImportWinding(self):
        """Import windings from file to workspace"""
        DIALOG_ImportWinding = dialog_import_winding.import_winding()
        ret = DIALOG_ImportWinding.run()
        if ret is not None:
            self.save_undo_state()  # for undo
            for data in ret:
                self.project.add_model(data)
            self.update_project_list(switch_to_new=True)
            self.statusbar.showMessage(
                "{} winding(s) imported".format(len(ret)), MSG_TIME
            )

    def dialog_EditWindingLayout(self):
        """
        calls the dialog to generate a winding based on a big table of available windings
        """
        DIALOG_EditWindingLayout = dialog_winding_layout.layout(self.data)
        ret = DIALOG_EditWindingLayout.run()

        if ret:
            self.save_undo_state()

            data = datamodel()
            data.set_machinedata(Q=ret["Q"], p=ret["P"] // 2, m=ret["m"])
            data.set_phases(ret["phases"], w=ret["w"], turns=ret["turns"])
            data.analyse_wdg()
            if ret["overwrite"]:
                data.set_title(self.data.get_title())  # use existing title
                data.set_notes(self.data.get_notes())  # use existings notes
                self.data = data
                self.project.replace_model_by_index(
                    data, self.project_listWidget.currentRow()
                )
            else:
                self.project.add_model(data)
                self.update_project_list(switch_to_new=True)
            self.update_data_in_GUI()

    def dialog_get_notes(self):
        """dialog asks user to type notes and stores it to datamodel"""
        dialog = dialog_notes.get_notes(self.data.notes)
        text = dialog.run()
        if text is not None:
            self.save_undo_state()
            self.data.set_notes(text)
            self.update_data_in_GUI()

    def dialog_new_winding(self):
        """
        dialog to generate a new winding
        wraps the user input to the existing generators
        """
        dialog = dialog_genwdg.NewWinding()
        ret = dialog.run()
        if ret is not None:
            if ret == 0:  # trigger the different generators
                self.dialog_EditWindingLayout()
            elif ret == 1:
                self.dialog_GenWinding()
            elif ret == 2:
                self.dialog_GenWindingCombinations()
            else:
                raise (Exception, "winding generator {} not implemented".format(ret))

    def dialog_settings(self):
        global config
        config
        DIALOG_Settings = dialog_settings.Settings(config)
        ret = DIALOG_Settings.run()
        if ret:
            config = ret
            save_config(config)
            self.project.analyse_all_models()  # recalc all models
            self.update_data_in_GUI()

    def update_data_in_GUI(self):
        """
        plots all winding data in gui
        """
        bc, bc_str = self.data.get_basic_characteristics()
        self.textBrowser_wdginfo.setHtml(bc_str)
        idx_old = self.comboBox_star_harmonics.currentText()

        idx = None
        if idx_old:
            if int(idx_old) in self.data.results["nu_el"]:
                idx = self.data.results["nu_el"].index(int(idx_old))

        self.comboBox_star_harmonics.blockSignals(
            True
        )  # prevent double plotting on startup
        self.comboBox_star_harmonics.clear()
        self.comboBox_star_harmonics.addItems(
            [str(k) for k in self.data.results["nu_el"]]
        )
        self.comboBox_star_harmonics.blockSignals(False)
        if idx:
            self.comboBox_star_harmonics.setCurrentIndex(
                idx
            )  # restore ordinal number for the new winding
        self.update_plot_in_GUI()
        self.reportEdit.setText(self.data.get_text_report())

    def update_plot_in_GUI(self, small_update=False):
        """
        update the current figure
        if 'small_update' is True, only new lines/bars are plottet and not the 
        all axes etc. --> speed up, for MMK-phase slider for example
        """
        # Update Figures
        if self.plot_tabs.currentWidget():  # if all tabs are closed
            tab_name = self.plot_tabs.currentWidget().objectName()
            if tab_name == "tab_slot":
                self.fig[tab_name].plot_slots(self.data.get_num_slots())
                self.fig[tab_name].plot(
                    self.data, draw_poles=config["plt"]["draw_poles"]
                )
            if tab_name == "tab_layout_polar":
                self.fig[tab_name].plot(
                    self.data,
                    optimize_overhang=self.checkBox_opt_wdg_overhang_layout_polar.isChecked(),
                    draw_poles=config["plt"]["draw_poles"],
                )
            if tab_name == "tab_overhang":
                self.fig[tab_name].plot(
                    self.data,
                    optimize_overhang=self.checkBox_opt_wdg_overhang.isChecked(),
                )
            if tab_name == "tab_star":
                self.fig[tab_name].plot(
                    self.data,
                    harmonic_idx=self.comboBox_star_harmonics.currentIndex(),
                    ForceX=self.checkBoxForceX.isChecked(),
                )
            if tab_name == "tab_wf":
                if self.radioButton_electrical.isChecked():
                    self.fig[tab_name].plot(self.data, mechanical=False)
                elif self.radioButton_mechanical.isChecked():
                    self.fig[tab_name].plot(self.data, mechanical=True)
            if tab_name == "tab_mmk":
                f = _get_float(self.MMK_phase_edit.text())
                f = 0.0 if f is None else f
                self.fig[tab_name].plot(self.data, f, small_update=small_update)

    def printer(self):
        printer = QPrinter(QPrinter.HighResolution)

        dialog = QPrintDialog(printer)

        # get actual view
        tab_name = self.plot_tabs.currentWidget().objectName()
        if tab_name in [
            "tab_slot",
            "tab_layout_polar",
            "tab_overhang",
            "tab_star",
            "tab_wf",
            "tab_mmk",
        ]:
            with tempfile.TemporaryDirectory() as tmpdir:
                self.fig[tab_name].save(
                    os.path.join(tmpdir, "fig.png"), config["plt"]["res"]
                )
                pixmap = QPixmap(os.path.join(tmpdir, "fig.png"))
                if dialog.exec_() == QPrintDialog.Accepted:
                    painter = QPainter(printer)

                    rect = painter.viewport()
                    size = pixmap.size()
                    size.scale(rect.size(), QtCore.Qt.KeepAspectRatio)
                    painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
                    painter.setWindow(pixmap.rect())
                    painter.drawPixmap(0, 0, pixmap)
                    del painter

        elif tab_name == "tab_report":
            if self.reportEdit.textCursor().hasSelection():
                dlg.addEnabledOption(QPrintDialog.PrintSelection)
            if dialog.exec_() == QPrintDialog.Accepted:
                self.reportEdit.print_(printer)
        else:
            print("printing not supported for the current content")
        del dialog

    def plot_tabs_init(self):
        self.plot_tabs_store()
        for k in range(self.plot_tabs.count()):
            self.plot_tabs_remove(0)

        pt = config["view"]["plot_tabs"]
        for p in pt:
            self.plot_tabs_add(p, update_menu=True)
        #  self.plot_tabs.setTabVisible(0, False)
        self.plot_tabs.setCurrentIndex(0)

    def plot_tabs_store(self):
        self.plot_tabs_store = {}
        for k in range(self.plot_tabs.count()):
            tab = self.plot_tabs.widget(k)
            self.plot_tabs_store[tab.objectName()] = {}
            self.plot_tabs_store[tab.objectName()]["widget"] = self.plot_tabs.widget(k)
            self.plot_tabs_store[tab.objectName()]["icon"] = self.plot_tabs.tabIcon(k)
            self.plot_tabs_store[tab.objectName()]["label"] = self.plot_tabs.tabText(k)

    def plot_tabs_update_menu(self, key, flag):
        self.setUpdatesEnabled(False)  # block signals
        self.plot_tabs_actions[key].setChecked(flag)
        self.setUpdatesEnabled(True)  # unblock signals

    def plot_tabs_add(self, key, update_menu=False):
        self.plot_tabs.addTab(
            self.plot_tabs_store[key]["widget"], self.plot_tabs_store[key]["label"]
        )
        idx = self.plot_tabs.count()
        self.plot_tabs.setTabIcon(idx - 1, self.plot_tabs_store[key]["icon"])
        if update_menu:
            self.plot_tabs_update_menu(key, True)
        self.plot_tabs.setCurrentIndex(self.plot_tabs.count() - 1)

    def plot_tabs_remove(self, idx, update_menu=True):
        """
        Remove tabs by index
        """
        key = self.plot_tabs.widget(idx).objectName()
        self.plot_tabs.removeTab(idx)

        #  print('remove', key, idx)
        if update_menu:
            self.plot_tabs_update_menu(key, False)

    def plot_tabs_remove_by_name(self, key, update_menu=True):
        """
        Remove tabs by name
        """
        for k in range(self.plot_tabs.count()):
            widget = self.plot_tabs.widget(k)
            if widget is not None:
                if widget.objectName() == key:
                    self.plot_tabs_remove(k, update_menu=update_menu)

    def plot_tabs_update_from_menu(self):
        """
        remove/add tabs depended on the menu
        """
        checked = []  # checks from menu
        for key, value in self.plot_tabs_actions.items():
            if value.isChecked():
                checked.append(key)

        checked2 = []  # active tabs
        for k in range(self.plot_tabs.count()):
            checked2.append(self.plot_tabs.widget(k).objectName())

        # activate tabs to sync with menu
        for c in checked:
            if c not in checked2:
                self.plot_tabs_add(c)

        # deactivate tabs to sync with menu
        for c in checked2:
            if c not in checked:
                self.plot_tabs_remove_by_name(c)

    def plot_tabs_show_all(self):
        for k in range(self.plot_tabs.count()):
            self.plot_tabs_remove(0)
        default_config = get_config(default=True)
        for tab in default_config["view"]["plot_tabs"]:
            self.plot_tabs_add(tab, update_menu=True)
        self.plot_tabs.setCurrentIndex(0)

    def plot_tabs_save_config(self):
        checked = []
        for k in range(self.plot_tabs.count()):
            checked.append(self.plot_tabs.widget(k).objectName())
        config["view"]["plot_tabs"] = checked
        save_config(config)

    def save_to_file(self):
        """
        returns True if file is saved
        """
        if not self.project.filename:
            ret = self.save_as_to_file()
            return ret
        else:
            self.project.save_to_file(self.project.filename)
            self.statusbar.showMessage(
                "Project saved as " + self.project.filename, MSG_TIME
            )
            self.check_is_saved()
            return True

    def save_as_to_file(self):
        """
        returns True if file is saved
        """
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save winding file", "", "Winding Files (*.wdg)", options=options
        )
        if filename:
            if not filename.endswith(".wdg"):
                filename += ".wdg"
            self.project.set_filename(filename)
            self.project.save_to_file(self.project.filename)
            self.statusbar.showMessage(
                "Project saved as " + self.project.filename, MSG_TIME
            )
            self.check_is_saved()
            return True
        else:
            return False

    def load_from_file(self, filename=None):
        """
        loads a *.wdg file in the workspace
        if filename is not given a file dialog appears
        """
        if not filename:
            if not self.project.get_save_state():
                ok = QMessageBox.question(
                    self,
                    "Load *.wdg file",
                    "Do you want to save?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                    QMessageBox.Cancel,
                )
                if ok == QMessageBox.Yes:
                    ret = self.save_to_file()
                    if not ret:  # user has not saved
                        return
                if ok == QMessageBox.Cancel:  # cancel
                    return

            options = QFileDialog.Options()
            filename, _ = QFileDialog.getOpenFileName(
                self, "Open winding file", "", "Winding Files (*.wdg)", options=options
            )
        if filename:
            self.project.load_from_file(filename)
            self.statusbar.showMessage("Project loaded: " + filename, MSG_TIME)
            self.project.set_filename(filename)
            self.update_project_list()
            self.update_data_in_GUI()
        self.check_is_saved()

    def tasks_on_exit(self):
        """
        Do some taske when the main window is closed
        """
        self.plot_tabs_save_config()

    def closeEvent(self, event):
        # Exit programm

        # Ask for saving
        if self.project.get_save_state():
            self.tasks_on_exit()
            event.accept()  # let the window close
        else:
            ok = QMessageBox.question(
                self,
                "Exit program",
                "Do you want to save?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if ok == QMessageBox.Yes:
                ret = self.save_to_file()
                if ret:  # user has saved
                    self.tasks_on_exit()
                    event.accept()  # let the window close
                else:  # user has not saved
                    event.ignore()
            elif ok == QMessageBox.No:
                self.tasks_on_exit()
                event.accept()  # close the window
            else:
                event.ignore()  # let the window open

    def open_manual(self):
        doc = os.path.join(__dir__, "doc", "SWAT-EM_manual.pdf")
        if platform.system() == "Darwin":  # macOS
            subprocess.call(("open", doc))
        elif platform.system() == "Windows":  # Windows
            os.startfile(doc)
        else:  # linux variants
            subprocess.call(("xdg-open", doc))

    def create_report(self):
        rep = report.HtmlReport(self.data)
        rep.create()
        rep.open_in_browser()

    def export_to_excel(self):
        """
        Export to excel
        """
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save to Excel file", "", "Excel (*.xlsx)", options=options
        )
        if filename:
            if not filename.endswith(".xlsx"):
                filename += ".xlsx"
            self.data.export_xlsx(filename)

    def export_to_txt(self):
        """
        Export text report
        """
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save to Text file", "", "Text (*.txt)", options=options
        )
        if filename:
            if not filename.endswith(".txt"):
                filename += ".txt"
            self.data.export_text_report(filename)

    def set_focus_to_find(self):
        self.plot_tabs.setCurrentWidget(self.tab_report)
        self.lineEdit_find.setFocus()

    def find_in_report(self):
        num_found = self.report.find(self.lineEdit_find.text())
        if num_found == -1:
            self.lineEdit_find.setStyleSheet("background-color: #FF0000")
        else:
            self.lineEdit_find.setStyleSheet("background-color: #FFFFFF")


def main():
    # command line options
    parser = argparse.ArgumentParser(
        prog="SWAT-EM",
        description="Generating and evaluating of windings for electrial machines",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        action="store",
        nargs="?",
        default="",
        dest="arg_1",
        help="*.py scriptfile or *.wdg file",
    )
    parser.add_argument(
        "--load",
        action="store",
        default="",
        dest="loadfile",
        help="Open an existing *.wdg file",
    )
    parser.add_argument(
        "--script",
        action="store",
        default="",
        dest="scriptfile",
        help="Open an existing *.py script file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + __version__,
        help="Show version",
    )
    args = parser.parse_args()

    if len(args.arg_1) > 0:
        #  print('my arg: ', args.arg_1)
        ext = os.path.splitext(args.arg_1)[-1]
        if ext.upper() == ".PY":
            args.scriptfile = args.arg_1
        elif ext.upper() == ".WDG":
            args.loadfile = args.arg_1

    if args.scriptfile:
        print("eval script file:", args.scriptfile)
    else:
        print("running GUI")
        # app = QApplication(sys.argv)
        ex = MainWindow()

        if args.loadfile:
            if os.path.isfile(args.loadfile):
                ex.load_from_file(args.loadfile)
            else:
                raise (Exception, "file not found:".format(args.loadfile))
        splash.close()
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
