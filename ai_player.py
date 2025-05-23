# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 10:40:48 2025

@author: 23329
"""
import random
import copy
import math
from Winrate_bar import WinrateBar
class AI:
    def __init__(self, game): # ai只依赖当前board以及先手数据，返回要下的列，game可以是任意含有board、winrate_bar的变量
        self.game = game
        self.board = game.board # 由于AI的初始化函数在游戏初始化时调用，此board必须随着游戏进程不断更新，故不可以用copy
    
    def cal_winrate(self, game_result_fixed, current_player): # current_player指刚刚下完的人
        board_copy = copy.deepcopy(self.board) # 开始计算后就要与游戏board数据分离
# =============================================================================
#         print(board_copy, current_player)
# =============================================================================
        rows, cols = len(board_copy), len(board_copy[0])
        for row in range(rows):
            for col in range(cols):
                if board_copy[row][col] == 0:
                    continue
                if board_copy[row][col] == 3:
                    board_copy[row][col] = current_player
        if game_result_fixed != -1:
            if game_result_fixed == 1:
                p_win, p_draw, p_lose = 1.0, 0.0, 0.0
            elif game_result_fixed == 2:
                p_win, p_draw, p_lose = 0.0, 0.0, 1.0
            elif game_result_fixed == 0:
                p_win, p_draw, p_lose = 0.0, 1.0, 0.0
        else:
            score = minimax(board_copy, depth=5, alpha=-math.inf, beta=math.inf, maximizingPlayer=True, ai_piece=3-current_player)[1]
            dist_win = max(1, abs(1000 - score))
            dist_draw = max(1, abs(score))
            dist_lose = max(1, abs(-1000 - score))

        # 反比权重
            inv_win = 1 / dist_win
            inv_draw = 1 / dist_draw
            inv_lose = 1 / dist_lose

            total = inv_win + inv_draw + inv_lose

            p_win = inv_win / total
            p_draw = inv_draw / total
            p_lose = inv_lose / total
            
            if current_player == 1:
                (p_win, p_lose) = (p_lose, p_win)

        self.game.winrate_bar.set_ratios(p_win, p_lose)

        self.game.label_winrate.setText(
    f"红方胜率: {p_win:.1%}   平局: {p_draw:.1%}   蓝方胜率: {p_lose:.1%}"
)
    
    def easy_move(self):
        valid_cols = get_valid_columns(self.board)
        return random.choice(valid_cols)
    
# =============================================================================
#     def medium_move(self): # 此方案计算量大，且效果不好，通用性差，已被废弃
#         valid_columns = get_valid_columns(self.board)
#         if not valid_columns:
#             return None
#         best_col = None
#         least_loss = 100
#         for col in valid_columns: #AI下一步，对每一列都计算胜率
#             self.wins = 0
#             self.loss = 0
#             self.draws = 0
#             sim_board = copy.deepcopy(self.board)
#             if not drop_piece(sim_board, col, 2):
#                 continue
#             self.simulate_game(sim_board, 1, 4) #玩家下，总共下4次
#             win_rate = self.wins / (self.wins + self.loss + self.draws)
#             # print(col, self.loss, self.draws, self.wins)
#             if self.loss < least_loss:
#                 least_loss = self.loss
#                 best_col = col
#         return best_col
#     
# =============================================================================
    def medium_move(self, current_player=1):
        board_copy = copy.deepcopy(self.board) # 关键bug，一定要先拷贝！
        rows, cols = len(board_copy), len(board_copy[0])
        for row in range(rows):
            for col in range(cols):
                if board_copy[row][col] == 0:
                    continue
                if board_copy[row][col] == 3:
                    board_copy[row][col] = current_player
        column, _ = minimax(board_copy, depth=2, alpha=-math.inf, beta=math.inf,
                        maximizingPlayer=True, ai_piece=2)
        return column

    def hard_move(self, current_player=1): #默认人机对战，即刚刚下完的一定是玩家
        board_copy = copy.deepcopy(self.board) # 关键bug，一定要先拷贝！
        rows, cols = len(board_copy), len(board_copy[0])
        for row in range(rows):
            for col in range(cols):
                if board_copy[row][col] == 0:
                    continue
                if board_copy[row][col] == 3:
                    board_copy[row][col] = current_player #由于在玩家动画期间就让AI思考了，此时还是锁定状态，在AI这里要解除锁定
        column, _ = minimax(board_copy, depth=5, alpha=-math.inf, beta=math.inf,
                        maximizingPlayer=True, ai_piece=2)
        return column
    
# =============================================================================
#     def simulate_game(self, board, next_turn, depth): #递归模拟玩家AI对下4次
#         if depth == 0:
#             result = check_winner_sim(board)
#             if result == 1:
#                 self.loss += 1
#             elif result == 0:
#                 self.draws += 1
#             else:
#                 self.wins += 1
#             return
#         valid_columns = get_valid_columns(board)
#         if not valid_columns: #如果无列可下，则说明满了，平局
#             self.draws += 1
#             return
#         for col in valid_columns:
#             sim_board = copy.deepcopy(board)
#             if not drop_piece(sim_board, col, next_turn):
#                 continue
#             if check_winner_sim(sim_board):
#                 result = check_winner_sim(sim_board)
#                 if result == 1:
#                     self.loss += 1
#                 elif result == 0:
#                     self.draws += 1
#                 else:
#                     self.wins += 1
#                 return
#             self.simulate_game(sim_board, 3 - next_turn, depth - 1)
# =============================================================================

def get_valid_columns(board):
    valid = []
    for col in range(len(board[0])):
        if board[0][col] == 0:  # 最上面那一行为空说明该列可下
            valid.append(col)
    return valid
    
def drop_piece(board, col, player_id):
    for row in reversed(range(len(board))):
        if board[row][col] == 0:
            board[row][col] = player_id
            return True
    return False


def check_winner_sim(board):
    rows, cols = len(board), len(board[0])

    for row in range(rows):
        for col in range(cols):
            if board[row][col] == 0:
                continue
            player = board[row][col]
            # 横向
            if col <= cols - 4 and all(board[row][col + i] == player for i in range(4)):
                return player
            # 纵向
            if row <= rows - 4 and all(board[row + i][col] == player for i in range(4)):
                return player
            # 斜下
            if row <= rows - 4 and col <= cols - 4 and all(board[row + i][col + i] == player for i in range(4)):
                return player
            # 斜上
            if row >= 3 and col <= cols - 4 and all(board[row - i][col + i] == player for i in range(4)):
                return player
    return 0  # 无胜者

def evaluate_window(window, ai_piece):
    opp_piece = 1 if ai_piece == 2 else 2
    score = 0

    if window.count(ai_piece) == 4:
        score += 1000
    elif window.count(ai_piece) == 3 and window.count(0) == 1:
        score += 100
    elif window.count(ai_piece) == 2 and window.count(0) == 2:
        score += 10
    elif window.count(opp_piece) == 3 and window.count(0) == 1:
        score -= 120  # 防守更重要
    elif window.count(opp_piece) == 2 and window.count(0) == 2:
        score -= 15
    
    return score

def evaluate_board(board, ai_piece):
    score = 0
    ROWS = len(board)
    COLS = len(board[0])
    
    # 中心列优先级
    center_col = COLS // 2
    center_array = [row[center_col] for row in board]
    center_count = center_array.count(ai_piece)
    score += center_count * 6  # 越中越强

    # 横向扫描
    for row in board:
        for col in range(COLS - 3):
            window = row[col:col+4]
            score += evaluate_window(window, ai_piece)

    # 竖向扫描
    for col in range(COLS):
        for row in range(ROWS - 3):
            window = [board[row+i][col] for i in range(4)]
            score += evaluate_window(window, ai_piece)

    # 正对角线 /
    for row in range(ROWS - 3):
        for col in range(COLS - 3):
            window = [board[row+i][col+i] for i in range(4)]
            score += evaluate_window(window, ai_piece)

    # 反对角线 \
    for row in range(ROWS - 3):
        for col in range(3, COLS):
            window = [board[row+i][col-i] for i in range(4)]
            score += evaluate_window(window, ai_piece)

    return score

def minimax(board, depth, alpha, beta, maximizingPlayer, ai_piece): # 经典minimax算法
    valid_moves = get_valid_columns(board)
    is_terminal = check_winner_sim(board)
    if not valid_moves:
        return (None, 0)
    if depth == 0 or is_terminal:
        if is_terminal:
            # 胜负判定（极端得分）
            if is_terminal == ai_piece:
                return (None, 1000)
            elif is_terminal == 3 - ai_piece:
                return (None, -1000)
            else:  # 和棋
                return (None, 0)
        else:
            return (None, evaluate_board(board, ai_piece))
    
    if maximizingPlayer:
        max_score = -math.inf
        best_col = random.choice(valid_moves)
        for col in valid_moves:
            new_board = copy.deepcopy(board)
            drop_piece(new_board, col, ai_piece)
            score = minimax(new_board, depth - 1, alpha, beta, False, ai_piece)[1]
            if score > max_score:
                max_score = score
                best_col = col
            alpha = max(alpha, score)
            if alpha >= beta:
                break  # 剪枝
        return best_col, max_score
    else:
        min_score = math.inf
        best_col = random.choice(valid_moves)
        opp_piece = 1 if ai_piece == 2 else 2
        for col in valid_moves:
            new_board = copy.deepcopy(board)
            drop_piece(new_board, col, opp_piece)
            score = minimax(new_board, depth - 1, alpha, beta, True, ai_piece)[1]
            if score < min_score:
                min_score = score
                best_col = col
            beta = min(beta, score)
            if alpha >= beta:
                break  # 剪枝
        return best_col, min_score
