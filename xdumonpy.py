#!/usr/bin/env python3

import os
import sys
import subprocess
import re
from Xlib import X, XK, display

# 基本的な設定
INIT_PTR_POS = 30  # マウスポインタの初期位置
WINDOW_MIN_WIDTH = 1920/8  # ウィンドウの最小幅
WINDOW_MIN_HEIGHT = 1280/8  # ウィンドウの最小高さ

# ウィンドウの方向を示す定数
LEFT = 1
RIGHT = 2
UPPER = 4
LOWER = 8

def debug(msg):
    """デバッグメッセージを標準エラー出力に出力"""
    print(msg, file=sys.stderr, flush=True)

class XdumonPy:
    def __init__(self):
        self.display = display.Display()
        self.screen = self.display.screen()
        self.colormap = self.screen.default_colormap
        
        # ウィンドウ管理用の辞書とリスト
        self.managed_windows = {}  # 管理対象のウィンドウを保持
        self.exposed_windows = []  # 表示中のウィンドウを保持
        
        # モニター情報の初期化
        self.monitor_geometries = self.get_available_monitor_geometries()
        self.maxsize = self.get_screen_size()
        
        # イベントの捕捉を開始
        self.catch_events()
        
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
            X.FocusChangeMask)

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

    def loop(self):
        """メインイベントループ"""
        while True:
            event = self.display.next_event()
            # イベントの種類に応じて適切なハンドラを呼び出す
            if event.type == X.MapRequest:
                self.handle_map_request(event)
            elif event.type == X.DestroyNotify:
                self.handle_destroy_notify(event)

    def handle_map_request(self, event):
        """新しいウィンドウが作成された時のハンドラ"""
        self.manage_window(event.window)

    def handle_destroy_notify(self, event):
        """ウィンドウが破棄された時のハンドラ"""
        if event.window in self.managed_windows:
            self.managed_windows.pop(event.window)
            if event.window in self.exposed_windows:
                self.exposed_windows.remove(event.window)

def main():
    wm = XdumonPy()
    try:
        wm.loop()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    main() 