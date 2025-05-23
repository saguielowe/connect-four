# -*- coding: utf-8 -*-
"""
Created on Sat May  3 11:01:09 2025

@author: 23329
"""

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from Winrate_bar import WinrateBar
from replay import ReplayGame
class GameHistory(QWidget):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("历史对局")
        self.resize(1000, 800)
        self.setFont(QFont("微软雅黑", 12))

        self.layout = QVBoxLayout(self)
        # 顶部用户信息
        self.label_name = QLabel("用户名")
        self.label_name.setText(self.username)
        with open(f"userdata/{username}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.data = data
        if data["stats"]["games_played"] != 0:
            winrate = data["stats"]["games_won"] / data["stats"]["games_played"]
        if data["stats"]["games_played"] < 10:
            self.xp = "青铜"
        elif data["stats"]["games_played"] < 30 and winrate >= 0.2:
            self.xp = "白银"
        elif data["stats"]["games_played"] < 50 and winrate >= 0.4:
            self.xp = "黄金"
        elif data["stats"]["games_played"] < 100 and winrate >= 0.5:
            self.xp = "铂金"
        elif data["stats"]["games_played"] >= 100 and winrate < 0.6:
            self.xp = "钻石"
        elif data["stats"]["games_played"] >= 100 and winrate >= 0.6:
            self.xp = "黑钻"
        self.label_level = QLabel()
        self.label_level.setText("等级："+self.xp)
        self.label_games = QLabel("已下局数：0")
        self.label_games.setText("已下局数："+str(data["stats"]["games_played"]))
        self.label_winrate = QLabel("胜率：100%")
        if data["stats"]["games_played"] == 0:
            self.label_winrate.setText("胜率：NaN")
        else:
            self.label_winrate.setText("胜率：" + str(data["stats"]["games_won"] * 100 // data["stats"]["games_played"]) +"%")
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.label_name)
        top_layout.addWidget(self.label_level)
        top_layout.addWidget(self.label_games)
        top_layout.addWidget(self.label_winrate)
        self.layout.addLayout(top_layout)
        
        self.games_stats = WinrateBar()
        self.label_games = QLabel()
        self.games_stats.set_ratios(data["stats"]["games_won"] / data["stats"]["games_played"], data["stats"]["games_lost"] / data["stats"]["games_played"])
        wins = data["stats"]["games_won"]
        loss = data["stats"]["games_lost"]
        draws = data["stats"]["games_played"] - wins - loss
        self.label_games.setText(f"胜利局数: {wins}   平局: {draws}   失败局数: {loss}")
        self.layout.addWidget(self.games_stats)
        self.layout.addWidget(self.label_games)
        
        # 表格部件
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["对手", "对手等级", "时间", "先手", "结果", "步数"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.layout.addWidget(self.table)

        # 按钮区域
        self.button_layout = QHBoxLayout()
        self.replay_btn = QPushButton("复盘")
        self.delete_btn = QPushButton("删除")
        self.button_layout.addWidget(self.replay_btn)
        self.button_layout.addWidget(self.delete_btn)
        self.layout.addLayout(self.button_layout)

        # 加载历史数据
        self.load_history()

        # 连接槽函数
        self.replay_btn.clicked.connect(self.replay_selected_game)
        self.delete_btn.clicked.connect(self.delete_selected_game)

    def load_history(self):
        self.table.setRowCount(0)
        self.history_dir = "userdata/"
        files = sorted(
        f for f in os.listdir(self.history_dir)
        if f.startswith(f"{self.username}_") and f.endswith(".json")
        )
        for filename in files:
            if filename.endswith(".json"):
                path = os.path.join(self.history_dir, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    record = json.load(f)

                row = self.table.rowCount()
                result_text = ["平", "胜", "负"]
                self.table.insertRow(row)
                # 添加基本信息
                self.table.setItem(row, 0, QTableWidgetItem(record.get("player2", "")))
                self.table.setItem(row, 1, QTableWidgetItem(record.get("opponent_xp", "")))
                self.table.setItem(row, 2, QTableWidgetItem(record.get("timestamp", "")))
                self.table.setItem(row, 3, QTableWidgetItem(record.get("first_player", "")))
                self.table.setItem(row, 4, QTableWidgetItem(result_text[int(record.get("result", ""))]))
                self.table.setItem(row, 5, QTableWidgetItem(str(len(record.get("moves", "")))))

                # 把完整记录作为用户数据绑定在首列 item 上
                self.table.item(row, 0).setData(Qt.UserRole, (path, record))
        self.table.resizeColumnsToContents()

    def get_selected_record(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "提示", "请先选中一条记录")
            return None, None
        row = selected[0].row()
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole)

    def replay_selected_game(self):
        path, record = self.get_selected_record()
        if record:
            self.replay_window = ReplayGame(record)
            self.replay_window.show()

    def delete_selected_game(self):
        path, record = self.get_selected_record()
        if path:
            reply = QMessageBox.question(self, "确认删除", "确定要删除该对局记录吗？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    os.remove(path)
                    self.load_history()
                    QMessageBox.information(self, "删除成功", "记录已删除")
                except Exception as e:
                    QMessageBox.warning(self, "删除失败", f"发生错误：{e}")
