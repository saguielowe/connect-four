# -*- coding: utf-8 -*-
"""
Created on Sun Apr 13 14:58:11 2025

@author: 23329
"""

import os
import json
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt

default_userdata = {
    "stats": {
        "games_played": 0,
        "games_won": 0,
        "games_lost": 0
    },
    "preferences": {
        "show_winrate": 1,
    }
}

class CreateUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建用户")
        self.setFixedSize(700, 400)
        self.setStyleSheet("font-size: 32px;")
        self.name_label = QLabel("用户名：")
        self.name_edit = QLineEdit()

        self.ok_button = QPushButton("确认")
        self.cancel_button = QPushButton("取消")

        self.ok_button.clicked.connect(self.accept_data)
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def accept_data(self):
        username = self.name_edit.text().strip()
        if not username:
            QMessageBox.warning(self, "错误", "用户名不能为空")
            return

        with open("userdata/users.json", "r+", encoding="utf-8") as f:
            data = json.load(f)
            if username in data["name"]:
                QMessageBox.warning(self, "错误", "用户名已存在")
                return
            data["name"].append(username)
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()

        # 创建该用户的 json 文件
        user_file = f"userdata/{username}.json"
        if not os.path.exists(user_file):
            with open(user_file, "w", encoding="utf-8") as uf:
                json.dump(default_userdata, uf, indent=2, ensure_ascii=False)

        self.accept()