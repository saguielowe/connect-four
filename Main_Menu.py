# -*- coding: utf-8 -*-
"""
Created on Sun Apr 13 12:33:21 2025

@author: 23329
"""
import sys
import os
import json, socket, threading
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout,
    QComboBox, QLabel, QCheckBox, QMenu, QAction, QMessageBox,
    QWidget, QHBoxLayout, QRadioButton, QGroupBox, QButtonGroup, QGridLayout,
    QInputDialog, QPlainTextEdit
)
from PyQt5.QtGui import QFont
from Game_Window import GameWindow
from game_history import GameHistory

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于本游戏")
        self.resize(800, 600)
        self.setFont(QFont("微软雅黑", 12))
        layout = QVBoxLayout()

        self.textbox = QPlainTextEdit()
        self.textbox.setReadOnly(True)
        layout.addWidget(self.textbox)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.setLayout(layout)

        try:
            with open("关于.txt", "r", encoding="utf-8") as f:
                self.textbox.setPlainText(f.read())
        except Exception as e:
            self.textbox.setPlainText(f"无法加载说明文件：\n{e}")

class ListenerThread(threading.Thread):
    def __init__(self, conn, on_receive):
        super().__init__(daemon=True)
        print("[Server] ListenerThread started.")
        self.conn = conn
        self.on_receive = on_receive
        self.running = True

    def run(self):
        while self.running:
            try:
                data = self.conn.recv(1024) # 一次最多传1024字节
                if data:
                    self.on_receive(data.decode())
            except Exception as e:
                print(f"[ListenerThread] Error: {e}")
                self.running = False

    def stop(self):
        self.running = False
        self.conn.close()

class Server: # 服务器端，监听一个窗口，一旦有别人连接则报告
    def __init__(self, host='0.0.0.0', port=12345, on_receive=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 没这句就报错
        try:
            self.sock.bind((host, port))
        except Exception as e:
            QMessageBox.critical(None, "连接失败", f"发生错误：{e}")
            return
        self.on_receive = on_receive
        self.sock.listen(1) # 一次只允许一个客户端等待
        print(f"[Server] Listening on {host}:{port}")
        self.accept_thread = threading.Thread(target=self.accept_connection)
        self.accept_thread.start()

    def send(self, msg):
        msg_json = json.dumps(msg)
        self.conn.sendall(msg_json.encode())

    def accept_connection(self):
        self.conn, self.addr = self.sock.accept()
        print(f"[Server] Connected by {self.addr}")
        self.listener = ListenerThread(self.conn, self.on_receive)
        self.listener.start()
    
    def close(self):
        self.listener.stop()
        self.conn.close()
        self.sock.close()

class Client: # 客户端，负责输入要联机的地址，主动发起连接
    def __init__(self, username, xp, host='127.0.0.1', port=12345, on_receive=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(60)  # 避免长时间卡住
        try:
            self.sock.connect((host, port))
            print(f"[Client] Connected to {host}:{port}")
        except socket.timeout:
            print("[Client] Connection timed out.")
            QMessageBox.critical(None, "连接失败", "连接超时！请重试！")
            return
        except Exception as e:
            print(f"[Client] Failed to connect: {e}")
            QMessageBox.critical(None, "连接失败", f"发生错误：{e}")
            return
        self.send({"type": "hello", "username": username, "xp": xp})
        self.listener = ListenerThread(self.sock, on_receive)
        self.listener.start()

    def send(self, msg):
        msg_json = json.dumps(msg)
        self.sock.sendall(msg_json.encode())

    def close(self):
        self.listener.stop()
        self.sock.close()

class SelectSecondPlayerDialog(QDialog):
    def __init__(self, users_file, player1_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择对手玩家")
        self.resize(500, 400)
        self.setFont(QFont("微软雅黑", 12))

        # 读取用户数据
        with open(users_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        all_names = data['name']
        self.available_names = [name for name in all_names if name != player1_name]

        # 先检查是否还有可选玩家
        if not self.available_names:
            QMessageBox.warning(self, "无法开始双人对战", "没有其他可用玩家！")
            self.reject()  # 直接关闭对话框
            return

        # 创建控件
        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"玩家1: {player1_name}"))

        layout.addWidget(QLabel("选择玩家2："))
        self.combo_player2 = QComboBox()
        self.combo_player2.addItems(self.available_names)
        layout.addWidget(self.combo_player2)

        button_layout = QHBoxLayout()
        self.button_ok = QPushButton("确定")
        self.button_cancel = QPushButton("取消")
        button_layout.addWidget(self.button_ok)
        button_layout.addWidget(self.button_cancel)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 连接信号
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel.clicked.connect(self.reject)

    def get_selected_player2(self):
        return self.combo_player2.currentText()

class FirstMoveDialog(QDialog):
    def __init__(self, player1_name, player2_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择先手方")
        self.resize(500, 400)
        self.setFont(QFont("微软雅黑", 12))

        self.selected = None  # 1 表示 玩家1，2 表示 玩家2 / AI

        layout = QVBoxLayout()
        layout.addWidget(QLabel("请选择谁先手："))

        self.radio_p1 = QRadioButton(player1_name)
        self.radio_p2 = QRadioButton(player2_name)
        self.radio_p1.setChecked(True)  # 默认玩家1先手
        layout.addWidget(self.radio_p1)
        layout.addWidget(self.radio_p2)

        button_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        button_layout.addWidget(btn_ok)

        btn_ok.clicked.connect(self.accept_choice)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def accept_choice(self):
        self.selected = 1 if self.radio_p1.isChecked() else 2
        self.accept()  # 关闭对话框并返回 QDialog.Accepted

# ===== 主菜单窗口类 =====
class MainMenuWindow(QMainWindow):
    move_received = pyqtSignal(int)  # 收到move信息时触发，发送列信息
    client_ready = pyqtSignal()
    host_ready = pyqtSignal(int)
    peace_required = pyqtSignal(dict)
    result_received = pyqtSignal(dict)
    def __init__(self, username):
        super().__init__()
        self.init_menu_bar()
        self.username = username
        self.setWindowTitle(f"四子棋 - {username}")
        self.setFont(QFont("微软雅黑", 12))
        self.resize(600, 500)
        self.game_window = None
        
        # 顶部用户信息
        self.label_name = QLabel("用户名")
        self.label_name.setText(self.username)
        with open(f"userdata/{username}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.data = data
        
        self.label_level = QLabel()
        self.label_games = QLabel("已下局数：0")
        self.label_games.setText("已下局数："+str(data["stats"]["games_played"]))
        self.label_winrate = QLabel("胜率：100%")
        if data["stats"]["games_played"] == 0:
            self.label_winrate.setText("胜率：NaN")
        else:
            self.label_winrate.setText("胜率：" + str(data["stats"]["games_won"] * 100 // data["stats"]["games_played"]) +"%")
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
        self.label_level.setText("等级："+self.xp)
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.label_name)
        top_layout.addWidget(self.label_level)
        top_layout.addWidget(self.label_games)
        top_layout.addWidget(self.label_winrate)
        
        grid_layout = QGridLayout()

# =============================================================================
#         self.label_info = QLabel("信息通告 / 公告栏")
#         self.label_info.setFixedHeight(100)
#         self.label_info.setStyleSheet("background-color: #EEE; border: 1px solid #AAA;")
#         self.label_info.setAlignment(Qt.AlignCenter)
# =============================================================================
        
        # 第1行 人机对战 + 难度选择
        self.button_pve = QPushButton("人机对弈")
        self.button_pve.clicked.connect(self.start_game_ai)
        self.combo_difficulty = QComboBox()
        self.combo_difficulty.addItems(["简单", "普通", "困难"])
        grid_layout.addWidget(self.button_pve, 0, 0)
        grid_layout.addWidget(self.combo_difficulty, 0, 1)

        # 第2行 双人对战 + 联机/不联机选择
        self.button_pvp = QPushButton("双人对战")
        self.button_pvp.clicked.connect(self.start_game_pvp)
        self.radio_online = QRadioButton("联机")
        self.radio_offline = QRadioButton("不联机")
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio_online)
        self.radio_group.addButton(self.radio_offline)
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_online)
        radio_layout.addWidget(self.radio_offline)
        radio_widget = QWidget()
        radio_widget.setLayout(radio_layout)
        grid_layout.addWidget(self.button_pvp, 1, 0)
        grid_layout.addWidget(radio_widget, 1, 1)

        # 第3行 历史复盘 + 显示统计复选框
        self.button_history = QPushButton("历史复盘")
        self.button_history.clicked.connect(self.open_history)
        self.label_histories = QLabel()
        prefix = f"{self.username}_"
        folder_path = "userdata"
        count = 0
        for filename in os.listdir(folder_path):
            if os.path.isfile(os.path.join(folder_path, filename)) and filename.startswith(prefix):
                count += 1
        self.label_histories.setText("可复盘局数："+str(count))
        grid_layout.addWidget(self.button_history, 2, 0)
        grid_layout.addWidget(self.label_histories, 2, 1)

        # 设置列比例（左列按钮窄，右列控件宽）
        grid_layout.setColumnStretch(0, 2)
        grid_layout.setColumnStretch(1, 2)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
# =============================================================================
#         main_layout.addWidget(self.label_info)
# =============================================================================
        main_layout.addLayout(grid_layout)

        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)
    
    def init_menu_bar(self):
        menubar = self.menuBar()

        user_menu = menubar.addMenu("用户(&Y)")

        action_change = QAction("切换用户(&Q)", self)
        action_change.setShortcut("Ctrl+Q")
        action_change.setStatusTip("改变当前登录账号，并可同时改变默认登录账号")
        action_change.triggered.connect(self.change_user)

        create_user_action = QAction("新建用户(&N)", self)
        create_user_action.setShortcut("Ctrl+N")
        create_user_action.setStatusTip("新建一个账号，并以该账号登录")
        create_user_action.triggered.connect(self.create_user)
        
        
        action_exit = QAction("注销账号(&Z)", self)
        action_exit.setShortcut("Ctrl+Z")
        action_exit.setStatusTip("注销当前登录账号全部信息，并重新选择登录账号")
        action_exit.triggered.connect(self.delete_user)
        
        action_rename = QAction("更改用户名(&G)", self)
        action_rename.setShortcut("Ctrl+G")
        action_rename.setStatusTip("更改当前用户名")
        action_rename.triggered.connect(self.rename)

        user_menu.addAction(action_change)
        user_menu.addSeparator()
        user_menu.addAction(create_user_action)
        user_menu.addSeparator()
        user_menu.addAction(action_exit)
        user_menu.addSeparator()
        user_menu.addAction(action_rename)

        # ❓ 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        action_about = QAction("关于(&A)", self)
        action_about.triggered.connect(self.show_about)
        help_menu.addAction(action_about)
    
    def show_about(self):
        dlg = AboutDialog(self)
        dlg.exec_()
    
    def change_user(self):
        from main import use_welcome_dialog
        username = use_welcome_dialog()
        if username:
            self.close()
            self.new_main = MainMenuWindow(username)
            self.new_main.show()
    
    def create_user(self):
        from createuserdialog import CreateUserDialog
        dialog = CreateUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "提示", "用户创建成功，请重新登录以切换。")
    
    def delete_user(self):
        reply = QMessageBox.question(self, "确认注销", f"确定要注销用户 {self.username} 吗？这将删除该用户的所有数据。",
                             QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if os.path.exists(f"userdata/{self.username}.json"):
                os.remove(f"userdata/{self.username}.json")
            with open("userdata/users.json", "r+", encoding="utf-8") as f:
                data = json.load(f)
                if self.username in data["name"]:          
                    data["name"].remove(self.username)
                    if data["default_account"] == self.username:
                        data["default_account"] = "None"  # 清除默认账户
                    f.seek(0)
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    f.truncate()
            from main import WelcomeDialog  # 避免循环导入
            self.close()  # 关闭当前主菜单窗口
            dialog = WelcomeDialog()
            if dialog.exec_() == QDialog.Accepted:
                new_user = dialog.selected_user
                self.new_menu = MainMenuWindow(new_user)
                self.new_menu.show()
    
    def rename(self):
        folder="userdata"
        new_name, ok = QInputDialog.getText(self, "修改用户名", "请输入新用户名：")
        if ok and new_name:
            if new_name == self.username:
                QMessageBox.information(self, "提示", "用户名未更改。")
                return
            old_name = self.username
            with open("userdata/users.json", "r+", encoding="utf-8") as f:
                data = json.load(f)          
                data["name"].remove(self.username)
                data["name"].append(new_name)
                if data["default_account"] == old_name:
                    data["default_account"] = new_name
                f.seek(0)
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.truncate()
            for filename in os.listdir(folder):
                if filename.startswith(old_name) and filename.endswith(".json"):
                    suffix = filename[len(old_name):]  # 保留 _01.json 这种部分
                    new_filename = new_name + suffix
                    old_path = os.path.join(folder, filename)
                    new_path = os.path.join(folder, new_filename)
                    os.rename(old_path, new_path)
            self.username = new_name
            self.label_name.setText(self.username)
    
    def start_game_ai(self): #此按钮对应与AI下棋
        self.difficulty = self.combo_difficulty.currentText()
        self.player1 = self.username
        self.player2 = "AI"
        dialog = FirstMoveDialog(self.player1, self.player2)
        if dialog.exec_() == QDialog.Accepted:
            first_player = dialog.selected  # 1 or 2
            self.game_window = GameWindow(self, 1, first_player)
            self.game_window.show()
            self.hide()
    
    def start_game_pvp(self): #此按钮对应与人下棋
        if self.radio_offline.isChecked():
            dialog = SelectSecondPlayerDialog('userdata/users.json', self.username, self)
            if dialog.exec_() == QDialog.Accepted:
                self.player1 = self.username
                self.player2 = dialog.get_selected_player2()
                dialog = FirstMoveDialog(self.player1, self.player2)
                if dialog.exec_() == QDialog.Accepted:
                    first_player = dialog.selected  # 1 or 2
                    self.game_window = GameWindow(self, 2, first_player)
                    self.game_window.show()
                    self.hide()
        elif self.radio_online.isChecked():
            self.player1 = self.username
            result = ask_connection_mode() #分配主副机
            if result == None:
                return
            self.id = result[0]
            if result[0] == "host":
                self.net = Server(host="127.0.0.1", port=result[2], on_receive=self.handle_message)
                print(f"我是主机，监听 {result[1]}:{result[2]}")
            elif result[0] == "client":
                self.net = Client(self.username, self.xp, host=result[1], port=result[2], on_receive=self.handle_message)
                print(f"我是客户端，连接到 {result[1]}:{result[2]}")
    
    def open_history(self):
        self.history_window = GameHistory(self.username)
        self.history_window.show()
        
    def handle_message(self, message): #此函数由监听线程调用，不可以进行GUI操作
        data = json.loads(message)
        if data["type"] == "hello" and self.id == "host": #客户端连上后立即向主机发送hello
            self.player2 = data["username"]
            self.opponent_xp = data["xp"]
            print("客户端用户名：", data["username"])
            self.net.send({"type": "hello", "username": self.username, "xp": self.xp}) #主机回复客户端自身信息
        if data["type"] == "hello" and self.id == "client": #客户端收到信息并告诉主机可以开始
            self.player2 = data["username"]
            self.opponent_xp = data["xp"]
            print("主机用户名：", data["username"])
            self.net.send({"type": "ready"})
        if data["type"] == "ready" and self.id == "host": #主机收到客户端ready后决定先手
            self.client_ready.connect(self.choose_first_player)
            self.client_ready.emit()
        if data["type"] == "ready" and self.id == "client": #客户端知道先手信息并进入游戏
            self.host_ready.connect(self.game_begin)    
            self.host_ready.emit(data["first_player"])
        if data["type"] == "move":
            self.move_received.emit(data["move"])
        if data["type"] == "peace": #求和时，求和方发送peace+ask信息，被求和方回答peace+yes/no信息
            self.peace_required.emit(data)
        if data["type"] == "result":
            self.result_received.emit(data)

    def choose_first_player(self):
        dialog = FirstMoveDialog(self.player1, self.player2)
        if dialog.exec_() == QDialog.Accepted: #主机发送先手信息给客户端，并开始游戏
            first_player = dialog.selected  # 1 or 2
            self.net.send({"type": "ready", "first_player": 3 - first_player}) #主机收到客户端ready消息分配先手
            self.game_window = GameWindow(self, 3, first_player)
            self.move_received.connect(self.game_window.on_remote_move)
            self.peace_required.connect(self.game_window.on_peace_request)
            self.result_received.connect(self.game_window.on_opp_result)
            self.game_window.show()
            self.hide()
    
    def game_begin(self, first_player):# 此函数仅有客户端会调用
        print("game begin!")
        self.game_window = GameWindow(self, 3, first_player) #这一部分也需要在主线程调用，需要重新管理槽函数！
        self.move_received.connect(self.game_window.on_remote_move)
        self.peace_required.connect(self.game_window.on_peace_request)
        self.game_window.show()
        self.hide()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 并不会真的连接，只是触发系统选个出口IP
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    finally:
        s.close()

def ask_connection_mode():
    # 主机 or 客户端
    dialog = QInputDialog()
    dialog.setWindowTitle("联机模式选择")
    dialog.setLabelText("请选择模式：")
    dialog.setComboBoxItems(["作为主机", "作为客户端"])
    dialog.setStyleSheet("QLabel { font-size: 32px; } QComboBox { font-size: 24px; }")
    ok = dialog.exec_()
    if not ok:
        return None
    mode = dialog.textValue()

    if mode == "作为主机":
        # 获取本机IP用于展示
        ip = get_local_ip()
        port_dialog = QInputDialog()
        port_dialog.setWindowTitle("输入端口")
        port_dialog.setLabelText(f"你的IP地址是 {ip}\n请输入监听的端口号：")
        port_dialog.setInputMode(QInputDialog.IntInput)
        port_dialog.setIntRange(1024, 65535)
        port_dialog.setIntValue(12345)
        port_dialog.setStyleSheet("QLabel { font-size: 32px; } QSpinBox { font-size: 24px; }")
        ok = port_dialog.exec_()
        if not ok:
            return None
        port = port_dialog.intValue()
        return ("host", ip, port)

    else:
        # 作为客户端，手动输入对方IP和端口
        ip_dialog = QInputDialog()
        ip_dialog.setWindowTitle("输入主机IP")
        ip_dialog.setLabelText("请输入主机的IP地址：")
        ip_dialog.setInputMode(QInputDialog.TextInput)
        ip_dialog.setStyleSheet("QLabel { font-size: 32px; } QLineEdit { font-size: 24px; }")
        ok = ip_dialog.exec_()
        if not ok:
            return None
        ip = ip_dialog.textValue()

        port_dialog = QInputDialog()
        port_dialog.setWindowTitle("输入端口")
        port_dialog.setLabelText("请输入主机的端口号：")
        port_dialog.setInputMode(QInputDialog.IntInput)
        port_dialog.setIntRange(1024, 65535)
        port_dialog.setIntValue(12345)
        port_dialog.setStyleSheet("QLabel { font-size: 32px; } QSpinBox { font-size: 24px; }")
        ok = port_dialog.exec_()
        if not ok:
            return None
        port = port_dialog.intValue()
        return ("client", ip, port)

