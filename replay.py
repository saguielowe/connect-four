# -*- coding: utf-8 -*-
"""
Created on Sat May  3 12:25:51 2025

@author: 23329
"""

import sys, time, json, os, copy
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout,
    QGroupBox, QLabel, QCheckBox, QWidget, QHBoxLayout, QMessageBox, QProgressBar
)
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPixmap, QPen, QKeyEvent
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QTimer, QEvent
from ai_player import AI
from Winrate_bar import WinrateBar
# 为了避免卡顿，仅在落子时计算了胜率并更新4联信息
class ClickableLabel(QLabel):
    clicked = pyqtSignal(int, int)
    def __init__(self):
        super().__init__()
        self.rows = 6
        self.cols = 7
        self.cell_size = 60
        self.overlay = Overlay(self)
        self.overlay.show()

    def mousePressEvent(self, event):
        self.clicked.emit(event.x(), event.y())

class Overlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(parent.size())
        self.col_width = parent.width() // 8
        self.scores = [0] * 7

    def set_scores(self, col):
        self.scores = [0] * 7
        if col == None:
            return
        self.scores[col] = 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont("微软雅黑", 8, QFont.Bold))
        painter.setPen(QPen(Qt.green))

        for i, score in enumerate(self.scores):
            if score != 1:
                continue
            painter.drawText(
                QRect(i * self.col_width, self.height() - 20, self.col_width, 20),
                Qt.AlignCenter,
                "最佳列"
            )

class ReplayGame(QMainWindow):
    ROWS = 6
    COLS = 7

    def __init__(self, record): # record 从username_0XX.json提取来的内容
        super().__init__()
        # 界面基本信息
        self.autoplay = False
        self.simulating = False
        self.can_simulate = True
        self.board_correct = True #如果棋盘不正确无法使用复盘功能
        self.current_step = 0 # current_step指现在下完的一步
        self.player1 = record["player1"]
        self.player2 = record["player2"]
        self.first_player = record["first_player"]
        if self.first_player == self.player1:
            self.turn = 0
        else:
            self.turn = 1
        self.setWindowTitle(f"四子棋 （回放中）- {self.player1} vs {self.player2}")
        self.setGeometry(200, 200, 600, 500)
        self.setFont(QFont("微软雅黑", 12))
        self.cell_size = 60
        # 动画状态变量
        self.drop_row = None
        self.drop_col = None
        self.drop_y = 0
        self.drop_timer = QTimer()
        self.update_timer = QTimer()
        self.drop_timer.timeout.connect(self.animate_drop)
        self.update_timer.timeout.connect(self.step_forward)
        self.waiting = False #当正在绘制棋子动画时暂停落子行为
        # 初始化棋盘
        self.board = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]  # 0 空，1 玩家1，2 玩家2
        self.move_sequence = record["moves"]
        self.move_sequence_copy = copy.deepcopy(self.move_sequence)
        self.board_copy = copy.deepcopy(self.board)
        self.chains = []
        self.win_chain = None
        #整体上下布局，自上而下分别为，进度条、top_layout、status、mid_layout、bottom_layout
        main_layout = QVBoxLayout()
        self.winrate_bar = WinrateBar()
        self.label_winrate = QLabel()

        outer_layout = QVBoxLayout()
        outer_layout.addWidget(self.winrate_bar)
        outer_layout.addWidget(self.label_winrate)

        main_layout.addLayout(outer_layout)
        # 顶部：头像 + 名字  + 名字 + 头像
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("红方："+ self.player1))
        with open(f"userdata/{self.player1}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
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
        top_layout.addWidget(QLabel("等级："+ self.xp))
        top_layout.addStretch()
        top_layout.addWidget(QLabel("等级："+ record.get("opponent_xp", "")))
        top_layout.addWidget(QLabel("蓝方："+ self.player2))
        main_layout.addLayout(top_layout)

        mid1_layout = QHBoxLayout()
        mid2_layout = QHBoxLayout()
        self.status = QLabel(f"现在轮到 {self.first_player} 落子")
        self.label_steps_moved = QLabel(f"已下步数: 0/{len(self.move_sequence)}")
        mid1_layout.addWidget(self.status)
        mid1_layout.addWidget(self.label_steps_moved)
        main_layout.addLayout(mid1_layout)

        # 棋盘 Pixmap
        self.label_board = ClickableLabel()
        self.label_board.clicked.connect(self.handle_click)
        self.label_board.setPixmap(QPixmap(420, 360))
        self.label_board.setStyleSheet("background-color: white; border: 1px solid black;")
        self.ai = AI(self)
        self.label_board.overlay.set_scores(self.ai.hard_move(self.first_player))
        self.label_board.installEventFilter(self)
        mid2_layout.addWidget(self.label_board)

        # 控制区 GroupBox
        control_group = QGroupBox()
        control_layout = QVBoxLayout()
        
        step_layout = QHBoxLayout()
        self.button_next = QPushButton("下一步")
        self.button_next.clicked.connect(self.step_forward)
        self.button_pre = QPushButton("上一步")
        self.button_pre.clicked.connect(self.step_undo)
        step_layout.addWidget(self.button_next)
        step_layout.addWidget(self.button_pre)
        control_layout.addLayout(step_layout)
        
        self.button_autoplay = QPushButton("自动播放")
        self.button_autoplay.clicked.connect(self.auto_display)
        control_layout.addWidget(self.button_autoplay)
        
        self.button_undo_sim = QPushButton("撤销上一步模拟")
        self.button_undo_sim.clicked.connect(self.undo_sim)
        self.button_end_sim = QPushButton("结束模拟")
        self.button_end_sim.clicked.connect(self.end_sim)
        control_layout.addWidget(self.button_undo_sim)
        control_layout.addWidget(self.button_end_sim)
        
        self.checkbox_show_move = QCheckBox("显示步数")
        self.checkbox_show_move.stateChanged.connect(self.draw_moves)
        control_layout.addWidget(self.checkbox_show_move)
        control_group.setLayout(control_layout)
        mid2_layout.addWidget(control_group)

        main_layout.addLayout(mid2_layout)
        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)
        self.resize(800, 600)
        QTimer.singleShot(0, self.label_board.setFocus)
        self.draw_board()
        
    def keyPressEvent(self, event: QKeyEvent): # 重写函数监听按键按下情况，基本逻辑与点击相同
        print("Key pressed:", event.key())

        if event.key() == Qt.Key_Right:
            self.step_forward()
        elif event.key() == Qt.Key_Left:
            self.step_undo()
        elif event.key() == Qt.Key_Space:
            self.auto_display()
        
    def handle_click(self, x, y): #此函数直接响应用户点击事件，判断是否合法后绘制动画，并呼唤ai落子
        if self.can_simulate == False:
            return
        if self.waiting == True:
            QMessageBox.warning(self, "落子失败", "请等待动画完毕再落子")
            return
        if self.autoplay == True:
            QMessageBox.warning(self, "落子失败", "请先停止自动播放！")
            return
        col = x // self.cell_size
        if col < 0 or col >= self.COLS:
            QMessageBox.warning(self, "无效落子", "不存在该列，请重新点击")
            return
        if self.simulating == False: #此处表明从原始棋盘开始的第一步模拟
            self.move_sequence_copy = copy.deepcopy(self.move_sequence)
            self.board_copy = copy.deepcopy(self.board) # 与落子序列不同，board需要时时更新
            self.move_sequence = self.move_sequence_copy[:self.current_step]
            self.simulating = True
            self.board_correct = False
        self.drop_row = self.can_drop_piece(col, player=1) # 此句之后已落子，棋盘锁定
        if self.drop_row == -1:
            QMessageBox.warning(self, "无效落子", "该列已满，请换一列落子")
            return
        self.waiting = True # 玩家落子动画等待
        self.drop_piece_with_animation(self.drop_row, col, 2 - (len(self.move_sequence) + self.turn) % 2)  # 玩家落子动画
        self.ai = AI(self)
        self.ai.cal_winrate(-1, 2 - (len(self.move_sequence) + self.turn) % 2) # 此处可以在落子后但动画尚未停止前就完成胜率的更改
    
# =============================================================================
#     def ai_to_move(self):
#         if self.waiting == False and self.ai_autoplay == True:
#             if len(self.move_sequence) == 42:
#                 self.ai_timer.stop()
#                 self.ai_autoplay = False
#                 self.button_ai_autoplay.setText("开始AI接管")
#             self.ai_col = self.ai.hard_move(self.current_player)
#             if self.ai_col == None:
#                 self.ai_autodisplay() #此时必定ai_display为真，相当于停止了AI
#                 return
#             self.drop_row = self.can_drop_piece(self.ai_col, self.current_player)
#             self.drop_piece_with_animation(self.drop_row, self.ai_col, self.current_player)
#             self.waiting = True
#             self.current_player = 3 - self.current_player
# =============================================================================

    def can_drop_piece(self, col, player):
        #此函数返回能否在col列落子，若能则更新board数据且返回能下的行
        for row in reversed(range(self.ROWS)):
            if self.board[row][col] == 0:
                self.board[row][col] = 3 #3表示已锁定
                self.move_sequence.append((row, col))
                self.update_info()
                return row #此函数每落一个子只能调用一次！
        return -1

    def drop_piece(self): # 此函数根据move_sequence执行一步落子，并启动动画
        row, col = self.move_sequence[self.current_step]
        self.waiting = True
        if self.current_step < len(self.move_sequence):
            self.current_step += 1
        self.drop_piece_with_animation(row, col, 2 - (self.current_step + self.turn) % 2)  # 玩家落子动画
        self.update_info()
        self.label_board.setFocus()
    
    def drop_piece_with_animation(self, row, col, player_id): #此函数开始动画
        self.drop_row = row
        self.drop_col = col
        self.drop_player = player_id
        self.drop_y = -1  # 起始高度
        self.drop_timer.start(15)  # 每15ms更新一次 
    
    def animate_drop(self): #此函数控制动画，动画停止后更新board数据
        cell_height = self.label_board.height() // self.ROWS
        self.drop_y += 10  # 每帧下落 10px
        target_y = self.drop_row * cell_height
        if self.drop_y >= target_y: #动画停止判断，并绘制提示
            self.drop_timer.stop()
            self.board[self.drop_row][self.drop_col] = self.drop_player
            self.board_hint() #动画结束后整个棋盘进入稳定状态再进行提示
            self.draw_board()
            self.ai = AI(self)
            if self.simulating == False: #使用回放算法
                self.ai.cal_winrate(-1, 2 - (self.current_step + self.turn) % 2)
                self.label_board.overlay.set_scores(self.ai.hard_move(2 - (self.current_step + self.turn) % 2))
            else:
                self.ai.cal_winrate(-1, 2 - (len(self.move_sequence) + self.turn) % 2)
                self.label_board.overlay.set_scores(self.ai.hard_move(2 - (len(self.move_sequence) + self.turn) % 2))
            self.waiting = False
        else:
            self.draw_board(animated=True)
    
    def draw_board(self, animated=False): # 此函数功能不会有错误，可放心使用
        #根据当前label的大小最大化正方形棋盘格子大小
        label_size = self.label_board.size()
        cell_width = label_size.width() // self.COLS
        cell_height = label_size.height() // self.ROWS
        self.cell_size = max(min(cell_width, cell_height), self.cell_size)
        #用pixmap绘制棋盘，先画格子，再画棋子，最后根据需要标序数
        board_pix = QPixmap(self.cell_size * self.COLS, self.cell_size * self.ROWS)
        board_pix.fill(Qt.white)
        painter = QPainter(board_pix)
        for row in range(self.ROWS):
            for col in range(self.COLS):
                x = col * self.cell_size
                y = row * self.cell_size
                painter.setPen(Qt.black)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(x, y, self.cell_size, self.cell_size)
                #先画格子，再根据当前棋子情况绘制棋子，记得清空brush！
                piece = self.board[row][col]
                if piece == 1 or piece == 2:
                    color = QColor("red") if piece == 1 else QColor("blue")
                    if (row, col) in set(self.chains): #如果需要提示则描边+半透明
                        painter.setPen(QPen(color, 4))
                        if piece == 1:
                            painter.setBrush(QBrush(QColor(255,0,0,80)))
                        else:
                            painter.setBrush(QBrush(QColor(0,0,255,80)))
                    else:
                        painter.setPen(Qt.white)
                        painter.setBrush(QBrush(color))
                    painter.drawEllipse(x + 5, y + 5, self.cell_size - 10, self.cell_size - 10)
                    if self.win_chain:
                        (r1, c1), (r2, c2), (r3, c3), (r4, c4) = self.win_chain
                        x_start = c1 * self.cell_size + self.cell_size // 2
                        y_start = r1 * self.cell_size + self.cell_size // 2
                        x_end = c4 * self.cell_size + self.cell_size // 2
                        y_end = r4 * self.cell_size + self.cell_size // 2
                        color = QColor("red") if self.board[r1][c1] == 1 else QColor("blue")
                        pen = QPen(color)
                        pen.setStyle(Qt.DashLine)
                        pen.setWidth(10)
                        painter.setPen(pen)
                        painter.drawLine(x_start, y_start, x_end, y_end)
        
        if self.checkbox_show_move.isChecked(): #如果需要标序数
            for index, (row, col) in enumerate(self.move_sequence):
                num_str = str(index + 1)
                x = col * self.cell_size + self.cell_size // 2
                y = row * self.cell_size + self.cell_size // 2
                # 设置字体颜色（对比背景）self.turn = 0 
                painter.setPen(Qt.white if index % 2 == 1 - self.turn else Qt.black)
                painter.setBrush(Qt.NoBrush)
                text_font = QFont("微软雅黑")
                text_font.setPointSize(int(self.cell_size*0.2))
                if index >= self.current_step:
                    if self.simulating == True:
                        text_font.setItalic(True)
                        painter.setPen(Qt.yellow if index % 2 == 1 - self.turn else Qt.green) # 前者蓝后者红
                    else:
                        break
                painter.setFont(text_font)
                # 构造一个 QRect 区域，代表这个格子的位置
                text_rect = QRect(x - self.cell_size // 2, y - self.cell_size // 2, self.cell_size, self.cell_size)
                painter.drawText(text_rect, Qt.AlignCenter, num_str)
#这里绘制动画棋子，动画的实现原理就是每隔15ms绘制一次，这颗棋子的位置不定，且不保留
        if animated and self.drop_row is not None:
            col = self.drop_col
            x = col * self.cell_size
            y = self.drop_y
            color = QColor("red") if self.drop_player == 1 else QColor("blue")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.black)
            painter.drawEllipse(x + 5, y + 5, self.cell_size - 10, self.cell_size - 10)
        
        painter.end()
        self.label_board.setPixmap(board_pix)
    
    def draw_moves(self):
        if self.waiting == True: #正在绘制动画，场上有临时棋子，比较混乱，不允许切换
            QMessageBox.warning(self, "更改失败", "请等待动画完毕再更改")
        else:
            self.draw_board(animated=False)
    
    def update_info(self):
        if self.simulating == False:
            if (self.current_step + self.turn) % 2 == 0:
                next_person = self.player1
            else:
                next_person = self.player2
            self.status.setText(f"现在轮到 {next_person} 落子")
            self.label_steps_moved.setText(f"已下步数: {self.current_step} / {len(self.move_sequence)}")
        else:
            if 2 - (len(self.move_sequence) + self.turn) % 2 == 1:
                next_person = self.player2
            else:
                next_person = self.player1
            self.status.setText(f"模拟中，现在轮到 {next_person} 落子")
            self.label_steps_moved.setText(f"已下步数: {self.current_step} / {len(self.move_sequence_copy)}")
    
    def step_forward(self):
        if self.waiting == True:
            QMessageBox.warning(self, "操作失败", "请等待动画完毕再步进")
            return
        if self.simulating == True or self.board_correct == False:
            QMessageBox.warning(self, "操作失败", "无法步进，请回到真实棋局后再试！")
            return
        if self.current_step == len(self.move_sequence):
            QMessageBox.warning(self, "操作失败", "已是最后一步！")
            if self.autoplay == True:
                self.update_timer.stop()
                self.autoplay = False
                self.button_autoplay.setText("自动播放")
            return
        self.drop_piece()
        
    def step_undo(self):
        if self.waiting == True:
            QMessageBox.warning(self, "操作失败", "请等待动画完毕再步退")
            return
        if self.simulating == True or self.board_correct == False:
            QMessageBox.warning(self, "操作失败", "无法步退，请回到真实棋局后再试！")
            return
        if self.current_step == 0:
            QMessageBox.warning(self, "操作失败", "已是第一步！")
            return
        self.current_step -= 1
        self.update_info()
        row, col = self.move_sequence[self.current_step]
        self.board[row][col] = 0
        self.draw_board()
    
    def auto_display(self):
        if self.simulating == True or self.board_correct == False:
            QMessageBox.warning(self, "操作失败", "请回到真实棋局后再试！")
            return
        if self.autoplay == False:
            self.update_timer.start(1000)
            self.autoplay = True
            self.button_autoplay.setText("暂停自动播放")
        else:
            self.update_timer.stop()
            self.autoplay = False
            self.button_autoplay.setText("自动播放")
    
    def undo_sim(self):
        if self.simulating == False:
            QMessageBox.warning(self, "操作失败", "根本没有开始模拟。")
            return
        if self.autoplay == True:
            QMessageBox.warning(self, "操作失败", "请暂停自动播放后再试！")
            return
        if len(self.move_sequence) <= self.current_step:
            self.board_correct = True
            QMessageBox.warning(self, "不能撤销", "已经回到开始模拟状态了，无法再撤销。")
            return
        self.can_simulate = True #到达终局后，若用户撤销一步模拟，允许继续模拟
        row, col = self.move_sequence.pop()
        self.board[row][col] = 0  # 清空该位置
        self.draw_board()
    
    def end_sim(self):
        if self.simulating == False:
            QMessageBox.warning(self, "操作失败", "根本没有开始模拟。")
            return
        if self.autoplay == True:
            QMessageBox.warning(self, "操作失败", "请暂停自动播放后再试！")
            return
        if self.board_correct == True:
            QMessageBox.information(self, "提示", "棋盘已是真实棋局。")
        self.move_sequence = copy.deepcopy(self.move_sequence_copy)
        self.board = copy.deepcopy(self.board_copy)
        self.simulating = False
        self.board_correct = True
        self.can_simulate = True
        self.draw_board()
    
    def check_chain(self, player_id): #统计三联的同时顺带统计四联
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]  # 下、右、右下、右上
        for row in range(self.ROWS):
            for col in range(self.COLS):
                if self.board[row][col] != player_id:
                    continue
                for dx, dy in directions:
                    chain = []
                    for i in range(4):
                        r = row + i * dy
                        c = col + i * dx
                        if 0 <= r < self.ROWS and 0 <= c < self.COLS and self.board[r][c] == player_id:
                            chain.append((r, c))
                        else:
                            break
                    if len(chain) == 4:
                        if self.simulating == True:
                            QMessageBox.information(self, "提示", "棋盘已定胜负")
                            self.can_simulate = False
                        return chain
                    elif len(chain) == 3:
                        r_before = row - dy
                        c_before = col - dx
                        r_after = row + 3 * dy
                        c_after = col + 3 * dx
                        before_ok = 0 <= r_before < self.ROWS and 0 <= c_before < self.COLS and self.board[r_before][c_before] == 0
                        after_ok = 0 <= r_after < self.ROWS and 0 <= c_after < self.COLS and self.board[r_after][c_after] == 0
                        if before_ok or after_ok:
                            self.chains.append(chain[0])
                            self.chains.append(chain[1])
                            self.chains.append(chain[2])
        return None
    
    def board_hint(self):
        self.chains.clear()
        self.win_chain = None
        result1 = self.check_chain(1)
        result2 = self.check_chain(2)
        if result1 != None:
            self.win_chain = result1
        elif result2 != None:
            self.win_chain = result2
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Right:
                self.step_forward()
                return True  # 表示已处理事件
            elif key == Qt.Key_Left:
                self.step_undo()
                return True
            elif key == Qt.Key_Space:
                self.auto_display()
                return True
        return super().eventFilter(obj, event)