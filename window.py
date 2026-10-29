import sys
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFileDialog, QLineEdit, \
    QHBoxLayout, QCheckBox, QProgressBar, QMessageBox, QGroupBox, QComboBox
from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from pathlib import Path

# Імпорт ЯДРА
from transcribe import load_model, transcribe, write_clear, write_srt



class Worker(QThread):
    # оголошення сигналів
    progress = Signal(int)
    step = Signal(str)
    error = Signal(str)
    done = Signal()
    

    def __init__(self, video_path, out_path, write_txt:bool, write_srt:bool, language):
        super().__init__()
        self.video_path = video_path
        self.out_path = out_path
        self.write_txt = write_txt
        self.write_srt = write_srt
        self.language = language

    def on_progress(self, persent, text):
        self.progress.emit(int(persent))
        self.step.emit(text)

    def run(self):
        try:
            model = load_model(self.on_progress)
            segments = transcribe(model, self.video_path, self.on_progress, self.language)
            if self.write_txt:
                write_clear(segments, self.out_path)
            if self.write_srt:
                write_srt(segments, self.out_path)
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))




class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Параметри вікна
        self.setWindowTitle("Transcriber")
        self.resize(800, 300)
        self.setObjectName("main")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        bg = (base / "assets" / "wave_tile.png").as_posix()
        self.setStyleSheet(f"""
            #main {{
                background-color: #34373c;
                background-image: url({bg});
            }}
            QLabel, QCheckBox {{
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid #8a8f98;
                border-radius: 3px;
                background: #2b2d31;
            }}
            QCheckBox::indicator:checked {{
                background: #8AE1FC;
            }}
            QCheckBox::indicator:hover {{
                background: #D4B8C0;
            }}
            QPushButton {{
                color: #1B1718;
                border-radius: 3px;
                padding: 6px 14px;
                border: none;
                background: #DBE4FC;
            }}
            QPushButton:hover {{
                background: #B5ECFD;
            }}
            QPushButton:disabled{{
                background: #A09498;
            }}
            QProgressBar{{
                border-radius: 8px; 
                text-align: center;
                color: #6b7280;
                background: #0E0C0C;
            }}
            QProgressBar::chunk{{
                border-radius: 8px;
                background: #8AE1FC;
            }}
            QLineEdit{{
                border-radius: 8px;
                padding: 4px;
                background: #1B1718;
                color: white;
            }}
            QGroupBox{{
                background: rgba(30, 32, 36, 180);
            }}
        """)


        # Змінні класу
        self.video_path = None
        self.directory_path = None

        # Блок з ОГОЛОШЕННЯ
        # Написи у вікні(лейбли)
        self.label_of_file = QLabel("Тут з'явиться назва вибраного відео")
        self.label_of_directory = QLabel("Тут з'явиться шлях до місця збереження")
        self.steps_label = QLabel("Очікування запуску ⏳")

        # Лайни з елементів
        self.line_name_edit = QLineEdit()
        self.line_name_edit.setPlaceholderText('Введіть назву файлу')
        self.label_of_line = QLabel('Назва файлу (з результатом):')
        self.combox_line = QLabel('💬 Мова транскрибування:')


        self.progress = QProgressBar()

        # Кнопки
        self.choose_file_button = QPushButton("Вибрати файл 🔎")
        self.choose_directory_button = QPushButton("Вибрати папку 📁")
        self.main_button = QPushButton("Транскрибувати 🧿")
        self.open_folder_button = QPushButton("Відкрити папку 📂")
        self.open_folder_button.setEnabled(False)

        # Чекбокси
        self.text_checkbox = QCheckBox('Текст (.txt)')
        self.text_checkbox.setChecked(True)
        self.srt_checkbox = QCheckBox('Субтитри (.srt)')

        self.combox = QComboBox()
        self.combox.addItem("Українська", "uk")
        self.combox.addItem("English", "en")
        self.combox.addItem("Auto", None)

        layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        row3 = QHBoxLayout()
        row4 = QHBoxLayout()
        row5 = QHBoxLayout()
        group_layout1 = QVBoxLayout()
        group1 = QGroupBox('    ⚙️️ Вибір файлу та налаштування')


        # Блок з ДОДАВАННЯ у вікно
        # Блок з назвою файлу та шляхом
        group_layout1.addLayout(row1)
        row1.addWidget(self.label_of_file, stretch=1)
        row1.addWidget(self.choose_file_button)

        group_layout1.addLayout(row2)
        row2.addWidget(self.label_of_directory, stretch=1)
        row2.addWidget(self.choose_directory_button)


        # Блок редагування назви файлу
        group_layout1.addLayout(row3)
        row3.addWidget(self.label_of_line, stretch=1)
        row3.addWidget(self.line_name_edit, stretch=1)


        # Блок з чекбоксами
        group_layout1.addLayout(row4)
        row4.addWidget(self.text_checkbox)
        row4.addWidget(self.srt_checkbox)
        row4.addStretch()
        row4.addWidget(self.combox_line)
        row4.addWidget(self.combox)

        layout.addWidget(group1)
        layout.addStretch()

        # Блок з кнопками
        layout.addWidget(self.steps_label)
        layout.addWidget(self.progress)

        layout.addLayout(row5)
        row5.addStretch()
        row5.addWidget(self.main_button)
        row5.addWidget(self.open_folder_button)
        row5.addStretch()


        group1.setLayout(group_layout1)
        self.setLayout(layout)

        # Призначення дій кнопкам
        self.choose_file_button.clicked.connect(self.choose_video)
        self.choose_directory_button.clicked.connect(self.choose_directory)
        self.main_button.clicked.connect(self.transcribe_video)
        self.open_folder_button.clicked.connect(self.open_folder)



    # Визначення початкової директорії
    def start_dir(self):
        return str(self.directory_path) if self.directory_path else str(Path.home())

    # Вибір відео для транскрибування
    def choose_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Вибір файлу", self.start_dir(), "Відео (*.mp4 *.mov *.mkv);;Усі файли (*)")
        if not path:
            return
        self.video_path = Path(path)
        self.directory_path = self.video_path.parent
        self.label_of_file.setText(f"Вибрано відео: {self.video_path.name}")
        self.label_of_directory.setText(f"Шлях до місця збереження: {self.directory_path}")
        self.set_default_name()

    # Вибір місця для збереження файлів
    def choose_directory(self):
        directory_path = QFileDialog.getExistingDirectory(self, "Вибір папки", self.start_dir())
        if not directory_path:
            return

        self.directory_path = Path(directory_path)
        self.label_of_directory.setText(f"Шлях до місця збереження: {self.directory_path}")

    # Встановлення назви файлу по замовчанню
    def set_default_name(self):
        self.line_name_edit.setText(self.video_path.stem)

    # Транскрибування відео
    def transcribe_video(self):
        if not self.video_path:
            QMessageBox.warning(self, "ПОМИЛКА", "Відео не вибрано!")
            return
        if not self.text_checkbox.isChecked() and not self.srt_checkbox.isChecked():
            QMessageBox.warning(self, "ПОМИЛКА", "Не вибрано формат файлу!")
            return

        name = self.line_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "ПОМИЛКА", "Відсутня назва файлу!")
            return

        self.result_dir = self.directory_path

        path = self.directory_path/name
        self.worker = Worker(self.video_path, path, self.text_checkbox.isChecked(), self.srt_checkbox.isChecked(), self.combox.currentData())
        self.worker.progress.connect(self.progress.setValue)
        self.worker.step.connect(self.steps_label.setText)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.done.connect(self.on_done)
        self.set_busy(True)
        self.open_folder_button.setEnabled(False)
        self.worker.start()

    # Виведення інформації про помилку
    def on_error(self, message):
        QMessageBox.critical(self, "ПОМИЛКА", message)

    # Дії при завершенні процесу (розблокування кнопки для відкриття папки з готовим файлом)
    def on_done(self):
        self.steps_label.setText("Готово")
        self.open_folder_button.setEnabled(True)

    # Відкриття папки з готовим файлом
    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.result_dir)))

    # Блокування кнопок під час процесу
    def set_busy(self, busy):
        busy_list = [self.choose_file_button, self.choose_directory_button, self.combox,
        self.main_button, self.text_checkbox, self.srt_checkbox, self.line_name_edit]
        for widget in busy_list:
            widget.setEnabled(not busy)

    # Розблокування кнопок після час
    def on_finished(self):
        self.set_busy(False)



if __name__ == "__main__":
    # Захист від повторного запуску вікна в упакованій програмі (macOS/Windows):
    # службові процеси multiprocessing виконуються тут і завершуються, не відкриваючи вікно
    import multiprocessing
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)

    import locale
    locale.setlocale(locale.LC_MESSAGES, "C")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())