#!/usr/bin/env python3

from Xlib import X

# アプリケーション設定
TERMINAL = 'urxvt'  # 端末エミュレータ
EDITOR = 'emacs'    # エディタ
BROWSER = 'google-chrome'  # ブラウザ
PRIORITY_WINDOW = EDITOR  # タイル配置時に優先するウィンドウ

# ウィンドウ設定
WINDOW_MIN_WIDTH = 1920/8   # ウィンドウの最小幅
WINDOW_MIN_HEIGHT = 1280/8  # ウィンドウの最小高さ
INIT_PTR_POS = 30          # マウスポインタの初期位置

# フレーム設定
FRAME_COLOR = 'SteelBlue3'        # 通常のフレーム色
FRAME_SPECIAL_COLOR = 'orange'    # 特別なウィンドウのフレーム色
FRAME_THICKNESS = 2              # フレームの太さ

# 仮想スクリーン設定
MAX_VSCREEN = 4  # 仮想スクリーンの最大数

# タイル配置設定
TILE_RATIOS = {
    'main_pane_ratio': 0.6,      # メインペインの画面比率（水平・垂直分割時）
    'grid_main_ratio': 0.5,      # グリッド配置時のメインウィンドウ比率
    'horizontal_ratios': [0.5],  # 水平分割時の比率プリセット
    'vertical_ratios': [0.5],    # 垂直分割時の比率プリセット
}

# キーバインド設定
KEY_BINDS = {
    # ウィンドウ操作
    ('i', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_focus_next_window',
        'arg': 0  # FORWARD
    },
    
    # アプリケーション起動
    ('1', X.Mod1Mask | X.ControlMask): {
        'command': f'{TERMINAL} &'
    },
    ('2', X.Mod1Mask | X.ControlMask): {
        'command': f'{EDITOR} &'
    },
    ('3', X.Mod1Mask | X.ControlMask): {
        'command': f'{BROWSER} &'
    },
    
    # ウィンドウ分割
    ('h', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_halve_window',
        'arg': 1  # LEFT
    },
    ('l', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_halve_window',
        'arg': 2  # RIGHT
    },
    ('j', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_halve_window',
        'arg': 8  # LOWER
    },
    ('k', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_halve_window',
        'arg': 4  # UPPER
    },
    
    # モニター操作
    ('n', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_move_window_to_next_monitor'
    },
    
    # 仮想スクリーン切り替え
    ('F1', X.Mod1Mask): {
        'method': 'cb_select_vscreen',
        'arg': 0
    },
    ('F2', X.Mod1Mask): {
        'method': 'cb_select_vscreen',
        'arg': 1
    },
    ('F3', X.Mod1Mask): {
        'method': 'cb_select_vscreen',
        'arg': 2
    },
    ('F4', X.Mod1Mask): {
        'method': 'cb_select_vscreen',
        'arg': 3
    },
    
    # 仮想スクリーン間のウィンドウ移動
    ('d', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_send_window_to_next_vscreen',
        'arg': 0  # FORWARD
    },
    ('a', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_send_window_to_next_vscreen',
        'arg': 1  # BACKWARD
    },
    
    # タイル配置
    ('t', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_tile_windows',
        'arg': 0  # TILE_PATTERN_GRID
    },
    ('h', X.Mod1Mask | X.ShiftMask): {
        'method': 'cb_tile_windows',
        'arg': 1  # TILE_PATTERN_HORIZONTAL
    },
    ('v', X.Mod1Mask | X.ShiftMask): {
        'method': 'cb_tile_windows',
        'arg': 2  # TILE_PATTERN_VERTICAL
    },
    
    # タイル比率調整
    ('plus', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_adjust_main_ratio',
        'arg': 0.1  # 増加
    },
    ('minus', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_adjust_main_ratio',
        'arg': -0.1  # 減少
    },
    ('r', X.Mod1Mask | X.ControlMask): {
        'method': 'cb_reset_main_ratio'
    },
    
    # 設定再読み込み
    ('R', X.Mod1Mask | X.ControlMask | X.ShiftMask): {
        'method': 'cb_reload_config'
    }
}

# パフォーマンス設定
DRAG_INTERVAL = 1/60  # ドラッグ更新の間隔（秒） 