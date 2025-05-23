import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QDialog, QVBoxLayout,
    QComboBox, QLabel, QCheckBox, QMessageBox
)
from PyQt5 import uic
from PyQt5.QtGui import QFont
from Main_Menu import MainMenuWindow
from PyQt5.QtCore import Qt
# ===== 对话框类（启动弹出） =====
default_userdata = {
    "stats": {
        "games_played": 0,
        "games_won": 0,
        "games_lost": 0
    }
}
class WelcomeDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("欢迎！")
        self.selected_user = None
        #设定大小防止看不清
        self.setFixedSize(700, 400)
        self.setStyleSheet("font-size: 32px;")
        self.temp_data = {}
        if not os.path.exists("userdata/users.json"):
            user_file = "userdata/默认用户.json"
            if not os.path.exists("userdata"):
                os.mkdir("userdata")
            f = os.open(user_file, os.O_CREAT)
            os.close(f)
            with open(user_file, "w", encoding="utf-8") as uf:
                json.dump(default_userdata, uf, indent=2, ensure_ascii=False)
            self.temp_data["name"] = []
            self.temp_data["name"].append("默认用户")  # 防止空白
        else:
            with open("userdata/users.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.temp_data = data
        
        #读取现有数据并存入temp_data，随后将其清空
        with open('userdata/users.json', 'w', encoding='utf-8') as f:
            json.dump({}, f)
            
        # 布局
        layout = QVBoxLayout()

        self.label = QLabel("请选择用户：")
        layout.addWidget(self.label)

        self.combo_box = QComboBox()
        self.combo_box.addItems(self.temp_data["name"])
        layout.addWidget(self.combo_box)

        self.default_box = QCheckBox("以后自动使用此账号登录")
        layout.addWidget(self.default_box)
        
        self.button_ok = QPushButton("确定")
        self.button_ok.clicked.connect(self.accept_selection) #链接按钮被按下事件到此函数
        layout.addWidget(self.button_ok)

        self.setLayout(layout)

    def closeEvent(self, event):
    # 提示用户必须选择账号
        QMessageBox.warning(self, "警告", "请点击“确定”按钮以继续。")
        event.ignore()  # 阻止关闭事件

    def accept_selection(self):
        self.selected_user = self.combo_box.currentText()
        if self.default_box.isChecked() == True:
            self.temp_data["default_account"] = self.selected_user
        else:
            self.temp_data["default_account"] = "None"
        #更改完数据写入users.json
        with open("userdata/users.json", "w", encoding="utf-8") as g:
            json.dump(self.temp_data, g, indent=2, ensure_ascii=False)
        
        self.accept()  # 关闭对话框并返回 QDialog.Accepted

def use_welcome_dialog():  # 不要传 app，不要调用 sys.exit
    welcome = WelcomeDialog()
    if welcome.exec_() == QDialog.Accepted:
        return welcome.selected_user
    return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.exists("userdata/users.json"):
        with open("userdata/users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if data["default_account"] != "None":
                menu = MainMenuWindow(data["default_account"])
                menu.show()
                sys.exit(app.exec_())
    #如果没有默认登录账户，则新建一个欢迎对话框指导用户登录
    username = use_welcome_dialog()
    if username:
        menu = MainMenuWindow(username)
        menu.show()
        sys.exit(app.exec_())