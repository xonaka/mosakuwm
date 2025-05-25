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

class XdumonPy:
    def __init__(self):
        self.display = display.Display()
        self.screen = self.display.screen()
        self.colormap = self.screen.default_colormap
        
        # ウィンドウ管理用の辞書とリスト
        self.managed_windows = {}  # 管理対象のウィンドウを保持
        self.exposed_windows = []  # 表示中のウィンドウを保持
        
        # イベントの捕捉を開始
        self.catch_events()
        
        # 既存のウィンドウを管理対象に追加
        for child in self.screen.root.query_tree().children:
            if child.get_attributes().map_state:
                self.manage_window(child)

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

    def get_monitor_geometry_with_window(self, window):
        """ウィンドウが表示されているモニターのジオメトリを取得"""
        # 基本実装として、プライマリモニターのジオメトリを返す
        return {
            'x': 0,
            'y': 0,
            'width': self.screen.width_in_pixels,
            'height': self.screen.height_in_pixels
        }

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