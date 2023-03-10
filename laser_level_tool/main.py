import sys
import subprocess
from PySide6.QtWidgets import QMainWindow, QHeaderView, QAbstractItemView, QButtonGroup, QDoubleSpinBox, QRadioButton, QLabel, QGridLayout, QSpinBox, QFormLayout, QSlider, QVBoxLayout, QTableWidget, QPushButton, QComboBox, QGroupBox, QWidget, QHBoxLayout, QSplitter, QApplication
from PySide6.QtCore import Qt

import qdarktheme

from Widgets import PixmapWidget, Graph, AnalyserWidget, TableUnit
from utils import units_of_measurements
from Core import Core


# Define the main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Laser Level Webcam Tool")
        self.resize(1100, 650)

        self.setting_zero = False  # state if the GUI is setting zero
        self.replace_sample = False  # state if we are replcing a sample
        self.table_selected_index = 0  # we keep track of the index so we can reselect it

        self.core = Core()  # where all the magic happens

        # Set the main window layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Widgets
        left_splitter = QSplitter()
        middle_splitter = QSplitter()
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        sensor_feed_widget = QGroupBox("Sensor Feed")
        analyser_widget = QGroupBox("Analyser")
        sampler_widget = QGroupBox("Sampler")
        plot_widget = QGroupBox("Plot")

        # -- Sensor Feed --
        self.sensor_feed_widget = PixmapWidget()
        self.camera_combo = QComboBox()
        camera_device_settings_btn = QPushButton("Device Settings")
        sensor_layout = QVBoxLayout()
        sensor_layout.setContentsMargins(1, 6, 1, 1)
        sensor_form = QFormLayout()
        sensor_form.addRow("Camera", self.camera_combo)
        sensor_layout.addWidget(self.sensor_feed_widget)
        sensor_layout.addLayout(sensor_form)
        sensor_layout.addWidget(camera_device_settings_btn)
        sensor_feed_widget.setLayout(sensor_layout)

        # -- Analyser --
        self.analyser_widget = AnalyserWidget()
        self.smoothing = QSlider(Qt.Horizontal)
        self.smoothing.setRange(0, 200)
        self.smoothing.setTickInterval(1)
        analyser_form = QFormLayout()
        analyser_layout = QVBoxLayout()
        analyser_layout.setContentsMargins(1, 6, 1, 1)
        analyser_form.addRow("Smoothing", self.smoothing)
        analyser_layout.addWidget(self.analyser_widget)
        analyser_layout.addLayout(analyser_form)
        analyser_widget.setLayout(analyser_layout)

        # -- Sampler --
        self.subsamples_spin = QSpinBox()
        self.subsamples_spin.setRange(0, 9999)
        self.outlier_spin = QSpinBox()
        self.outlier_spin.setRange(0, 99)
        self.units_combo = QComboBox()
        self.units_combo.addItems(units_of_measurements.keys())
        self.units_combo.setCurrentIndex(1)
        self.sensor_width_spin = QDoubleSpinBox()
        self.zero_btn = QPushButton("Zero")
        self.sample_btn = QPushButton("Take Sample")
        self.replace_btn = QPushButton("Replace Sample")
        self.sample_btn.setDisabled(True)
        self.replace_btn.setDisabled(True)
        self.sample_table = QTableWidget()
        self.sample_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        sample_layout = QGridLayout()
        sample_layout.setContentsMargins(1, 1, 1, 1)
        sample_layout.addWidget(QLabel("Sub Samples #"), 0, 0, 1, 1, alignment=Qt.AlignRight)
        sample_layout.addWidget(self.subsamples_spin, 0, 1, 1, 1)
        sample_layout.addWidget(QLabel("Outlier Removal %"), 0, 2, 1, 1, alignment=Qt.AlignRight)
        sample_layout.addWidget(self.outlier_spin, 0, 3, 1, 1)
        sample_layout.addWidget(QLabel("Units"), 1, 0, 1, 1, alignment=Qt.AlignRight)
        sample_layout.addWidget(self.units_combo, 1, 1, 1, 1)
        sample_layout.addWidget(QLabel("Sensor Width (mm)"), 1, 2, 1, 1, alignment=Qt.AlignRight)
        sample_layout.addWidget(self.sensor_width_spin, 1, 3, 1, 1)
        sample_layout.addWidget(self.zero_btn, 2, 0, 1, 1)
        sample_layout.addWidget(self.sample_btn, 2, 1, 1, 2)
        sample_layout.addWidget(self.replace_btn, 2, 3, 1, 1)
        sample_layout.addWidget(self.sample_table, 3, 0, 1, 4)
        sampler_widget.setLayout(sample_layout)

        # -- Plot --
        self.graph_mode_group = QButtonGroup()
        self.raw_radio = QRadioButton("Raw")
        self.graph_mode_group.addButton(self.raw_radio)
        self.flat_radio = QRadioButton("Flattened")
        self.graph_mode_group.addButton(self.flat_radio)
        self.graph = Graph(self.core.samples)
        plot_layout = QVBoxLayout()
        plot_layout.setContentsMargins(0, 3, 0, 0)
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.raw_radio, alignment=Qt.AlignRight)
        radio_layout.addWidget(self.flat_radio)
        plot_layout.addLayout(radio_layout)
        plot_layout.addWidget(self.graph)
        plot_widget.setLayout(plot_layout)

        # Attach Widgets
        left_splitter.addWidget(sensor_feed_widget)
        left_splitter.addWidget(analyser_widget)
        right_splitter.addWidget(sampler_widget)
        right_splitter.addWidget(plot_widget)
        middle_splitter.addWidget(left_splitter)
        middle_splitter.addWidget(right_splitter)
        main_layout.addWidget(middle_splitter)

        # Logic
        middle_splitter.setSizes([300, 100])

        self.graph.samples = self.core.samples

        for cam in self.core.get_cameras():
            self.camera_combo.addItem(cam)

        self.core.set_camera(self.camera_combo.currentIndex())

        # Signals
        self.core.OnSensorFeedUpdate.connect(self.sensor_feed_widget.setPixmap)
        self.core.OnAnalyserUpdate.connect(self.analyser_widget.set_data)
        self.sensor_feed_widget.OnHeightChanged.connect(self.analyser_widget.setMaximumHeight)
        self.sensor_feed_widget.OnHeightChanged.connect(lambda value: setattr(self.core, "analyser_widget_height", value))
        self.smoothing.valueChanged.connect(lambda value: setattr(self.core.frameWorker, "analyser_smoothing", value))
        self.subsamples_spin.valueChanged.connect(lambda value: setattr(self.core, "subsamples", value))
        self.outlier_spin.valueChanged.connect(lambda value: setattr(self.core, "outliers", value))
        self.units_combo.currentTextChanged.connect(self.core.set_units)
        self.sensor_width_spin.valueChanged.connect(lambda value: setattr(self.core, "sensor_width", value))
        self.zero_btn.clicked.connect(self.zero_btn_cmd)
        self.sample_btn.clicked.connect(self.sample_btn_cmd)
        self.replace_btn.clicked.connect(self.replace_btn_cmd)
        self.core.OnSubsampleProgressUpdate.connect(self.subsample_progress_update)
        self.core.OnSampleComplete.connect(self.finished_subsample)
        self.core.OnSampleComplete.connect(self.update_table)
        self.core.OnUnitsChanged.connect(self.update_table)
        self.core.OnUnitsChanged.connect(self.graph.set_units)
        camera_device_settings_btn.clicked.connect(self.extra_controls)
        self.camera_combo.currentIndexChanged.connect(self.core.set_camera)
        self.graph_mode_group.buttonClicked.connect(self.update_graph_mode)
        self.sample_table.itemSelectionChanged.connect(self.hightlight_sample)

        # Trigger the state of things
        self.smoothing.setValue(50)
        self.subsamples_spin.setValue(10)
        self.outlier_spin.setValue(30)
        self.units_combo.setCurrentIndex(0)
        self.sensor_width_spin.setValue(5.9)
        self.raw_radio.setChecked(True)
        self.update_graph_mode()  # have to trigger it manually the first time

    def hightlight_sample(self):
        index = self.sample_table.currentRow()
        self.graph.set_selected_index(index)

    def extra_controls(self):
        cmd = f'ffmpeg -f dshow -show_video_device_dialog true -i video="{self.camera_combo.currentText()}"'
        subprocess.Popen(cmd, shell=True)

    def update_graph_mode(self):
        checked_button = self.graph_mode_group.checkedButton()
        self.graph.set_mode(checked_button.text())

    def update_table(self):
        units = self.core.units
        header_names = [f"Measured ({units})", f"Flattened ({units})", f"Scrape ({units})", f"Shim ({units})"]
        self.sample_table.setColumnCount(len(header_names))
        self.sample_table.setHorizontalHeaderLabels(header_names)
        header = self.sample_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Delete the rows
        self.sample_table.setRowCount(0)

        for sample in self.core.samples:
            # Check if there are enough rows in the table widget, and add a new row if necessary
            if sample.x >= self.sample_table.rowCount():
                self.sample_table.insertRow(sample.x)

            for col, val in enumerate([sample.y, sample.linYError, sample.shim, sample.scrape]):
                # measured value
                cell = TableUnit()
                cell.value = val
                cell.units = self.core.units
                self.sample_table.setItem(sample.x, col, cell)

        self.sample_table.selectRow(self.table_selected_index)
        self.graph.update(self.update_table)
        # unit_multiplier = units_of_measurements[self.core.units]

        # self.graph.set_data([self.core.sample_data * unit_multiplier, self.core.line_data * unit_multiplier, self.core.units])

    def finished_subsample(self):
        """
        Sample complete. Reset the GUI back to the default state
        """
        self.zero_btn.setEnabled(True)
        self.sample_btn.setEnabled(True)
        self.replace_btn.setEnabled(True)

        if self.setting_zero == True:
            self.zero_btn.setText("Zero")
            self.setting_zero = False
        else:
            if self.replace_sample:
                self.replace_btn.setText("Replace Sample")
                self.replace_sample = False
            else:
                self.sample_btn.setText("Take Sample")

    def subsample_progress_update(self, sample_total):
        """
        Progress update on either zero or sample button
        """
        sample = sample_total[0]
        total = sample_total[1]

        if self.setting_zero == True:
            self.zero_btn.setText(f"{sample}/{total}")
        else:
            self.sample_btn.setText(f"{sample}/{total}")

    def zero_btn_cmd(self):
        """
        Calls the sample button command but sets a flag so we know the GUI is in a state of setting the zero value
        """
        self.table_selected_index = 0

        self.setting_zero = True
        self.replace_sample = False
        self.zero_btn.setDisabled(True)
        self.sample_btn.setDisabled(True)
        self.replace_btn.setDisabled(True)

        self.core.samples[:] = []  # clear list in-place without changing it's reference
        self.graph.update(self.zero_btn_cmd)
        self.core.start_sample(self.setting_zero, replacing_sample=False, replacing_sample_index=None)

    def sample_btn_cmd(self):
        """
        Calls on Core to take a sample
        """
        self.table_selected_index = self.sample_table.currentRow()

        self.zero_btn.setDisabled(True)
        self.sample_btn.setDisabled(True)
        self.replace_btn.setDisabled(True)
        self.core.start_sample(self.setting_zero, replacing_sample=False, replacing_sample_index=None)

    def replace_btn_cmd(self):
        """
        Call for when we are replacing a sample
        """
        self.table_selected_index = self.sample_table.currentRow()

        self.zero_btn.setDisabled(True)
        self.sample_btn.setDisabled(True)
        self.replace_btn.setDisabled(True)
        index = self.sample_table.currentRow()
        self.core.start_sample(self.setting_zero, replacing_sample=True, replacing_sample_index=index)

    def closeEvent(self, event):
        self.core.workerThread.quit()
        self.core.workerThread.wait()
        self.core.sampleWorkerThread.quit()
        self.core.sampleWorkerThread.wait()
        self.deleteLater()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
