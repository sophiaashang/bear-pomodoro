# Bear Pomodoro · 小熊陪学番茄钟

一个会陪你学习的桌面悬浮番茄钟。一只戴金丝眼镜、系红领结的小熊，跟着你的节奏看书、敲电脑、喝咖啡、拉大提琴、打麻将。

A tiny always-on-top Pomodoro timer for Windows, with an animated bear, built-in focus music and an auto-looping 25/5 cycle. (UI text is Chinese; see [English notes](#english-notes) below.)

![小熊的九套日常](docs/bear-scenes.png)

上排是安静时，下排是放歌时（戴耳机、飘音符）。

## 特点

- **全自动循环**：专注 25 分钟 → 休息 5 分钟 → 再专注，不用每轮点按钮。每 4 个番茄后自动长休息 15 分钟。
- **小熊会动**：专注时轮流 看书 / 敲电脑 / 喝咖啡 / 写字；休息时轮流 喝茶打盹 / 拉大提琴 / 弹吉他 / 打麻将 / 抱爆米花看电影；到点会举手欢呼；放歌时戴耳机晃脑袋。全部用 Pillow 逐帧绘制，没有任何图片素材。
- **只放纯音乐**：从一批公开的学习歌单里随机取曲，放之前先查歌词，有歌词的自动跳过。窗内直接播放，不会拉起别的播放器。
- **提示音自己合成**：开始、收工、休息三种音效由代码合成（风铃 / 马林巴质感），不带任何音频文件。
- **两百多条提示语**：每个阶段随机抽一句，同一轮内不重复。可以在 `phrases.json` 里随便增删。
- **鼠标移开就缩起来**：鼠标不在窗口上时，自动收成一个小胶囊（小熊 + 倒计时 + 一条细进度条）并变透明；鼠标移过去立刻展开成完整界面。每次换阶段会自动展开几秒，免得错过提示语。窗口放在哪个屏幕角，就固定那个角的边缘伸缩，不会跑位。
- **不打扰**：置顶、无边框、圆角、半透明；不出现在任务栏和 Alt-Tab；展开和收起各用固定尺寸；随便拖动。
- **今日计数**：记录今天完成了几个番茄，次日自动清零。

## 安装与运行

只支持 Windows 10 / 11。

**1. 装 Python 3**：到 <https://www.python.org/downloads/> 下载安装。安装界面最下面一定要勾上 **Add python.exe to PATH**，不勾的话后面会找不到命令。tkinter 随 Python 一起装好，不用另外装。

**2. 拿到代码**，二选一：
- 会用 git：`git clone https://github.com/sophiaashang/bear-pomodoro.git`
- 不会用：在仓库页面点绿色的 **Code**，选 **Download ZIP**，解压到任意文件夹。

**3. 启动**，二选一：
- **双击 `start.bat`**。第一次会自动安装 Pillow，之后直接启动，窗口出现在屏幕右下角。
- 或者在文件夹里打开终端：

```bash
pip install -r requirements.txt
pythonw bear_pomodoro.py        # 无控制台窗口运行
# 或 python bear_pomodoro.py    # 带控制台，出错时能看到报错
```

也可以传入一个开始时间戳，让倒计时从那个时刻算起：`pythonw bear_pomodoro.py 1760000000`。

**启动不了？**
- 双击后提示找不到 Python：说明没装或没勾 PATH，重装一次并勾上。
- 窗口一闪就没了：用 `python bear_pomodoro.py` 启动，看终端里的报错。
- 点“音乐”提示网络不通：音乐走的是网易云的非官方接口，可能被网络环境挡住或接口已变。计时功能不受影响。

**退出**：展开状态下点右上角的 ✕。**开机自启**：把 `start.bat` 的快捷方式放进 `shell:startup` 文件夹（Win+R 输入 `shell:startup`）。

第一次运行会在脚本目录生成 `pomodoro_sounds/`（提示音）；点播放后会生成 `pomodoro_music/`（歌曲缓存）。这些都已写进 `.gitignore`。

## 操作

| 按钮 | 作用 |
| --- | --- |
| ▶ 音乐 / ⏸ 音乐 | 开始播放；播放中显示 ⏸，点一下暂停，再点继续 |
| ⏭ | 换下一首 |
| ⏱ 停表 / 继续 | 冻结或恢复计时（和音乐的暂停是两回事） |
| 提前休息 / 跳过休息 | 手动切换阶段（不算完成一个番茄） |
| ✕ | 退出 |

在窗口空白处按住左键可以拖动。再次启动会自动关掉上一个旧窗口，不会叠出多个。

## 自定义

- **提示语**：编辑 `phrases.json`，六个分类 `focus / done / rest / long / back / pause`，每个是一个字符串数组。建议每句不超过 20 个字，否则会超出窗口宽度。文件缺失或格式有误时，会退回内置的少量默认提示语。
- **时长**：改 `bear_pomodoro.py` 顶部的 `FOCUS`、`REST`、`LONG`（秒）和 `SET`（几个番茄后长休息）。
- **收起行为**：`AUTO_COLLAPSE = False` 可以关掉自动收起，窗口一直展开；`ALPHA_FULL / ALPHA_DIM` 是展开和收起时的透明度；`COLLAPSE_DELAY` 是鼠标离开后多久收起；`PIN_SECONDS` 是换阶段后保持展开的秒数；`CW, CH` 是收起后的胶囊尺寸。
- **歌单**：改 `PLAYLISTS`，每项是 `(显示名, 歌单ID)`，歌单 ID 是网易云歌单链接里的数字。
- **配色**：改 `BG / FG / GOLD / ACC / TEAL` 等颜色常量。

## 关于音乐的说明

音乐功能通过网易云音乐的**非官方**公开接口取得歌单和试听链接，仅供个人学习使用。

- 本仓库**不包含**任何音频文件，歌曲只在你本机运行时下载到本地缓存，歌曲版权归原作者和版权方所有。
- 这些接口不是官方 API，随时可能变化或失效；失效时窗口会提示“网络不通”或“没找到能放的歌”，计时功能不受影响。
- 请自行评估并遵守当地法律与平台服务条款。如果你不想使用这个功能，直接不点“音乐”按钮即可，它不会自动播放。
- 有无歌词是靠歌词接口加启发式判断的，偶尔会有误判。

## 已知限制

- 仅支持 Windows（用到了 MCI 播放、DWM 圆角、窗口扩展样式等系统接口）。
- 窗口位置默认在主显示器右下角，不会记住上次拖动到的位置。
- 音量固定，暂时没有音量调节。

## 工作方式（简述）

- 整个界面画在一块 `tkinter.Canvas` 上，按钮和进度条都是手绘的圆角形状，布局写死，所以窗口不会因为内容变化而改变大小。
- 小熊由 `render_bear()` 以 3 倍超采样绘制再缩小，所以边缘平滑；约 11 帧每秒，单帧耗时在毫秒级。
- Windows 的 MCI 设备绑定到打开它的线程，所以后台线程只负责取曲和下载，真正的播放调用都切回主线程。

## English notes

- Windows 10/11 only. `pip install -r requirements.txt`, then `pythonw bear_pomodoro.py`.
- Auto-loops 25 min focus → 5 min rest, with a 15 min long break after every 4 pomodoros. Pause / skip buttons are available.
- Music comes from public NetEase Cloud Music playlists through **unofficial** endpoints, lyrics are checked so only instrumental tracks are played. No audio is bundled; use at your own discretion and respect the rights holders and the platform's terms.
- UI strings live in `phrases.json` (Chinese); durations, playlists and colours are constants at the top of `bear_pomodoro.py`.

## 许可证

[MIT](LICENSE)。使用前请把 `LICENSE` 里的版权人占位符改成你自己的名字。
