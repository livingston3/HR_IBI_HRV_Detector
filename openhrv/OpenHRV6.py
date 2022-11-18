from PySide6.QtWidgets import (QMainWindow, QPushButton, QHBoxLayout,
                               QVBoxLayout, QWidget, QLabel, QComboBox,
                               QSlider, QGroupBox, QFormLayout, QCheckBox,
                               QFileDialog, QProgressBar, QGridLayout, 
                               QApplication, QLineEdit)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtGui import QIcon, QLinearGradient, QBrush, QGradient
import sys
from random import randint
from model_edited import Model
import pyqtgraph as pg
from utils import valid_address, valid_path
from datetime import datetime
from sensor_edited import SensorScanner, SensorClient
from logger import Logger

import resources    # noqa

class ViewSignals(QObject):
    """Cannot be defined on View directly since Signal needs to be defined on
    object that inherits from QObject"""
    annotation = Signal(tuple)
    start_recording = Signal(str)

# class ThirdWindow(QWidget):
    
#     def __init__(self, secondwin):
#         super().__init__()

#         self.secondwin = secondwin

#         self.setGeometry(300, 300, 750, 450)
#         self.setWindowTitle("Third Window")
        
#         layout = QVBoxLayout()
        
#         self.label = QLabel("Third Window % d" % randint(0,1000))
#         self.button = QPushButton("Push for the second window")
        
#         layout.addWidget(self.label)
#         layout.addWidget(self.button)
        
#         self.setLayout(layout)

#         self.button.clicked.connect(self.secondwin.show )
#         self.button.clicked.connect(self.hide )

class SecondWindow(QWidget):

    def __init__(self, homewin):
        super().__init__()
        
        self.homewin = homewin
        # self.thirdwin = ThirdWindow(self)

        # self.setGeometry(300, 300, 750, 450)
        # self.setWindowTitle("Second Window")

        # layout = QVBoxLayout()
        
        # self.label = QLabel("Second Window % d" % randint(0,1000))
        # self.button1 = QPushButton("Push for the first window")
        # self.button2 = QPushButton("Push for the third window")
        
        # layout.addWidget(self.label)
        # layout.addWidget(self.button1)
        # layout.addWidget(self.button2)
        
        # self.setLayout(layout)

        # self.button1.clicked.connect(self.homewin.show)
        # self.button1.clicked.connect(self.hide)

        # self.button2.clicked.connect(self.thirdwin.show)
        # self.button2.clicked.connect(self.hide)

        self.setWindowTitle("Data gathering for ML")
        self.setGeometry(150,150,300,450)

        line1_label = QLabel("User ID:")
        line1_lineedit = QLineEdit("")
        line2_label = QLabel("Select sound group")
        line2_combo = QComboBox()
        line2_combo.addItems(["One", "Two", "Three"])
        line3_label = QLabel("Play sound")
        line3_button = QPushButton("Play sound")
        line4_label = QLabel("Select emotion:")
        line4_combo = QComboBox()
        line4_combo.addItems(["One", "Two", "Three"])
        line5_label = QLabel("Emotion intensity:")
        line5_combo = QComboBox()
        line5_combo.addItems(["One", "Two", "Three"])
        line6_button = QPushButton("Submit")

        layout2 = QGridLayout()

        layout2.addWidget(line1_label, 0, 0)
        layout2.addWidget(line1_lineedit, 0, 1)
        layout2.addWidget(line2_label, 1, 0)
        layout2.addWidget(line2_combo, 1, 1)
        layout2.addWidget(line3_label, 2, 0)
        layout2.addWidget(line3_button, 2, 1)
        layout2.addWidget(line4_label, 3, 0)
        layout2.addWidget(line4_combo, 3, 1)
        layout2.addWidget(line5_label, 4, 0)
        layout2.addWidget(line5_combo, 4, 1)
        layout2.addWidget(line6_button, 5, 1)

        self.setLayout(layout2)

class MainWindow(QMainWindow):

    def __init__(self, model):
        super().__init__()

        self.model = model

        self.window2 = SecondWindow(self)

        self.setGeometry(60, 60, 900, 900)
        self.setWindowTitle("Connecting the Polar ECG Sensor")

        self.model.ibis_buffer_update.connect(self.plot_ibis)
        self.model.mean_hrv_update.connect(self.plot_hrv)
        self.model.hr_buffer_update.connect(self.plot_hr)
        self.model.addresses_update.connect(self.list_addresses)

        self.signals = ViewSignals()

        self.scanner = SensorScanner()
        self.scanner.sensor_update.connect(self.model.set_sensors)
        self.scanner.status_update.connect(self.show_status)

        self.sensor = SensorClient()
        self.sensor.ibi_update.connect(self.model.set_ibis_buffer)
        self.sensor.hr_update.connect(self.model.set_hr_buffer)
        self.sensor.status_update.connect(self.show_status)

        self.logger = Logger()
        self.logger_thread = QThread()
        self.logger.moveToThread(self.logger_thread)
        self.model.ibis_buffer_update.connect(self.logger.write_to_file)
        self.model.addresses_update.connect(self.logger.write_to_file)
        # self.model.pacer_rate_update.connect(self.logger.write_to_file)
        # self.model.hrv_target_update.connect(self.logger.write_to_file)
        self.model.hr_buffer_update.connect(self.logger.write_to_file)
        # self.model.biofeedback_update.connect(self.logger.write_to_file)
        self.signals.annotation.connect(self.logger.write_to_file)
        self.logger_thread.finished.connect(self.logger.save_recording)
        self.signals.start_recording.connect(self.logger.start_recording)
        # self.logger.recording_status.connect(self.show_recording_status)
        self.logger.status_update.connect(self.show_status)

#Inter beat interval
        self.ibis_plot = pg.PlotWidget()
        self.ibis_plot.setBackground("w")
        self.ibis_plot.setLabel("left", "Inter-Beat-Interval (msec)",
                                        **{"font-size": "18px"})
        self.ibis_plot.setLabel("bottom", "Seconds", **{"font-size": "18px"})
        self.ibis_plot.showGrid(y=True)
        self.ibis_plot.setYRange(300, 1500, padding=0)
        self.ibis_plot.setMouseEnabled(x=False, y=False)

        self.ibis_signal = pg.PlotCurveItem()
        pen = pg.mkPen(color=(0, 191, 255), width=7.5)
        self.ibis_signal.setPen(pen)
        self.ibis_signal.setData(self.model.ibis_seconds,
                                         self.model.ibis_buffer)
        self.ibis_plot.addItem(self.ibis_signal)

#Mean HRV
        self.mean_hrv_plot = pg.PlotWidget()
        self.mean_hrv_plot.setBackground("w")
        self.mean_hrv_plot.setLabel("left", "HRV (msec)",
                                        **{"font-size": "18px"})
        self.mean_hrv_plot.setLabel("bottom", "Seconds", **{"font-size": "18px"})
        self.mean_hrv_plot.showGrid(y=True)
        self.mean_hrv_plot.setYRange(0, 300, padding=0)
        self.mean_hrv_plot.setMouseEnabled(x=False, y=False)
        colorgrad = QLinearGradient(0, 0, 0, 1)    # horizontal gradient
        colorgrad.setCoordinateMode(QGradient.ObjectMode)
        colorgrad.setColorAt(0, pg.mkColor("g"))
        colorgrad.setColorAt(.5, pg.mkColor("y"))
        colorgrad.setColorAt(1, pg.mkColor("r"))
        brush = QBrush(colorgrad)
        self.mean_hrv_plot.getViewBox().setBackgroundColor(brush)

        self.mean_hrv_signal = pg.PlotCurveItem()
        pen = pg.mkPen(color="w", width=7.5)
        self.mean_hrv_signal.setPen(pen)
        self.mean_hrv_signal.setData(self.model.mean_hrv_seconds, self.model.mean_hrv_buffer)
        self.mean_hrv_plot.addItem(self.mean_hrv_signal)

#Heart rate
        self.hr_plot = pg.PlotWidget()
        self.hr_plot.setBackground("w")
        self.hr_plot.setLabel("left", "Heart Rate",
                                        **{"font-size": "18px"})
        self.hr_plot.setLabel("bottom", "Seconds", **{"font-size": "18px"})
        self.hr_plot.showGrid(y=True)
        self.hr_plot.setYRange(0, 160, padding=0)
        self.hr_plot.setMouseEnabled(x=False, y=False)
        colorgrad = QLinearGradient(0, 0, 0, 1)    # horizontal gradient
        colorgrad.setCoordinateMode(QGradient.ObjectMode)
        colorgrad.setColorAt(0, pg.mkColor("r"))
        colorgrad.setColorAt(.5, pg.mkColor("y"))
        colorgrad.setColorAt(1, pg.mkColor("g"))
        brush = QBrush(colorgrad)
        self.hr_plot.getViewBox().setBackgroundColor(brush)

        self.hr_signal = pg.PlotCurveItem()
        pen = pg.mkPen(color="w", width=7.5)
        self.hr_signal.setPen(pen)
        self.hr_signal.setData(self.model.hr_seconds, self.model.hr_buffer)
        self.hr_plot.addItem(self.hr_signal)


        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.scanner.scan)

        self.address_menu = QComboBox()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_sensor)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_sensor)

        self.next_label = QLabel("(If HRV and IBI are working please press next to continue)")
        self.next_button = QPushButton("Next")

        self.next_button.clicked.connect(self.hide)
        self.next_button.clicked.connect(self.window2.show)

        self.start_recording_button = QPushButton("Start")
        self.start_recording_button.clicked.connect(self.get_filepath)

        self.save_recording_button = QPushButton("Save")
        self.save_recording_button.clicked.connect(self.logger.save_recording)

        self.annotation = QComboBox()
        self.annotation.setEditable(True)    # user can add custom annotations (edit + enter)
        self.annotation.setDuplicatesEnabled(False)
        self.annotation_button = QPushButton("Annotate")
        self.annotation_button.clicked.connect(self.emit_annotation)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.recording_status_label = QLabel("Status:")
        self.recording_statusbar = QProgressBar()
        self.recording_statusbar.setRange(0, 1)

        self.statusbar = self.statusBar()

        self.vlayout0 = QVBoxLayout(self.central_widget)

        self.hlayout0 = QHBoxLayout()

        self.hlayout0.addWidget(self.ibis_plot, stretch=80)
        self.vlayout0.addLayout(self.hlayout0)
        self.vlayout0.addWidget(self.hr_plot)
        self.vlayout0.addWidget(self.ibis_plot)
        self.vlayout0.addWidget(self.mean_hrv_plot)

        self.hlayout1 = QHBoxLayout()

        self.device_config = QGridLayout()
        self.device_config.addWidget(self.scan_button, 0, 0)
        self.device_config.addWidget(self.address_menu, 0, 1)
        self.device_config.addWidget(self.connect_button, 1, 0)
        self.device_config.addWidget(self.disconnect_button, 1, 1)
        self.device_config.addWidget(self.next_label, 2, 0)
        self.device_config.addWidget(self.next_button, 2, 1)
        self.device_panel = QGroupBox("ECG Devices")
        self.device_panel.setLayout(self.device_config)
        self.hlayout1.addWidget(self.device_panel, stretch=25)

        self.recording_config = QGridLayout()
        self.recording_config.addWidget(self.start_recording_button, 0, 0)
        self.recording_config.addWidget(self.save_recording_button, 0, 1)
        self.recording_config.addWidget(self.recording_statusbar, 0, 2)
        self.recording_config.addWidget(self.annotation, 1, 0, 1, 2)    # row, column, rowspan, columnspan
        self.recording_config.addWidget(self.annotation_button, 1, 2)
        self.recording_panel = QGroupBox("Recording")
        self.recording_panel.setLayout(self.recording_config)
        self.hlayout1.addWidget(self.recording_panel, stretch=25)

        self.vlayout0.addLayout(self.hlayout1)

        self.logger_thread.start()

    def closeEvent(self, event):
        """Properly shut down all threads."""
        print("Closing threads...")

        self.sensor.disconnect_client()

        self.logger_thread.quit()
        self.logger_thread.wait()

    def get_filepath(self):
        current_time = datetime.now().strftime("%Y-%m-%d-%H-%M")
        default_file_name = f"OpenHRV_{current_time}.csv"
        file_path = QFileDialog.getSaveFileName(None, "Create file",
                                                default_file_name,
                                                options=QFileDialog.DontUseNativeDialog)[0]    # native file dialog not reliable on Windows (most likely COM issues)
        if not file_path:    # user cancelled or closed file dialog
            return
        if not valid_path(file_path):
            self.show_status("File path is invalid or exists already.")
            return
        # file_path = "C:/Users/Don/Desktop/Dissertation/Python Tests/OpenHRV-main/openhrv/HR.csv"
        self.signals.start_recording.emit(file_path)

    def connect_sensor(self):
        if not self.address_menu.currentText():
            return
        address = self.address_menu.currentText().split(",")[1].strip()    # discard device name
        if not valid_address(address):
            print(f"Invalid sensor address: {address}.")
            return
        sensor = [s for s in self.model.sensors if s.address().toString() == address]
        self.sensor.connect_client(*sensor)

    def disconnect_sensor(self):
        self.sensor.disconnect_client()

    def plot_ibis(self, ibis):
        self.ibis_signal.setData(self.model.ibis_seconds, ibis[1])

    def plot_hrv(self, hrv):
        self.mean_hrv_signal.setData(self.model.mean_hrv_seconds, hrv[1])

    def plot_hr (self, hr):
        self.hr_signal.setData(self.model.hr_seconds, hr[1])

    def list_addresses(self, addresses):
        self.address_menu.clear()
        self.address_menu.addItems(addresses[1])

    def show_recording_status(self, status):
        self.recording_statusbar.setRange(0, status)    # indicates busy state if progress is 0

    def show_status(self, status, print_to_terminal=True):
        self.statusbar.showMessage(status, 0)
        if print_to_terminal:
            print(status)

    def emit_annotation(self):
        self.signals.annotation.emit(("Annotation", self.annotation.currentText()))


def main():
    app = QApplication(sys.argv)
    model = Model()
    window1 = MainWindow(model)
    window1.show()
    app.exec()

if __name__ == '__main__':
    main()