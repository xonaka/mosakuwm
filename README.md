# mosakuwm

## 概要
mosakuwmは、OSS である [xpywm](https://github.com/h-ohsaki/xpywm) をベースとして開発されたX11ウィンドウマネージャです。マルチモニタ環境への対応、仮想デスクトップ機能、柔軟なキーバインド設定、外部ツールとの連携、画面録画機能など、多彩な機能を備えています。

本プロジェクトの開発は、[xpywm](https://github.com/h-ohsaki/xpywm) および [hogewm](https://github.com/void-hoge/hogewm) の設計と実装から多くを学び、それらに独自の機能拡張を重ねる形で進めてまいりました。両プロジェクトの開発者の皆様に、心より感謝申し上げます。
## 特徴
- xpywmの基本機能を継承しつつ、以下の拡張を実装：
  - 複数モニタ・仮想デスクトップ対応（XRandR利用）
  - キーバインドはソース内の`KEY_BINDS`辞書で一元管理
  - ウィンドウのタイル・分割・最大化・移動・スタック
  - フォーカス/特殊ウィンドウの枠色ハイライト
  - スクリーンショット・画面録画（import/ffmpeg利用）
  - xpymon等の外部ツール連携
  - 設定ファイル不要、全てPythonコードで完結
- ユーザーごとのカスタマイズは`~/.mosakurc`（Pythonスクリプト）で柔軟に可能

## インストール
1. 依存パッケージのインストール
   ```sh
   sudo apt install python3-xlib x11-utils x11-xserver-utils xrandr ffmpeg pactl
   ```
2. リポジトリをクローン
   ```sh
   git clone <リポジトリURL>
   cd mosakuwm
   ```
3. 実行権限を付与
   ```sh
   chmod +x mosakuwm
   ```
4. Xセッションで起動
   - `~/.xinitrc`に`exec /path/to/mosakuwm`を追加、または
   - X上で`./mosakuwm`を実行

## 使い方
- 起動後、各種キーバインドでウィンドウ操作が可能です
- キーバインドや動作を変更したい場合は`mosakuwm`本体、または`~/.mosakurc`を編集してください

## カスタマイズ
mosakuwmは起動時にユーザーごとのRCスクリプト（`~/.mosakurc`）を自動で読み込みます。RCスクリプトは任意のPythonコードで、グローバル変数やキーバインド、関数・メソッドの上書きも可能です。

例：枠色の変更とキーバインド追加
```python
# ~/.mosakurc
FRAME_COLOR = 'lemon chiffon'
KEY_BINDS[('9', X.Mod1Mask | X.ControlMask)] = {
    'command': 'xterm &'
}
```

利用可能な変数や`KEY_BINDS`の詳細はソースを参照してください。

## 主なキーバインド例
| キー操作             | 動作内容                     |
|----------------------|------------------------------|
| Ctrl+Alt+1           | ターミナル起動               |
| Ctrl+Alt+2           | エディタ起動                 |
| Ctrl+Alt+3           | ブラウザ起動                 |
| Ctrl+Alt+4           | メモ帳（emacs）起動          |
| Ctrl+Alt+5           | xpymon表示/非表示＋全ウィンドウ調整 |
| Ctrl+Alt+m           | ウィンドウ最大化             |
| Ctrl+Alt+h/l/j/k     | ウィンドウ分割（左右上下）   |
| Ctrl+Alt+n           | ウィンドウを次のモニタへ      |
| Ctrl+Alt+z           | ウィンドウを閉じる           |
| Ctrl+Alt+t           | 全ウィンドウをタイル配置      |
| Alt+F1～F4           | 仮想デスクトップ切替         |
| Alt+F12              | 画面録画                     |

詳細は`KEY_BINDS`辞書を参照してください。

### モニタ内ウィンドウ遷移モード（cb_toggle_monitor_local_selection）
- **Ctrl+Alt+0** で有効/無効をトグルできます。
- 有効時は「現在フォーカス中のウィンドウが属するモニタ内」のウィンドウだけをTab遷移（Ctrl+Alt+i）で切り替え可能になります。
- 無効時は全モニタのウィンドウが遷移対象になります。
- **用途例:** デュアル・マルチモニタ環境で、特定モニタ内だけでウィンドウを切り替えたい場合や、他モニタのウィンドウに邪魔されたくない場合に便利です。
- 解除は再度Ctrl+Alt+0を押すだけです。

### 外部モニタ強制切替（cb_force_external_monitor）
- **Ctrl+Alt+b** で実行できます。
- 既知の外部モニタ（HDMI/DP等）をon/offし、必要に応じて再構成します。
- 例えば「外部ディスプレイを一時的に切り離したい」「認識し直したい」場合などに便利です。
- 内蔵ディスプレイ（例: eDP-1）はoffにしません。

## 開発・コントリビュート
- コードは1ファイル構成で、拡張や修正が容易です
- バグ報告・機能要望・PR歓迎
- 高度なカスタマイズはPythonソースを直接編集してください

## トラブルシューティング
- **キーバインドが効かない**: Xサーバーのキーマップや他WMとの競合を確認
- **xpymon等が起動しない**: パス・インストール状況を確認
- **マルチモニタが正しく動作しない**: XRandRの設定を確認

## ライセンス
GPL-3.0 License

---

本プロジェクトは[xpywm](https://github.com/h-ohsaki/xpywm) および [hogewm](https://github.com/void-hoge/hogewm) の開発者の皆様に深く感謝しつつ、両プロジェクトを参考に独自の工夫を加えたものです。自由にご利用・改変・配布してください。

