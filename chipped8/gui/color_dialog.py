from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout,
    QWidget, QHBoxLayout, QPushButton, QColorDialog, QLabel
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCore import Qt, Signal

class ColorPresetWidget(QWidget):
    clicked = Signal(list)

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.setFixedSize(220, 50)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.colors)

    def paintEvent(self, event):
        painter = QPainter(self)
        width = self.width() // 4
        for i, color in enumerate(self.colors):
            painter.setBrush(QColor(color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(i * width, 0, width, self.height())

class ColorSwatch(QWidget):
    clicked = Signal()

    def __init__(self, color='#cccccc', parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(160, 80)
        self.setCursor(Qt.PointingHandCursor)

    def set_color(self, color):
        self.color = QColor(color)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Open QColorDialog to pick a color
            new_color = QColorDialog.getColor(self.color, self, 'Select Color')
            if new_color.isValid():
                self.set_color(new_color.name())
                self.clicked.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setBrush(self.color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

class ColorSelectorDialog(QDialog):

    def __init__(self, color_1='#cccccc', color_2='#cccccc', color_3='#cccccc', color_4='#cccccc'):
        super().__init__()

        self.setWindowTitle('Select Color')
        self.resize(700, 350)

        # Store selected colors from initialization
        selected_colors = [color_1, color_2, color_3, color_4]

        # Presets
        self.presets = [
            ['#0f052d', '#203671', '#36868f', '#5fc75d'], # Default
            ['#9bbc0f', '#306230', '#0f380f', '#8bac0f'], # Gameboy
            ['#f8f8f8', '#545454', '#a80020', '#c8c8c8'], # NES
            ['#40318d', '#6c5eb5', '#b8c76f', '#ffffff'], # C64
            ['#fdf0d5', '#b10f2e', '#720026', '#ffba08'], # Famicom
            ['#ffffff', '#000000', '#aaaaaa', '#666666'], # Mac Classic
            ['#000000', '#ffffff', '#d62828', '#3a86ff'], # ZX Spectrum
            ['#000000', '#c0c0c0', '#00ffff', '#ff00ff'], # MS-DOS ANSI
            ['#f0f0f0', '#2d2d2d', '#e63946', '#457b9d'], # SNES
        ]

        main_layout = QVBoxLayout(self)

        # Presets layout
        grid = QGridLayout()

        for i, preset_colors in enumerate(self.presets):
            preset_widget = ColorPresetWidget(preset_colors)
            preset_widget.clicked.connect(self.on_preset_clicked)
            grid.addWidget(preset_widget, i // 3, i % 3)

        main_layout.addWidget(QLabel('Presets:'))
        main_layout.addLayout(grid)

        main_layout.addSpacing(64)

        # Swatches layout
        swatch_layout = QHBoxLayout()
        self.swatches = []

        for color in selected_colors:
            swatch = ColorSwatch(color)
            swatch_layout.addWidget(swatch)
            self.swatches.append(swatch)

        main_layout.addWidget(QLabel('Your Colors:'))
        main_layout.addLayout(swatch_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        self.ok_button = QPushButton('OK')
        self.ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(cancel_button)
        main_layout.addLayout(buttons_layout)

        # Don't let the window be resized
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowMaximizeButtonHint)
        self.setFixedSize(self.sizeHint())

    def on_preset_clicked(self, colors):
        for swatch, color in zip(self.swatches, colors):
            swatch.set_color(color)

    def get_colors(self):
        return [swatch.color.name() for swatch in self.swatches]
