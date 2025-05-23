import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtGui import QPainter, QFont, QPen
from PyQt5.QtCore import Qt, QRect


class Overlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(parent.size())
        self.scores = [0] * 7

    def set_scores(self, scores):
        self.scores = scores
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.setPen(QPen(Qt.green))

        col_count = len(self.scores)
        col_width = self.width() // col_count

        for i, score in enumerate(self.scores):
            text = f"{score:.0f}%"
            painter.drawText(
                QRect(i * col_width, self.height() - 20, col_width, 20),
                Qt.AlignCenter,
                text
            )


class BoardArea(QWidget):
    def __init__(self):
        super().__init__()
        self.rows = 6
        self.cols = 7
        self.cell_size = 60
        self.setFixedSize(self.cols * self.cell_size, self.rows * self.cell_size)
        self.overlay = Overlay(self)
        self.overlay.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(Qt.black, 2))

        for row in range(self.rows):
            for col in range(self.cols):
                x = col * self.cell_size
                y = row * self.cell_size
                painter.drawRect(x, y, self.cell_size, self.cell_size)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("可视化棋盘 + 提示分数")
        layout = QVBoxLayout()

        self.board = BoardArea()
        layout.addWidget(self.board)

        btn = QPushButton("更新提示")
        btn.clicked.connect(self.update_scores)
        layout.addWidget(btn)

        self.setLayout(layout)
        self.resize(460, 460)

    def update_scores(self):
        import random
        scores = [random.randint(0, 100) for _ in range(7)]
        self.board.overlay.set_scores(scores)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
