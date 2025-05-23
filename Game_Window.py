import sys, time, json, os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout,
    QGroupBox, QLabel, QCheckBox, QWidget, QHBoxLayout, QMessageBox, QProgressBar
)
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPixmap, QPen, QKeyEvent
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QTimer, QUrl
from PyQt5.QtMultimedia import QSoundEffect

from ai_player import AI
from Winrate_bar import WinrateBar
from datetime import datetime

class ClickableLabel(QLabel):
    clicked = pyqtSignal(int, int)

    def mousePressEvent(self, event):
        self.clicked.emit(event.x(), event.y())

class GameWindow(QMainWindow):
    ROWS = 6
    COLS = 7
    # player1永远都是username，AI一定都是player2，与先手无关
    def __init__(self, menu_window, mode, first_player): # mode: 1=pve 2=pvp 3=online first_player决定player1还是player2是先手
        super().__init__()
        # 界面基本信息
        self.mode = mode
        self.turn = first_player - 1 #如果先手不是player1，那么需要调整
        self.menu_window = menu_window #将主界面窗口当作参数传过来
        self.click_allowed = True
        self.username = self.menu_window.player1
        if first_player == 1:
            self.first_player = self.menu_window.player1
        else:
            self.first_player = self.menu_window.player2
        self.setWindowTitle(f"四子棋 - {self.menu_window.player1} vs {self.menu_window.player2}")
        self.setFixedSize(850, 800)
        self.setFont(QFont("微软雅黑", 12))
        self.cell_size = 60
        self.initial_time = time.time()
        self.user_initial_time = time.time()
        # 动画状态变量
        self.drop_row = None
        self.drop_col = None
        self.drop_y = 0
        self.drop_timer = QTimer()
        self.update_timer = QTimer()
        self.update_timer.start(1000)
        self.drop_timer.timeout.connect(self.animate_drop)
        self.waiting = False #当正在绘制棋子动画时暂停落子行为
        self.drop_sound = QSoundEffect()
        self.drop_sound.setSource(QUrl.fromLocalFile("sounds/drop.wav"))
        self.drop_sound.setVolume(0.5)  # 音量范围 0.0 - 1.0
        # 初始化棋盘
        self.board = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]  # 0 空，1 玩家1，2 玩家2
        self.ai = AI(self)
        if mode == 1:
            self.difficulty = self.menu_window.difficulty
        self.move_sequence = []
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
        top_layout.addWidget(QLabel("红方：" + self.menu_window.player1))
        top_layout.addWidget(QLabel("等级："+ self.menu_window.xp))
        top_layout.addStretch()
        if self.mode == 2:
            with open(f"userdata/{self.menu_window.player2}.json", "r", encoding="utf-8") as f:
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
            top_layout.addWidget("蓝方：" + QLabel(self.menu_window.player2))
        elif self.mode == 1:
            self.xp = self.menu_window.difficulty
            top_layout.addWidget(QLabel("难度："+ self.xp))
            top_layout.addWidget(QLabel("AI"))
        else:
            self.xp = self.menu_window.opponent_xp
            top_layout.addWidget(QLabel("等级："+ self.xp))
            top_layout.addWidget(QLabel(self.menu_window.player2))
        
        main_layout.addLayout(top_layout)

        # 中部：棋盘+左状态+右控件
        mid_layout = QHBoxLayout()
        self.status = QLabel(f"现在轮到 {self.first_player} 落子")
        main_layout.addWidget(self.status)

        # 棋盘 Pixmap
        self.label_board = ClickableLabel()
        self.label_board.clicked.connect(self.handle_click)
        self.label_board.setPixmap(QPixmap(420, 360))
        
        self.label_board.setStyleSheet("background-color: white; border: 1px solid black;")
        mid_layout.addWidget(self.label_board)

        # 控制区 GroupBox
        control_group = QGroupBox()
        control_layout = QVBoxLayout()
        button_giveup_game = QPushButton("认输")
        button_giveup_game.clicked.connect(self.give_up)
        control_layout.addWidget(button_giveup_game)
        another_button = QPushButton()
        if mode == 1:
            another_button.setText("悔棋")
        else:
            another_button.setText("求和")
        another_button.clicked.connect(self.peace)
        control_layout.addWidget(another_button)
        self.checkbox_show_move = QCheckBox("显示步数")
        self.checkbox_show_move.stateChanged.connect(self.draw_moves)
        control_layout.addWidget(self.checkbox_show_move)
        self.checkbox_show_winrate = QCheckBox("显示胜率")
        self.checkbox_show_winrate.setChecked(True)
        self.checkbox_show_winrate.stateChanged.connect(self.ai.cal_winrate)
        control_layout.addWidget(self.checkbox_show_winrate)
        control_group.setLayout(control_layout)
        mid_layout.addWidget(control_group)

        main_layout.addLayout(mid_layout)

        # 底部：字母 + 步数 + 时间信息
        bottom_layout = QHBoxLayout()
        self.label_total_time = QLabel("对局时间：0:00")
        bottom_layout.addWidget(self.label_total_time)
        self.label_steps_moved = QLabel("已下步数: 0/42")
        bottom_layout.addWidget(self.label_steps_moved)
        self.label_user_time = QLabel("0:00")
        bottom_layout.addWidget(self.label_user_time)
        main_layout.addLayout(bottom_layout)
        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)
        self.resize(800, 600)
        self.update_timer.timeout.connect(self.update_time)
        self.draw_board()
        if first_player == 2:
            if self.mode == 1: # 如果对手不是AI那么实际上什么也不用做
                if self.difficulty == "简单":
                    self.ai_col = self.ai.easy_move()
                elif self.difficulty == "普通":
                    self.ai_col = self.ai.medium_move()
                else:
                    self.ai_col = self.ai.hard_move()
                self.ai_to_move()
                if self.checkbox_show_winrate.isChecked():
                    self.ai.cal_winrate(-1, 2 - (len(self.move_sequence) + self.turn) % 2)
        if first_player == 1 and self.mode == 3:
            self.click_allowed = True
        elif first_player == 2 and self.mode == 3:
            self.click_allowed = False
    
    def on_remote_move(self, col): #联机时获取对方落子信息，执行动画并更新胜率
        if self.mode == 3:
            self.drop_row = self.can_drop_piece(col, 2)
            self.waiting = True # 玩家落子动画等待
            self.drop_piece_with_animation(col, 2 - (len(self.move_sequence) + self.turn) % 2)  # 玩家落子动画
            if self.checkbox_show_winrate.isChecked():
                self.ai.cal_winrate(-1, 2 - (len(self.move_sequence) + self.turn) % 2)
            self.click_allowed = True
    
    
    def keyPressEvent(self, event: QKeyEvent): # 重写函数监听按键按下情况，基本逻辑与点击相同
        if self.click_allowed == False and self.mode == 3:
            QMessageBox.warning(self, "落子失败", "请等待对方落子后再落子")
            return
        if self.waiting == True:
            QMessageBox.warning(self, "落子失败", "请等待动画完毕再落子")
            return
        if self.mode == 1 and (len(self.move_sequence) + self.turn) % 2 == 1:
            QMessageBox.warning(self, "落子失败", "请等待AI落子完毕")
            return
        if event.key() == Qt.Key_L:
            cheat_col = self.ai.hard_move()
            QMessageBox.warning(self, "作弊提示", f"AI推荐第{cheat_col}列")
        if event.key() in (Qt.Key_A, Qt.Key_B, Qt.Key_C, Qt.Key_D, Qt.Key_E, Qt.Key_F, Qt.Key_G):
            key_map = {
                Qt.Key_A: 0,
                Qt.Key_B: 1,
                Qt.Key_C: 2,
                Qt.Key_D: 3,
                Qt.Key_E: 4,
                Qt.Key_F: 5,
                Qt.Key_G: 6
                }
            col = key_map[event.key()]
            if col < 0 or col >= self.COLS:
                QMessageBox.warning(self, "无效落子", "不存在该列，请重新点击")
                return
            self.drop_row = self.can_drop_piece(col, player=1)
            if self.drop_row == -1:
                QMessageBox.warning(self, "无效落子", "该列已满，请换一列落子")
                return
            if self.mode == 3:
                self.menu_window.net.send({"type": "move", "move": col})
                self.click_allowed = False
            self.waiting = True # 玩家落子动画等待
            self.drop_piece_with_animation(col, 2 - (len(self.move_sequence) + self.turn) % 2)  # 玩家落子动画
            if self.checkbox_show_winrate.isChecked(): #计算玩家落子后胜率
                self.ai.cal_winrate(-1, 2 - (len(self.move_sequence) + self.turn) % 2)
            if self.mode == 1: # 如果对手不是AI那么实际上什么也不用做
                if self.difficulty == "简单":
                    self.ai_col = self.ai.easy_move()
                elif self.difficulty == "普通":
                    self.ai_col = self.ai.medium_move()
                else:
                    self.ai_col = self.ai.hard_move()
                QTimer.singleShot(1000, self.ai_to_move)
    
    def handle_click(self, x, y): #此函数直接响应用户点击事件，判断是否合法后绘制动画，并呼唤ai落子
        if self.click_allowed == False and self.mode == 3:
            QMessageBox.warning(self, "落子失败", "请等待对方落子后再落子")
            return
        if self.waiting == True:
            QMessageBox.warning(self, "落子失败", "请等待动画完毕再落子")
            return
        if self.mode == 1 and (len(self.move_sequence) + self.turn) % 2 == 1:
            QMessageBox.warning(self, "落子失败", "请等待AI落子完毕")
            return
        col = x // self.cell_size
        if col < 0 or col >= self.COLS:
            QMessageBox.warning(self, "无效落子", "不存在该列，请重新点击")
            return
        self.drop_row = self.can_drop_piece(col, player=1) # 此句之后已落子，棋盘锁定
        if self.drop_row == -1:
            QMessageBox.warning(self, "无效落子", "该列已满，请换一列落子")
            return
        if self.mode == 3:
            self.menu_window.net.send({"type": "move", "move": col})
            print(col)
            self.click_allowed = False
        self.waiting = True # 玩家落子动画等待
        self.drop_piece_with_animation(col, 2 - (len(self.move_sequence) + self.turn) % 2)  # 玩家落子动画
        if self.mode == 1: # 如果对手不是AI那么实际上什么也不用做
            if self.difficulty == "简单":
                self.ai_col = self.ai.easy_move()
            elif self.difficulty == "普通":
                self.ai_col = self.ai.medium_move()
            else:
                self.ai_col = self.ai.hard_move()
            QTimer.singleShot(1000, self.ai_to_move) # 为了使得交替更加自然，故意让AI等万事俱备后晚1秒下棋

    def ai_to_move(self):
        if self.waiting == False: #等玩家的棋子落地后再执行动画
            self.drop_row = self.can_drop_piece(self.ai_col, player=2)
            self.drop_piece_with_animation(self.ai_col, 2)
            self.waiting = True

    def can_drop_piece(self, col, player):
        #此函数返回能否在col列落子，若能则更新board数据且返回能下的行，并更新移动列表
        for row in reversed(range(self.ROWS)):
            if self.board[row][col] == 0:
                self.board[row][col] = 3 #3表示已锁定
                self.move_sequence.append((row, col))
                self.update_info()
                self.user_initial_time = time.time()
                return row #此函数每落一个子只能调用一次！
        return -1
    
    def drop_piece_with_animation(self, col, player_id): #此函数开始动画
        self.drop_sound.play()
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
            if self.checkbox_show_winrate.isChecked(): #计算任意一方落子后的胜率
                self.ai.cal_winrate(-1, 2 - (len(self.move_sequence) + self.turn) % 2)
            self.waiting = False
# =============================================================================
#             if self.drop_player == 1: # 此处会让玩家落子动画与AI落子一同执行，取消AI等待时间
#                 self.ai_to_move()
#                 target_y = 10000
# =============================================================================
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
                # 设置字体颜色（对比背景）
                painter.setPen(Qt.white if index % 2 == 1 - self.turn else Qt.black)
                painter.setBrush(Qt.NoBrush)
                text_font = QFont("微软雅黑")
                text_font.setPointSize(int(self.cell_size*0.2))
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
        if len(self.move_sequence) == 42:
            self.end_game(None, 0)
    
    def draw_moves(self):
        if self.waiting == True: #正在绘制动画，场上有临时棋子，比较混乱，不允许切换
            QMessageBox.warning(self, "更改失败", "请等待动画完毕再更改")
        else:
            self.draw_board(animated=False)
    
    def update_info(self):
        if (len(self.move_sequence) + self.turn) % 2 == 0:
            next_person = self.menu_window.player1
        else:
            next_person = self.menu_window.player2
        self.status.setText(f"现在轮到 {next_person} 落子")
        self.label_steps_moved.setText(f"已下步数: {len(self.move_sequence)} / 42")
    
    def update_time(self):
        current_time = time.time()
        delta_time = current_time - self.initial_time
        minutes = int(delta_time // 60)
        seconds = int(delta_time % 60)
        self.label_total_time.setText(f"对局时间：{minutes}:{seconds:02d}")
        if self.mode == 1:
            delta_time = current_time - self.user_initial_time
            minutes = int(delta_time // 60)
            seconds = int(delta_time % 60)
            self.label_user_time.setText(f"落子计时：{minutes}:{seconds:02d}")
        else:
            delta_time = current_time - self.user_initial_time
            minutes = int(delta_time // 60)
            if minutes >= 1:
                self.update_timer.stop()
                self.end_game(None, 2 - (len(self.move_sequence) + self.turn) % 2)
            seconds = 60 - int(delta_time % 60)
            self.label_user_time.setText(f"落子倒计时：{minutes}:{seconds:02d}")
    
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
                        self.win_chain = chain
                        self.draw_board()
                        self.end_game(chain, player_id)
                        return 1
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
        self.check_chain(1)
        self.check_chain(2)
        
    def end_game(self, coord, player_id):
    # 此函数处理所有结束棋局的可能，player_id指代赢家id，0代表平局。
    # 游戏结束应弹出对话框，记录游戏数据，并回到主界面
        self.update_timer.stop() # 先停止计时再说
        self.ai.cal_winrate(player_id, 0)
        if player_id == 1:
            QMessageBox.information(self, "游戏结束", f"{self.menu_window.player1} 胜利！     ")
            self.menu_window.data["stats"]["games_won"] += 1
        elif player_id == 2:
            QMessageBox.information(self, "游戏结束", f"{self.menu_window.player2} 胜利！     ")
            self.menu_window.data["stats"]["games_lost"] += 1
        else:
            QMessageBox.information(self, "游戏结束", "平局！     ")
        self.menu_window.data["stats"]["games_played"] += 1
        
        if self.mode == 2: #仅本地双人对战需要修改对战方数据
            with open(f"userdata/{self.menu_window.player2}.json", "r+", encoding="utf-8") as f:
                data_2 = json.load(f)
            if player_id == 1:
                data_2["stats"]["games_lost"] += 1
            elif player_id == 2:
                data_2["stats"]["games_won"] += 1
            data_2["stats"]["games_played"] += 1
            # 在写入之前关闭文件并重新打开，以确保覆盖而不是追加
            with open(f"userdata/{self.menu_window.player2}.json", "w", encoding="utf-8") as f:
                json.dump(data_2, f, indent=4, ensure_ascii=False)
        # 游戏结束更改玩家数据
        with open(f"userdata/{self.menu_window.player1}.json", "w", encoding="utf-8") as f:
            json.dump(self.menu_window.data, f, indent=2, ensure_ascii=False)
        
        os.makedirs("userdata/", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        index = 1
        while True:
            filename = f"{self.menu_window.player1}_{index}.json"
            filepath = os.path.join("userdata/", filename)
            if not os.path.exists(filepath):
                break
            index += 1

        record = {
        "player1": self.menu_window.player1,
        "player2": self.menu_window.player2,
        "opponent_xp": self.xp,
        "timestamp": timestamp,
        "first_player": self.first_player,
        "moves": self.move_sequence,
        "result": player_id
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=4, ensure_ascii=False)
        # 删除旧的主界面换一个新的
        self.menu_window.close()
        from Main_Menu import MainMenuWindow
        self.new_menu_window = MainMenuWindow(self.username)
        self.new_menu_window.show()
        self.close()
    
    def give_up(self):
        self.end_game(None, 2) #相当于对手赢了
        
    def peace(self): # pvp时求和，pve时悔棋
        if self.mode == 2:
            self.end_game(None, 0)
        elif self.mode == 3:
            self.menu_window.net.send({"type": "peace", "text": "ask"})
            QMessageBox.information(self, "提示", "求和请求已发送，等待对方同意……")
            self.click_allowed = False
        else:
            if len(self.move_sequence) < 2:
                QMessageBox.warning(self, "不能悔棋", "已经到最初了，无法再悔棋。")
                return
            for _ in range(2):  # 悔两步
                row, col = self.move_sequence.pop()
                self.board[row][col] = 0  # 清空该位置
            self.current_player = 1  # 重置为玩家回合
            if self.checkbox_show_winrate.isChecked():
                print(self.board)
                self.ai.cal_winrate(-1, self.current_player)
            self.status.setText(f"悔棋成功，现在轮到 {self.menu_window.player1} 落子")
            self.draw_board()
            
    def on_peace_request(self, msg):
        if self.mode == 3:
            if msg["text"] == "ask":
                ret = QMessageBox.question(self, "求和请求", "对手向你发出了求和请求，是否同意？", QMessageBox.Yes, QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.menu_window.net.send({"type": "peace", "text": "yes"})
                    self.end_game(None, 0)
                elif ret == QMessageBox.No:
                    self.menu_window.net.send({"type": "peace", "text": "no"})
                    QMessageBox.information(self, "提示", "已拒绝对方求和请求，游戏继续……")
            elif msg["text"] == "yes":
                self.end_game(None, 0)
            elif msg["text"] == "no":
                QMessageBox.information(self, "提示", "对方拒绝了你的求和请求，游戏继续……")

                

            