#!/usr/bin/env python3

import os
import sys
import subprocess
import re
import time
import math
from Xlib import X, XK, display

# 設定ファイルのインポート
try:
    import config as cfg
except ImportError:
    print("設定ファイルが見つかりません。デフォルト設定を使用します。", file=sys.stderr)
    # デフォルト設定
    class cfg:
        # アプリケーション設定
        TERMINAL = 'urxvt'
        EDITOR = 'emacs'
        BROWSER = 'google-chrome'
        PRIORITY_WINDOW = EDITOR

        # ウィンドウ設定
        WINDOW_MIN_WIDTH = 1920/8
        WINDOW_MIN_HEIGHT = 1280/8
        INIT_PTR_POS = 30

        # フレーム設定
        FRAME_COLOR = 'SteelBlue3'
        FRAME_SPECIAL_COLOR = 'orange'
        FRAME_THICKNESS = 2

        # 仮想スクリーン設定
        MAX_VSCREEN = 4

        # キーバインド設定
        KEY_BINDS = {}

        # パフォーマンス設定
        DRAG_INTERVAL = 1/60

# 定数定義
LEFT = 1
RIGHT = 2
UPPER = 4
LOWER = 8

# 移動方向の定数
FORWARD = 0
BACKWARD = 1

# タイル配置パターンの定数
TILE_PATTERN_GRID = 0
TILE_PATTERN_HORIZONTAL = 1
TILE_PATTERN_VERTICAL = 2

class XdumonPy:
    def __init__(self):
        self.display = display.Display()
        self.screen = self.display.screen()
        self.colormap = self.screen.default_colormap
        
        # キーバインド関連
        self.keybinds = {}
        self.pressed_keys = set()
        
        # ウィンドウ管理用の辞書とリスト
        self.managed_windows = {}
        self.exposed_windows = []
        self.framed_window = None
        
        # フレーム関連
        self.frame_windows = {}
        self.special_window = []
        
        # 仮想スクリーン関連
        self.window_vscreen = {}
        self.current_vscreen = 0
        
        # ドラッグ操作用の変数
        self.start = None
        self.start_geom = None
        self.last_dragged_time = time.time()
        
        # モニター情報の初期化
        self.monitor_geometries = self.get_available_monitor_geometries()
        self.maxsize = self.get_screen_size()
        
        # フレームウィンドウの作成
        self.create_frame_windows()
        
        # イベントの捕捉を開始
        self.catch_events()
        self.grab_buttons()
        self.grab_keys()
        
        # 既存のウィンドウを管理対象に追加
        for child in self.screen.root.query_tree().children:
            if child.get_attributes().map_state:
                self.manage_window(child)

    def get_screen_size(self):
        """スクリーン全体のサイズを取得"""
        lines = subprocess.getoutput('xrandr').split('\n')
        match = re.search(r'current (\d+) x (\d+)', lines[0])
        return {
            'width': int(match.group(1)),
            'height': int(match.group(2))
        }

    def get_available_monitor_geometries(self):
        """利用可能なモニターの情報を取得"""
        debug('function: get_available_monitor_geometries called')
        monitors = self.get_monitors_info()
        geometries = {}
        for name, monitor in monitors.items():
            if monitor['connected']:
                geom = monitor['geometry']
                if not geom:
                    debug(f'Monitor {name} is connected but not mapped.')
                    continue
                geometries[name] = {
                    'name': name,
                    'width': geom['width'],
                    'height': geom['height'],
                    'x': geom['x'],
                    'y': geom['y']
                }
        return geometries

    def get_monitors_info(self):
        """xrandrを使用して接続されているモニターの情報を取得"""
        debug('function: get_monitors_info called')
        lines = subprocess.getoutput('xrandr').split('\n')
        monitors = {}
        for line in lines[1:]:
            if 'connected' in line:
                name = line.split()[0]
                connected = ' connected' in line
                try:
                    m = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
                    width = int(m.group(1))
                    height = int(m.group(2))
                    x = int(m.group(3))
                    y = int(m.group(4))
                    geom = {
                        'width': width,
                        'height': height,
                        'x': x,
                        'y': y
                    }
                except:
                    geom = None
                primary = 'primary' in line
                monitors[name] = {
                    'connected': connected,
                    'geometry': geom,
                    'primary': primary
                }
        return monitors

    def get_monitor_coverarea(self, wgeom, mgeom):
        """ウィンドウとモニターの重なり面積を計算"""
        xmin = min(wgeom.x, mgeom['x'])
        xmax = max(wgeom.x + wgeom.width, mgeom['x'] + mgeom['width'])
        xsum = wgeom.width + mgeom['width']
        xcover = max(0, xsum - (xmax - xmin))
        
        ymin = min(wgeom.y, mgeom['y'])
        ymax = max(wgeom.y + wgeom.height, mgeom['y'] + mgeom['height'])
        ysum = wgeom.height + mgeom['height']
        ycover = max(0, ysum - (ymax - ymin))
        
        return xcover * ycover

    def get_monitor_geometry_with_window(self, window):
        """ウィンドウが最も重なっているモニターのジオメトリを取得"""
        geom = self.get_window_geometry(window)
        if not geom:
            return list(self.monitor_geometries.values())[0]

        maxcoverage = 0
        maxmonitor = list(self.monitor_geometries.values())[0]
        
        for name, monitor in self.monitor_geometries.items():
            coverarea = self.get_monitor_coverarea(geom, monitor)
            coverage = coverarea / (monitor['width'] * monitor['height'])
            normcoverage = coverarea * coverage
            if maxcoverage < normcoverage:
                maxcoverage = normcoverage
                maxmonitor = monitor
        
        return maxmonitor

    def move_window_to_monitor(self, window, dst):
        """ウィンドウを指定したモニターに移動"""
        if window not in self.managed_windows.keys():
            return
            
        src = self.managed_windows.get(window, None)
        if src is None:
            return
            
        wgeom = self.get_window_geometry(window)
        if wgeom is None:
            return
            
        # 移動先モニターのサイズに合わせてウィンドウをスケーリング
        hratio = dst['width'] / src['width']
        vratio = dst['height'] / src['height']
        
        xd = wgeom.x - src['x']
        yd = wgeom.y - src['y']
        
        x = int(xd * hratio) + dst['x']
        y = int(yd * vratio) + dst['y']
        width = int(wgeom.width * hratio)
        height = int(wgeom.height * vratio)
        
        window.configure(
            x=x,
            y=y,
            width=width,
            height=height
        )
        self.managed_windows[window] = dst

    def move_window_to_next_monitor(self, window):
        """ウィンドウを次のモニターに移動"""
        if window not in self.exposed_windows:
            return
            
        src = self.managed_windows.get(window, None)
        if src is None:
            return
            
        monitors = list(self.monitor_geometries.values())
        srcidx = monitors.index(src)
        dstidx = (srcidx + 1) % len(monitors)
        dst = monitors[dstidx]
        
        self.move_window_to_monitor(window, dst)

    def catch_events(self):
        """ルートウィンドウのイベントをキャッチするための設定"""
        self.screen.root.change_attributes(
            event_mask = X.SubstructureRedirectMask |
            X.SubstructureNotifyMask |
            X.EnterWindowMask |
            X.LeaveWindowMask |
            X.FocusChangeMask |
            X.ButtonPressMask |
            X.ButtonReleaseMask |
            X.PointerMotionMask)

    def grab_buttons(self):
        """マウスボタンのグラブ設定"""
        debug('function: grab_buttons called')
        # Alt + 左クリックでウィンドウ移動
        # Alt + 右クリックでウィンドウリサイズ
        for button in [1, 3]:  # 1: 左クリック, 3: 右クリック
            self.screen.root.grab_button(
                button,
                X.Mod1Mask,  # Alt キー
                True,
                X.ButtonPressMask |
                X.ButtonReleaseMask |
                X.PointerMotionMask,
                X.GrabModeAsync,
                X.GrabModeAsync,
                X.NONE,
                X.NONE)

    def grab_keys(self):
        """キーバインドの設定"""
        debug('function: grab_keys called')
        for (key, modifier), rule in cfg.KEY_BINDS.items():
            keysym = XK.string_to_keysym(key)
            keycode = self.display.keysym_to_keycode(keysym)
            if modifier is None:
                continue
            self.screen.root.grab_key(
                keycode,
                modifier,
                True,
                X.GrabModeAsync,
                X.GrabModeAsync
            )
            self.keybinds[(keycode, modifier)] = rule
            debug(f'debug: ({key}, {modifier}) grabbed as ({keycode}, {modifier})')

    def handle_button_press(self, event):
        """マウスボタンが押された時の処理"""
        debug('handler: handle_button_press called')
        window = event.child
        if window not in self.managed_windows.keys():
            return

        # ポインタをグラブしてドラッグ操作の準備
        self.screen.root.grab_pointer(
            True,
            X.PointerMotionMask |
            X.ButtonReleaseMask,
            X.GrabModeAsync,
            X.GrabModeAsync,
            X.NONE,
            X.NONE,
            0)

        self.start = event
        self.start_geom = self.get_window_geometry(window)

    def handle_button_release(self, event):
        """マウスボタンが離された時の処理"""
        debug('handler: handle_button_release called')
        self.display.ungrab_pointer(0)
        if event.child in self.managed_windows:
            # ウィンドウの所属モニターを更新
            self.managed_windows[event.child] = self.get_monitor_geometry_with_window(event.child)

    def handle_motion_notify(self, event):
        """マウスポインタが移動した時の処理"""
        debug('handler: handle_motion_notify called')
        if self.start is None or self.start.child == X.NONE:
            return

        # ドラッグ更新の間隔制御
        now = time.time()
        if now - self.last_dragged_time < cfg.DRAG_INTERVAL:
            return
        self.last_dragged_time = now

        # マウスの移動量を計算
        xdiff = event.root_x - self.start.root_x
        ydiff = event.root_y - self.start.root_y

        if self.start.detail == 1:  # 左クリックドラッグ: 移動
            self.start.child.configure(
                x=self.start_geom.x + xdiff,
                y=self.start_geom.y + ydiff
            )
            self.draw_frame_windows()  # フレームも一緒に移動
        elif self.start.detail == 3:  # 右クリックドラッグ: リサイズ
            # 最小サイズのチェック
            new_width = self.start_geom.width + xdiff
            new_height = self.start_geom.height + ydiff
            
            if new_width <= cfg.WINDOW_MIN_WIDTH or new_height <= cfg.WINDOW_MIN_HEIGHT:
                return
                
            self.start.child.configure(
                width=new_width,
                height=new_height
            )
            self.draw_frame_windows()  # フレームもリサイズ

    def manage_window(self, window):
        """新しいウィンドウを管理対象に追加"""
        attrs = self.get_window_attributes(window)
        if window in self.managed_windows.keys():
            return
        if attrs is None:
            return
        if attrs.override_redirect:
            return
            
        self.managed_windows[window] = self.get_monitor_geometry_with_window(window)
        self.exposed_windows.append(window)
        # 新規ウィンドウを現在の仮想スクリーンに割り当て
        self.window_vscreen[window] = self.current_vscreen
        window.map()

    def get_window_attributes(self, window):
        """ウィンドウの属性を取得"""
        try:
            return window.get_attributes()
        except:
            return None

    def get_window_geometry(self, window):
        """ウィンドウのジオメトリを取得"""
        try:
            return window.get_geometry()
        except:
            return None

    def handle_key_press(self, event):
        """キーが押された時の処理"""
        debug('handler: handle_key_press called')
        keycode = event.detail
        modifier = event.state
        entry = (keycode, modifier)
        
        rule = self.keybinds.get(entry, None)
        if rule:
            if 'method' in rule:
                method = getattr(self, rule['method'], None)
                if method:
                    arg = rule.get('arg', None)
                    if arg is not None:
                        method(event, arg)
                    else:
                        method(event)
            elif 'command' in rule:
                os.system(rule['command'])

    def cb_focus_next_window(self, event, direction=FORWARD):
        """次のウィンドウにフォーカスを移動"""
        debug('callback: cb_focus_next_window called')
        if not self.exposed_windows:
            return
            
        if self.framed_window in self.exposed_windows:
            idx = self.exposed_windows.index(self.framed_window)
            if direction == FORWARD:
                idx = (idx + 1) % len(self.exposed_windows)
            else:
                idx = (idx - 1) % len(self.exposed_windows)
        else:
            idx = 0
            
        next_window = self.exposed_windows[idx]
        self.focus_window(next_window)
        next_window.warp_pointer(cfg.INIT_PTR_POS, cfg.INIT_PTR_POS)

    def focus_window(self, window):
        """指定したウィンドウにフォーカスを設定"""
        debug('function: focus_window called')
        if window not in self.exposed_windows:
            return
            
        window.set_input_focus(X.RevertToParent, 0)
        window.configure(stack_mode=X.Above)
        self.framed_window = window
        self.draw_frame_windows()

    def cb_halve_window(self, event, direction):
        """ウィンドウを半分のサイズに変更"""
        debug('callback: cb_halve_window called')
        if not self.framed_window:
            return
            
        self.halve_window(self.framed_window, direction)
        self.framed_window.warp_pointer(cfg.INIT_PTR_POS, cfg.INIT_PTR_POS)

    def halve_window(self, window, direction):
        """ウィンドウを指定した方向に半分のサイズにする"""
        if window not in self.exposed_windows:
            return
            
        geom = self.get_window_geometry(window)
        if not geom:
            return
            
        if direction & (LEFT | RIGHT) != 0 and geom.width <= cfg.WINDOW_MIN_WIDTH:
            return
        if direction & (UPPER | LOWER) != 0 and geom.height <= cfg.WINDOW_MIN_HEIGHT:
            return
            
        x, y = geom.x, geom.y
        width, height = geom.width, geom.height
        
        if direction & (LEFT | RIGHT) != 0:
            width //= 2
        if direction & (UPPER | LOWER) != 0:
            height //= 2
            
        if direction & RIGHT != 0:
            x += width
        if direction & LOWER != 0:
            y += height
            
        window.configure(
            x=x,
            y=y,
            width=width,
            height=height
        )

    def cb_move_window_to_next_monitor(self, event):
        """ウィンドウを次のモニターに移動"""
        debug('callback: cb_move_window_to_next_monitor called')
        if not self.framed_window:
            return
            
        self.move_window_to_next_monitor(self.framed_window)
        self.framed_window.warp_pointer(cfg.INIT_PTR_POS, cfg.INIT_PTR_POS)

    def loop(self):
        """メインイベントループ"""
        while True:
            event = self.display.next_event()
            if event.type == X.MapRequest:
                self.handle_map_request(event)
            elif event.type == X.DestroyNotify:
                self.handle_destroy_notify(event)
            elif event.type == X.ButtonPress:
                self.handle_button_press(event)
            elif event.type == X.ButtonRelease:
                self.handle_button_release(event)
            elif event.type == X.MotionNotify:
                self.handle_motion_notify(event)
            elif event.type == X.KeyPress:
                self.handle_key_press(event)

    def handle_map_request(self, event):
        """新しいウィンドウが作成された時のハンドラ"""
        self.manage_window(event.window)

    def handle_destroy_notify(self, event):
        """ウィンドウが破棄された時のハンドラ"""
        if event.window in self.managed_windows:
            self.managed_windows.pop(event.window)
            if event.window in self.exposed_windows:
                self.exposed_windows.remove(event.window)
            if event.window in self.window_vscreen:
                self.window_vscreen.pop(event.window)
            if event.window == self.framed_window:
                self.framed_window = None
                self.unmap_frame_windows()

    def select_vscreen(self, num):
        """指定した仮想スクリーンに切り替え"""
        debug('function: select_vscreen called')
        if num < 0 or num >= cfg.MAX_VSCREEN:
            return

        self.current_vscreen = num
        self.exposed_windows = []

        # 現在の仮想スクリーンに属するウィンドウのみを表示
        for window in self.managed_windows.keys():
            if self.window_vscreen[window] == num:
                window.map()
                self.exposed_windows.append(window)
            else:
                window.unmap()

    def send_window_to_next_vscreen(self, window, direction):
        """ウィンドウを次または前の仮想スクリーンに移動"""
        debug('function: send_window_to_next_vscreen called')
        if window not in self.exposed_windows:
            return None

        current_idx = self.window_vscreen[window]
        if direction == FORWARD:
            next_idx = (current_idx + 1) % cfg.MAX_VSCREEN
        else:
            next_idx = (current_idx - 1) % cfg.MAX_VSCREEN

        self.window_vscreen[window] = next_idx
        return next_idx

    def create_frame_windows(self):
        """フレームウィンドウの作成"""
        debug('function: create_frame_windows called')
        self.frame_pixel = self.colormap.alloc_named_color(cfg.FRAME_COLOR).pixel
        
        for side in ['left', 'right', 'upper', 'lower']:
            window = self.screen.root.create_window(
                0, 0, 16, 16, 0,
                self.screen.root_depth,
                X.InputOutput,
                background_pixel=self.frame_pixel,
                override_redirect=True
            )
            window.map()
            self.frame_windows[side] = window

    def draw_frame_windows(self):
        """フレームウィンドウの描画"""
        if self.framed_window is None:
            return

        # フレームの色を設定
        if self.framed_window in self.special_window:
            new_frame_pixel = self.colormap.alloc_named_color(cfg.FRAME_SPECIAL_COLOR).pixel
        else:
            new_frame_pixel = self.colormap.alloc_named_color(cfg.FRAME_COLOR).pixel

        # 各フレームの色を更新
        for side in ['left', 'right', 'upper', 'lower']:
            self.frame_windows[side].change_attributes(background_pixel=new_frame_pixel)
            self.frame_windows[side].clear_area(0, 0, 0, 0, True)

        # フレームの位置とサイズを設定
        geom = self.get_window_geometry(self.framed_window)
        if geom is None:
            return

        for side in ['left', 'right', 'upper', 'lower']:
            x, y, width, height = 0, 0, 0, 0
            if side == 'left':
                x = geom.x
                y = geom.y
                width = cfg.FRAME_THICKNESS
                height = geom.height
            elif side == 'right':
                x = geom.x + geom.width - cfg.FRAME_THICKNESS
                y = geom.y
                width = cfg.FRAME_THICKNESS
                height = geom.height
            elif side == 'upper':
                x = geom.x
                y = geom.y
                width = geom.width
                height = cfg.FRAME_THICKNESS
            elif side == 'lower':
                x = geom.x
                y = geom.y + geom.height - cfg.FRAME_THICKNESS
                width = geom.width
                height = cfg.FRAME_THICKNESS

            self.frame_windows[side].configure(
                x=x,
                y=y,
                width=width,
                height=height,
                stack_mode=X.Above
            )
            self.frame_windows[side].map()

    def map_frame_windows(self):
        """フレームウィンドウを表示"""
        for side in ['left', 'right', 'upper', 'lower']:
            self.frame_windows[side].map()

    def unmap_frame_windows(self):
        """フレームウィンドウを非表示"""
        for side in ['left', 'right', 'upper', 'lower']:
            self.frame_windows[side].unmap()

    def get_tile_layout(self, tile_num):
        """タイル配置のレイアウトを計算"""
        debug('function: get_tile_layout called')
        tmp = int(math.sqrt(tile_num))
        # (row, col)を返す
        if tmp**2 == tile_num:
            return (tmp, tmp)
        if (tmp+1)*tmp >= tile_num:
            return (tmp, tmp+1)
        return (tmp+1, tmp+1)

    def tile_windows(self, window, pattern=TILE_PATTERN_GRID):
        """ウィンドウをタイル状に配置"""
        debug('function: tile_windows called')
        # 現在のモニターを取得
        monitor = self.managed_windows.get(window, None)
        if monitor is None:
            return

        # 現在のモニターに表示されているウィンドウを収集
        target_windows = []
        for win in self.exposed_windows:
            if monitor == self.managed_windows.get(win, None):
                target_windows.append(win)

        # ウィンドウをIDでソート（安定した配置のため）
        def sort_key(window):
            return window.id
        target_windows.sort(key=sort_key)

        # エディタウィンドウを優先的に配置
        eidx = None
        for i in range(len(target_windows)):
            if cfg.PRIORITY_WINDOW in self.get_window_class(target_windows[i]).lower():
                eidx = i

        if pattern == TILE_PATTERN_GRID:
            self.tile_windows_grid(target_windows, monitor, eidx)
        elif pattern == TILE_PATTERN_HORIZONTAL:
            self.tile_windows_horizontal(target_windows, monitor, eidx)
        elif pattern == TILE_PATTERN_VERTICAL:
            self.tile_windows_vertical(target_windows, monitor, eidx)

        # ポインタを移動
        window.warp_pointer(cfg.INIT_PTR_POS, cfg.INIT_PTR_POS)

    def tile_windows_grid(self, target_windows, monitor, eidx):
        """グリッドパターンでウィンドウを配置"""
        if not target_windows:
            return

        # レイアウトの計算
        nrows, ncols = self.get_tile_layout(len(target_windows))
        offcuts_num = nrows*ncols - len(target_windows)

        # エディタウィンドウを左下に配置
        if eidx is not None:
            target_windows[eidx], target_windows[ncols*(nrows-1)-1] = \
                target_windows[ncols*(nrows-1)-1], target_windows[eidx]

        # ウィンドウの配置
        for row in reversed(range(nrows)):
            for col in reversed(range(ncols)):
                if not target_windows:
                    break
                win = target_windows.pop(0)
                
                # 位置とサイズの計算
                x = monitor['x'] + monitor['width']*col//ncols
                width = monitor['width']//ncols
                
                # 下段の空きスペースを利用
                if row == 1 and col < offcuts_num:
                    height = monitor['height']*2//nrows
                    y = monitor['y']
                else:
                    height = monitor['height']//nrows
                    y = monitor['y'] + monitor['height']*row//nrows
                
                # ウィンドウの設定
                win.configure(
                    x=x,
                    y=y,
                    width=width,
                    height=height
                )

    def tile_windows_horizontal(self, target_windows, monitor, eidx):
        """水平分割パターンでウィンドウを配置"""
        if not target_windows:
            return

        # エディタウィンドウを最上部に配置
        if eidx is not None:
            target_windows[eidx], target_windows[0] = \
                target_windows[0], target_windows[eidx]

        num_windows = len(target_windows)
        for i, win in enumerate(target_windows):
            # 位置とサイズの計算
            x = monitor['x']
            y = monitor['y'] + (monitor['height'] * i) // num_windows
            width = monitor['width']
            height = monitor['height'] // num_windows

            # ウィンドウの設定
            win.configure(
                x=x,
                y=y,
                width=width,
                height=height
            )

    def tile_windows_vertical(self, target_windows, monitor, eidx):
        """垂直分割パターンでウィンドウを配置"""
        if not target_windows:
            return

        # エディタウィンドウを最左部に配置
        if eidx is not None:
            target_windows[eidx], target_windows[0] = \
                target_windows[0], target_windows[eidx]

        num_windows = len(target_windows)
        for i, win in enumerate(target_windows):
            # 位置とサイズの計算
            x = monitor['x'] + (monitor['width'] * i) // num_windows
            y = monitor['y']
            width = monitor['width'] // num_windows
            height = monitor['height']

            # ウィンドウの設定
            win.configure(
                x=x,
                y=y,
                width=width,
                height=height
            )

    def cb_tile_windows(self, event, pattern=TILE_PATTERN_GRID):
        """タイル配置のコールバック"""
        debug('callback: cb_tile_windows called')
        if not self.framed_window:
            return
        self.tile_windows(self.framed_window, pattern)
        self.focus_window(self.framed_window)

    def get_window_class(self, window):
        """ウィンドウのクラス名を取得"""
        try:
            cmd, cls = window.get_wm_class()
            return cls if cls is not None else ''
        except:
            return ''

def main():
    wm = XdumonPy()
    try:
        wm.loop()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    main() 