#!/bin/sh

# フォントパスの設定
xset +fp $HOME/lib/fonts

# X設定の読み込み
xrdb $HOME/.Xdefaults
xmodmap $HOME/.Xmodmap

# キーボード設定
xset r rate 200 40
setxkbmap -option ctrl:nocaps

# ウィンドウマネージャーの起動
cd $HOME/scr/my_scr/python/mosakuwm
./mosakuwm 2> debug.log &

# 待機時間を追加（ウィンドウマネージャーの初期化を待つ）
sleep 1

# アプリケーションの起動
emacs &
urxvt -geometry 80x35-65-0 &
xscreensaver -no-splash &
xpylog &

# セッションを維持
exec $HOME/hogewm/eternal_sleep 