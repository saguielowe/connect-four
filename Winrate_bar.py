# -*- coding: utf-8 -*-
"""
Created on Fri May  2 11:25:41 2025

@author: 23329
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt

class WinrateBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.p_win = 0.0
        self.p_lose = 0.0
        self.setMinimumHeight(40)

    def set_ratios(self, win, lose):
        self.p_win = win
        self.p_lose = lose
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        win_width = int(w * self.p_win)
        lose_width = int(w * self.p_lose)
        draw_width = w - win_width - lose_width  # 保证总长度

        x = 0
        if win_width > 0:
            painter.setBrush(QColor("red"))
            painter.drawRect(x, 0, win_width, h)
            x += win_width

        if draw_width > 0:
            painter.setBrush(QColor("white"))
            painter.drawRect(x, 0, draw_width, h)
            x += draw_width

        if lose_width > 0:
            painter.setBrush(QColor("blue"))
            painter.drawRect(x, 0, lose_width, h)

        painter.end()
