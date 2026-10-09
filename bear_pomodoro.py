# -*- coding: utf-8 -*-
"""小熊陪学番茄钟 v9 —— 单文件 tkinter，固定尺寸悬浮小窗
- 全自动循环：专注25 -> 休息5 -> 专注25 ... 每4个番茄后长休息15分钟；不用每轮点按钮
  (暂停计时 / 提前休息 / 跳过休息 随时可用；今日完成数记在 pomodoro_state.json)
- 熊按场景换着做事：专注时 看书/敲电脑/喝咖啡/写字；休息时 喝茶打盹/拉大提琴/弹电吉他/打麻将/抱爆米花看电影
- 音乐只放纯音乐：歌单取曲后先查歌词，有歌词的自动跳过；窗内自己播(MCI)，不拉起网易云
- 提示音自己合成，缓存在 pomodoro_sounds/
- 置顶、无边框、圆角、不进任务栏；窗口固定尺寸
用法: pythonw bear_pomodoro.py [开始时间戳]
"""
import array, ctypes, datetime, json, math, os, random, re, sys, threading, time, urllib.request, wave
import ctypes.wintypes as wt
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(HERE, "pomodoro_music")
SOUND_DIR = os.path.join(HERE, "pomodoro_sounds")
PID_FILE = os.path.join(HERE, "pomodoro.pid")
STATE_FILE = os.path.join(HERE, "pomodoro_state.json")
LOG = os.path.join(HERE, "pomodoro.log")
os.makedirs(MUSIC_DIR, exist_ok=True); os.makedirs(SOUND_DIR, exist_ok=True)

FOCUS, REST, LONG = 25 * 60, 5 * 60, 15 * 60
SET = 4   # 几个番茄后长休息

# 全是纯音乐/轻音乐歌单（取曲时还会逐首查歌词，有词的跳过）
PLAYLISTS = [
    ("纯音乐图书馆·专注学习", 316192152),
    ("安静的纯音乐", 486899256),
    ("想难题/背单词纯音乐", 482655706),
    ("阅读轻音乐·温柔静心", 9838843201),
    ("看书学习轻音乐", 3067329591),
    ("学霸模式·古典", 2821046530),
    ("刷题古典纯音乐", 2167554558),
    ("大提琴·心灵深处的声音", 2936325936),
    ("书房阅读·咖啡馆爵士", 7307871195),
    ("吉他治愈纯音乐", 8661917065),
    ("静心学习·提升专注力", 2905371840),
    ("深度专注·写论文", 8161839236),
    ("Lofi阅览室", 8756910202),
    ("Lofi自习室", 8143630267),
    ("α波记忆强化", 2390862226),
    ("40赫兹高效专注", 13025735367),
    ("霍格沃茨自习室·雨声", 5209217058),
]
# ---- 提示语：优先读 phrases.json，缺失或格式不对时退回内置的少量默认值 ----
_DEFAULT_PHRASES = {
    "focus": ["书翻开，歌开起，慢慢进入状态", "这一轮，只做一件事", "我在，不急，慢慢来"],
    "done": ["到点啦，站起来，看看窗外", "起来溜达溜达，喝杯水", "这一轮收工，手离开键盘"],
    "rest": ["休息中，别刷手机", "活动一下肩颈吧", "喝水了吗"],
    "long": ["四个番茄了，这一组很扎实", "长休息，真的去走一走"],
    "back": ["休息结束，回来吧", "电量补满，开始下一轮"],
    "pause": ["停表了，想继续就点一下", "暂停中，不计时"],
}


def load_phrases():
    data = {k: list(v) for k, v in _DEFAULT_PHRASES.items()}
    try:
        with open(os.path.join(HERE, "phrases.json"), encoding="utf-8") as f:
            raw = json.load(f)
        for k in data:
            v = raw.get(k)
            if isinstance(v, list):
                v = [x.strip() for x in v if isinstance(x, str) and x.strip()]
                if v: data[k] = v
    except Exception as e:
        log("phrases.json 读取失败，使用内置默认:", repr(e))
    return data


PHRASES = load_phrases()


class Deck:
    """洗牌取句：一轮抽完才重新洗牌，且换牌时不会让上一句紧接着再出现"""
    def __init__(self, items):
        self.items = list(items); self.q = []; self.last = None

    def draw(self):
        if not self.q:
            self.q = self.items[:]; random.shuffle(self.q)
            if len(self.q) > 1 and self.q[-1] == self.last:
                self.q[0], self.q[-1] = self.q[-1], self.q[0]
        self.last = self.q.pop()
        return self.last


DECKS = {k: Deck(v) for k, v in PHRASES.items()}


def say(cat): return DECKS[cat].draw()


FOCUS_SCENES = ["book", "laptop", "coffee", "writing"]
REST_SCENES = ["tea", "cello", "guitar", "mahjong", "movie"]

BG, FG, DIM, ACC, GOLD, TEAL = "#16141a", "#ece7dc", "#a39eae", "#a94442", "#d4af37", "#7fb7a4"
BTN_RED = "#e5736f"        # 按钮上的红字（比装饰用的 ACC 更亮，深色底上才看得清）
PILL, PILL_HOV, TRACK = "#241f2b", "#322b3b", "#3a3446"
W, H = 300, 182            # 展开时的窗口尺寸
CW, CH = 168, 62           # 收起时的小胶囊：只留小熊、倒计时和一条细进度条
AUTO_COLLAPSE = True       # 鼠标移开自动收起并变透明，移过去自动展开；设为 False 则一直展开
ALPHA_FULL, ALPHA_DIM = 0.95, 0.55
COLLAPSE_DELAY = 0.9       # 鼠标离开后多久收起（秒）
PIN_SECONDS = 7.0          # 启动时、每次换阶段时先展开多久，让你看到提示语


def log(*a):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + " ".join(map(str, a)) + "\n")
    except Exception: pass


def single_instance():
    try:
        old = int(open(PID_FILE).read().strip())
        if old != os.getpid():
            os.system(f"taskkill /F /PID {old} >nul 2>&1")
    except Exception: pass
    open(PID_FILE, "w").write(str(os.getpid()))


def load_today():
    try:
        d = json.load(open(STATE_FILE, encoding="utf-8"))
        if d.get("date") == str(datetime.date.today()): return int(d.get("count", 0))
    except Exception: pass
    return 0


def save_today(n):
    try:
        json.dump({"date": str(datetime.date.today()), "count": n}, open(STATE_FILE, "w", encoding="utf-8"))
    except Exception as e: log("state err", repr(e))


# =====================  音效合成（纯标准库）  =====================
SR = 44100
BELL = [(1.0, 1.0, 2.6), (2.0, 0.34, 4.5), (2.76, 0.18, 6.0), (4.1, 0.07, 9.0)]
MARIMBA = [(1.0, 1.0, 7.0), (4.0, 0.22, 16.0), (9.9, 0.05, 30.0)]


def _render(notes, total, partials_default, echo=(0.19, 0.32), amp=0.5):
    buf = [0.0] * int(SR * total)
    for n in notes:
        t0, fr, dur = n[0], n[1], n[2]
        g = n[3] if len(n) > 3 else 1.0
        parts = n[4] if len(n) > 4 else partials_default
        i0 = int(t0 * SR); cnt = int(min(dur, total - t0) * SR)
        for i in range(cnt):
            t = i / SR
            atk = 1 - math.exp(-t * 300)
            v = 0.0
            for r, a, dec in parts:
                v += a * math.exp(-t * dec) * math.sin(2 * math.pi * fr * r * t)
            if i0 + i < len(buf): buf[i0 + i] += v * atk * g
    d = int(echo[0] * SR)
    for k in (1, 2):
        for i in range(len(buf) - 1, d * k - 1, -1):
            buf[i] += buf[i - d * k] * (echo[1] ** k)
    pk = max(1e-9, max(abs(x) for x in buf))
    fade = int(0.04 * SR)
    for i in range(fade): buf[len(buf) - 1 - i] *= i / fade
    return array.array("h", [int(x / pk * amp * 32767) for x in buf])


def _save(name, pcm):
    p = os.path.join(SOUND_DIR, name + ".wav")
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return p


def ensure_sounds():
    C5, E5, G5, A5, C6, E6, G4, D5 = 523.25, 659.25, 783.99, 880.0, 1046.5, 1318.5, 392.0, 587.33
    if not os.path.exists(os.path.join(SOUND_DIR, "start.wav")):
        _save("start", _render([(0, C5, .6, 1, MARIMBA), (.11, E5, .6, 1, MARIMBA), (.22, G5, .7, 1, MARIMBA),
                                (.38, C6, 1.2, .8, BELL)], 1.9, BELL, amp=.42))
    if not os.path.exists(os.path.join(SOUND_DIR, "done.wav")):
        _save("done", _render([(0, E6, 1.6, .8), (.32, C6, 1.6, .85), (.64, G5, 1.8, .9), (.98, A5, 1.8, .8),
                               (1.5, C5, 3.0, .7), (1.5, E5, 3.0, .6), (1.5, G5, 3.0, .6), (1.5, C6, 3.0, .35)],
                              4.8, BELL, echo=(.23, .38), amp=.45))
    if not os.path.exists(os.path.join(SOUND_DIR, "rest.wav")):
        _save("rest", _render([(0, G4, 1.5, 1), (.28, D5, 1.8, .8)], 2.6, BELL, echo=(.25, .35), amp=.38))
    return {n: os.path.join(SOUND_DIR, n + ".wav") for n in ("start", "done", "rest")}


def play_sound(path):
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        log("sound err", repr(e))


# =====================  熊：逐帧绘制  =====================
FUR, FUR_D, FUR_L, MUZ, NOSE = "#a07c5b", "#8a6a4f", "#5e4534", "#d9b894", "#3d2e22"
BODY = "#8f6f52"
CREAM = "#efe9dc"
BGRGB = tuple(int(BG[i:i + 2], 16) for i in (1, 3, 5))


def render_bear(state, music, t, px, scene="book"):
    """state: focus / rest / done(庆祝)；scene 决定手里的东西；music: 是否在放歌"""
    SS = 3; N = px * SS; f = N / 72.0
    img = Image.new("RGB", (N, N), BGRGB); d = ImageDraw.Draw(img)

    def el(cx, cy, rx, ry, fill=None, outline=None, w=0):
        d.ellipse([(cx - rx) * f, (cy - ry) * f, (cx + rx) * f, (cy + ry) * f], fill=fill, outline=outline,
                  width=max(1, int(w * f)) if outline else 0)

    def ln(pts, fill, w):
        d.line([(x * f, y * f) for x, y in pts], fill=fill, width=max(1, int(w * f)), joint="curve")

    def poly(pts, fill): d.polygon([(x * f, y * f) for x, y in pts], fill=fill)

    def rr(x0, y0, x1, y1, r, fill):
        d.rounded_rectangle([x0 * f, y0 * f, x1 * f, y1 * f], radius=r * f, fill=fill)

    def arc(cx, cy, rx, ry, a0, a1, fill, w):
        d.arc([(cx - rx) * f, (cy - ry) * f, (cx + rx) * f, (cy + ry) * f], a0, a1, fill=fill, width=max(1, int(w * f)))

    def star(cx, cy, r, fill):
        k = r * 0.28
        poly([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r),
              (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill)

    celebrate = state == "done"
    sc = "none" if celebrate else scene
    inst = sc in ("cello", "guitar")

    # ---- 节奏 ----
    if celebrate: b = -abs(math.sin(t * 6.0)) * 3.2
    elif inst: b = math.sin(t * 2 * math.pi * 1.6) * 1.5
    elif music: b = math.sin(t * 2 * math.pi * 1.4) * 2.0
    elif sc == "tea": b = math.sin(t * 1.3) * 0.9
    else: b = math.sin(t * 2.1) * 1.1
    tilt = math.sin(t * 2 * math.pi * 0.7) * 1.8 if (music or inst) else 0.0
    hx = 36 + tilt

    # 喝咖啡的节奏
    sip = 0.0
    if sc == "coffee":
        ph = t % 7.0
        if ph < 2.2: sip = math.sin(ph / 2.2 * math.pi)

    # ---- 身体 / 耳朵 / 头 ----
    el(36, 72 + b * 0.3, 21, 17, fill=BODY)
    poly([(hx - 1.5, 55 + b), (hx, 58 + b), (hx + 1.5, 55 + b)], BODY)
    if celebrate:
        w = math.sin(t * 9.0) * 3.5
        ln([(21, 60), (11, 36 + w)], BODY, 7); ln([(51, 60), (61, 36 - w)], BODY, 7)
        el(11, 36 + w, 4.8, 4.8, fill=FUR); el(61, 36 - w, 4.8, 4.8, fill=FUR)
    for ex in (hx - 16, hx + 16):
        el(ex, 15 + b, 9.5, 9.5, fill=FUR_D); el(ex, 15.5 + b, 5.3, 5.3, fill=FUR_L)
    el(hx, 36 + b, 25, 22, fill=FUR)
    el(hx, 45 + b, 11.5, 8.3, fill=MUZ)
    ty = 59.5 + b * 0.6
    poly([(hx - 10, ty - 4), (hx, ty), (hx - 10, ty + 4)], ACC); poly([(hx + 10, ty - 4), (hx, ty), (hx + 10, ty + 4)], ACC)
    el(hx, ty, 2.3, 2.3, fill="#8c302f")

    # ---- 眼睛 ----
    ey = 33 + b; exs = (hx - 9.5, hx + 9.5)
    blink = (t % 4.3) < 0.13
    mode = "open"; gx = 0.0; gy = 0.0
    if celebrate: mode = "happy"
    elif sc in ("tea", "cello"): mode = "closed"
    elif sc == "guitar": mode = "happy"
    elif sc == "mahjong": gx, gy = -0.8, 1.3
    elif sc == "movie": gx, gy = 1.2, -1.2
    elif sc in ("book", "writing"): gy = 1.3 if (t % 9.0) < 6.5 else -0.6
    elif sc == "laptop": gy = 0.3
    elif sc == "coffee" and sip > 0.35: mode = "closed"
    if blink and mode == "open": mode = "closed"
    if mode == "happy":
        for x in exs: arc(x, ey + 1.5, 3.4, 3.0, 200, 340, "#1a1512", 1.7)
    elif mode == "closed":
        for x in exs: arc(x, ey - 1.0, 3.4, 2.6, 20, 160, "#1a1512", 1.5)
    else:
        for x in exs:
            el(x + gx * 0.6, ey + gy, 2.7, 2.9, fill="#1a1512"); el(x + gx * 0.6 + 0.9, ey + gy - 1.0, 0.8, 0.8, fill="#f3efe6")
    for x in exs: el(x, ey, 7.6, 7.2, outline=GOLD, w=1.35)
    ln([(exs[0] + 7.6, ey - 0.8), (exs[1] - 7.6, ey - 0.8)], GOLD, 1.2)
    if sc == "laptop":                       # 屏幕的光映在镜片上
        fl = 0.6 + 0.4 * math.sin(t * 3.0)
        for x in exs: el(x - 1.8, ey - 1.8, 2.6 * fl, 1.5, fill="#9fc4e8")
    if sc == "mahjong":                      # 一边眉毛挑起来
        ln([(exs[1] - 5, ey - 10.5), (exs[1] + 5, ey - 12.5)], FUR_L, 1.4)

    # ---- 鼻口 ----
    el(hx, 42 + b, 3.1, 2.3, fill=NOSE)
    if celebrate:
        el(hx, 49.2 + b, 3.0, 3.2, fill="#4a1f1f"); el(hx, 50.6 + b, 1.8, 1.4, fill="#c9605f")
        el(hx - 15, 43 + b, 3.2, 2.0, fill="#c98a74"); el(hx + 15, 43 + b, 3.2, 2.0, fill="#c98a74")
    elif sc == "tea":
        el(hx, 49 + b, 1.4, 1.2, fill=NOSE)
    elif sc in ("cello", "guitar"):
        ln([(hx, 44 + b), (hx, 45.5 + b)], NOSE, 1.1); arc(hx, 46 + b, 4.6, 3.2, 15, 165, NOSE, 1.2)
    elif sc == "mahjong":
        ln([(hx, 44 + b), (hx, 45.5 + b)], NOSE, 1.1); arc(hx + 1.5, 46 + b, 3.6, 2.6, 20, 150, NOSE, 1.2)
    elif sc == "movie":
        ln([(hx, 44 + b), (hx, 46 + b)], NOSE, 1.1); el(hx, 48.8 + b, 1.7, 1.0 + abs(math.sin(t * 8)) * 0.9, fill="#4a1f1f")
    else:
        ln([(hx, 44 + b), (hx, 46 + b)], NOSE, 1.1)
        arc(hx - 2.4, 46 + b, 2.4, 2.0, 10, 150, NOSE, 1.1); arc(hx + 2.4, 46 + b, 2.4, 2.0, 30, 170, NOSE, 1.1)

    # ================= 场景道具 =================
    if sc == "book":
        by = 62 + b * 0.5
        poly([(18, by + 1), (36, by - 1.5), (54, by + 1), (54, by + 11), (36, by + 8.5), (18, by + 11)], "#e8dfcf")
        ln([(36, by - 1.5), (36, by + 8.5)], "#b8a98c", 1.0)
        for k in range(3):
            ln([(21, by + 3.5 + k * 2.2), (33, by + 2.2 + k * 2.2)], "#b8a98c", 0.7)
            ln([(39, by + 2.2 + k * 2.2), (51, by + 3.5 + k * 2.2)], "#b8a98c", 0.7)
        if (t % 6.0) < 0.45:
            p = (t % 6.0) / 0.45
            xx = 36 + 16 * math.cos(p * math.pi)
            poly([(36, by - 1.5), (xx, by - 4 - 3 * math.sin(p * math.pi)), (xx, by + 6), (36, by + 8.5)], "#f4ecdc")
        el(17, by + 6, 4.4, 4.4, fill=FUR); el(55, by + 6, 4.4, 4.4, fill=FUR)

    elif sc == "laptop":
        ly = 61 + b * 0.4
        rr(20, ly, 52, ly + 8.5, 1.8, "#3a3744")
        el(36, ly + 4.2, 2.0, 2.0, fill="#c9a94a")
        rr(15, ly + 8.5, 57, ly + 11, 1.0, "#55505f")
        for k, x in enumerate((25, 47)):
            py = ly + 8.0 - abs(math.sin(t * 9.0 + k * math.pi)) * 1.8
            el(x, py, 4.3, 3.4, fill=FUR)

    elif sc == "coffee":
        mcy = 64.5 + b * 0.5 - sip * 13.5
        rr(30, mcy - 6, 42, mcy + 6, 2.2, CREAM)
        el(36, mcy - 6, 6, 1.5, fill="#6b4423")
        arc(42, mcy, 3.4, 3.4, 270, 90, CREAM, 1.6)
        el(29.2, mcy + 1, 3.5, 3.5, fill=FUR); el(44.2, mcy + 1.5, 3.5, 3.5, fill=FUR)
        if sip < 0.1:
            for k in range(2):
                pts = [(33 + k * 6 + math.sin(t * 2.5 + k * 1.7 + j * 1.1) * 1.2, mcy - 8 - j * 3) for j in range(4)]
                ln(pts, "#6d6877", 0.9)

    elif sc == "writing":
        py0 = 62 + b * 0.4
        rr(19, py0, 53, py0 + 12, 1.0, "#efe8d8")
        for k in range(2): ln([(23, py0 + 4 + k * 3.5), (49, py0 + 4 + k * 3.5)], "#d5ccb8", 0.6)
        prog = (t % 4.0) / 4.0
        px_ = 24 + prog * 24
        pts = [(24 + i * 1.2, py0 + 8 + (0.8 if i % 2 else -0.8)) for i in range(int((px_ - 24) / 1.2) + 1)]
        if len(pts) > 1: ln(pts, "#4a4458", 0.8)
        yy = py0 + 8 + (0.8 if int(px_ * 1.0) % 2 else -0.8)
        ln([(px_, yy), (px_ + 6, yy - 11)], GOLD, 1.8)
        el(px_ + 4.5, yy - 7, 3.6, 3.6, fill=FUR)
        el(20, py0 + 8, 3.4, 3.4, fill=FUR)

    elif sc == "tea":
        cy = 62 + b * 0.5
        el(24, cy + 6, 4.6, 4.6, fill=FUR)
        poly([(41, cy), (57, cy), (55, cy + 12), (43, cy + 12)], CREAM)
        arc(57.5, cy + 5.5, 3.6, 3.6, 270, 90, CREAM, 1.6)
        el(49, cy + 0.6, 7.6, 1.5, fill="#b07a4a")
        for k, off in enumerate((0.0, 1.7)):
            pts = [(46 + k * 6 + math.sin(t * 2.5 + off + j * 1.1) * 1.3, cy - 2 - j * 3) for j in range(4)]
            ln(pts, "#6d6877", 0.9)
        el(60, cy + 6, 4.4, 4.4, fill=FUR)

    elif sc == "cello":
        el(46, 66 + b * 0.3, 14, 10, fill="#a5622f"); el(46, 66 + b * 0.3, 8, 6, fill="#b87238")
        ln([(42, 62), (42, 70)], "#4a3322", 0.8); ln([(51, 62), (51, 70)], "#4a3322", 0.8)
        ln([(55, 61), (65.5, 38)], "#4a3322", 2.4); el(66, 36, 2.0, 2.0, fill="#4a3322")
        sx = math.sin(t * 2.4) * 7.0
        ln([(14 + sx, 71), (52 + sx, 59)], "#e0d3b4", 1.0)
        el(16 + sx, 70.5, 3.8, 3.8, fill=FUR)
        el(60 + math.sin(t * 7) * 0.6, 44, 3.6, 3.6, fill=FUR)

    elif sc == "guitar":
        el(24, 67 + b * 0.3, 12.5, 8.5, fill=ACC); el(24, 67 + b * 0.3, 5.5, 3.6, fill="#2c2733")
        ln([(20, 63), (20, 71)], "#d9d2c5", 1.0); ln([(27, 63), (27, 71)], "#d9d2c5", 1.0)
        ln([(34, 64), (66, 50.5)], "#4a3322", 2.4); rr(64.5, 46.5, 70, 52, 1.0, "#2c2733")
        sy = 66 + math.sin(t * 14.0) * 2.2
        el(23, sy, 3.9, 3.9, fill=FUR)
        el(50, 56.5, 3.5, 3.5, fill=FUR)
        for k in range(2):
            a = ((t * 1.6 + k * 0.5) % 1.0)
            arc(10, 64, 3 + a * 5, 3 + a * 5, 150, 210, GOLD, 0.9)

    elif sc == "mahjong":
        base_y = 62.5 + b * 0.3
        marks = ["g", "r", "b", "g", "r"]
        kk = int(t / 4.0) % 5; q = math.sin((t % 4.0) / 4.0 * math.pi)
        for i in range(5):
            x = 13 + i * 9.0; lift = q * 8 if i == kk else 0.0; y = base_y - lift
            rr(x, y, x + 7.6, y + 9.5, 1.4, CREAM); rr(x, y + 6.6, x + 7.6, y + 9.5, 1.2, "#2e8b57")
            m = marks[i]
            if m == "g": ln([(x + 3.8, y + 1.4), (x + 3.8, y + 5.6)], "#2e8b57", 1.5)
            elif m == "r": el(x + 3.8, y + 3.4, 1.6, 1.6, fill=ACC)
            else: el(x + 3.8, y + 3.4, 1.9, 1.9, outline="#3b6ea5", w=0.9)
            if i == kk: el(x + 3.8, y - 1.2, 3.3, 3.3, fill=FUR)

    elif sc == "movie":
        for cx_, cy_ in ((28, 58.5), (33, 57), (38, 58), (43, 58.5), (31, 56), (40, 56.5)):
            el(cx_, cy_ + b * 0.3, 2.4, 2.4, fill="#f4e3a1")
        for k in range(6):
            x0t = 25 + k * 22 / 6; x1t = 25 + (k + 1) * 22 / 6
            x0b = 28 + k * 16 / 6; x1b = 28 + (k + 1) * 16 / 6
            poly([(x0t, 60 + b * 0.3), (x1t, 60 + b * 0.3), (x1b, 72), (x0b, 72)], ACC if k % 2 == 0 else CREAM)
        el(24.5, 64, 3.6, 3.6, fill=FUR)
        p = t % 5.0
        if p < 1.4:
            qq = math.sin(p / 1.4 * math.pi)
            ppx = 47 - (47 - (hx + 3)) * qq; ppy = 64 - (64 - 48) * qq
            el(ppx, ppy, 3.6, 3.6, fill=FUR)
            if qq > 0.2: el(ppx - 1, ppy - 3, 1.7, 1.7, fill="#f4e3a1")
        else:
            el(47, 64, 3.6, 3.6, fill=FUR)

    # ---- 耳机（放歌时；拉琴/弹吉他时不戴）----
    if music and not inst and not celebrate:
        arc(hx, 36 + b, 27.5, 26.5, 188, 352, "#2c2733", 3.4)
        for sx_ in (-1, 1):
            cx = hx + sx_ * 26.5
            d.rounded_rectangle([(cx - 4.3) * f, (31 + b) * f, (cx + 4.3) * f, (47 + b) * f], radius=3.5 * f, fill=ACC)
            d.rounded_rectangle([(cx - 2.2) * f, (33 + b) * f, (cx + 2.2) * f, (45 + b) * f], radius=2.0 * f, fill="#c0504d")
    if music or inst:
        for k in range(2):
            p = ((t * 0.55 + k * 0.5) % 1.0)
            nx = 58 + math.sin(p * 6.0 + k) * 3.5 - k * 46; ny = 22 - p * 20 + k * 6
            if 0 < nx < 72 and ny > -2:
                el(nx, ny + 4, 2.1, 1.6, fill=GOLD); ln([(nx + 1.9, ny + 3.6), (nx + 1.9, ny - 3)], GOLD, 0.9)
                ln([(nx + 1.9, ny - 3), (nx + 4.2, ny - 1.4)], GOLD, 0.9)

    if celebrate:
        for k, (sx_, sy_, ph) in enumerate(((8, 12, 0.0), (64, 10, 1.7), (66, 52, 3.1), (6, 54, 4.4))):
            a = 0.5 + 0.5 * math.sin(t * 6 + ph)
            star(sx_, sy_, 1.5 + 3.2 * a, GOLD)
    if sc == "tea":
        for k in range(3):
            p = ((t * 0.28 + k / 3.0) % 1.0)
            zx = 50 + p * 10; zy = 24 - p * 13; sz = 1.6 + p * 2.0
            ln([(zx - sz, zy - sz), (zx + sz, zy - sz), (zx - sz, zy + sz), (zx + sz, zy + sz)], "#9a95aa", 0.9)
    return img.resize((px, px), Image.LANCZOS)


# =====================  播放器 / 取曲（只放纯音乐）  =====================
class Player:
    def __init__(self):
        self.mci = ctypes.windll.winmm.mciSendStringW
        self.open_ = False; self.paused = False; self.volume = 600

    def _s(self, cmd):
        buf = ctypes.create_unicode_buffer(256)
        err = self.mci(cmd, buf, 255, 0)
        return err, buf.value

    def play(self, path):
        self.stop()
        err, _ = self._s(f'open "{path}" type mpegvideo alias pm')
        if err: log("mci open err", err); return False
        self._s(f"setaudio pm volume to {self.volume}")
        err, _ = self._s("play pm")
        self.open_ = not err; self.paused = False
        return self.open_

    def stop(self):
        if self.open_:
            self._s("stop pm"); self._s("close pm")
        self.open_ = False; self.paused = False

    def toggle(self):
        if not self.open_: return
        if self.paused: self._s("resume pm"); self.paused = False
        else: self._s("pause pm"); self.paused = True

    def ended(self):
        if not self.open_ or self.paused: return False
        _, mode = self._s("status pm mode")
        return mode == "stopped"

    def length_ms(self):
        _, v = self._s("status pm length")
        return int(v) if v.isdigit() else 0


H_UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
META = re.compile(r"(作曲|作词|编曲|制作|演奏|纯音乐|请欣赏|Music|Composer|Lyrics|Arranged|Produced|混音|母带|录音|监制|出品|策划|OP|SP)", re.I)


def http(u, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(u, headers=H_UA), timeout=timeout)


def has_lyrics(sid):
    """网易云歌词接口：nolyric=纯音乐；否则去掉作曲/编曲等署名行，剩 >=5 行正文就算有人声"""
    d = json.load(http(f"https://music.163.com/api/song/lyric?id={sid}&lv=1&kv=1&tv=-1"))
    if d.get("nolyric"): return False
    lrc = (d.get("lrc") or {}).get("lyric", "") or ""
    n = 0
    for line in lrc.splitlines():
        t = re.sub(r"\[[^\]]*\]", "", line).strip()
        if len(t) < 2: continue
        if "纯音乐" in t: return False
        if META.search(t) and re.search(r"[:：]", t): continue
        n += 1
    return n >= 5


class Music:
    def __init__(self, ui_cb, run_main):
        self.player = Player(); self.ui_cb = ui_cb; self.run_main = run_main
        self.pl = random.choice(PLAYLISTS); self.queue = []; self.cur = ""
        self.busy = False; self.rejected = set()

    def _fetch_ids(self):
        self.pl = random.choice(PLAYLISTS)           # 每攒一批曲子换一个歌单，听着不腻
        d = json.load(http(f"https://music.163.com/api/v6/playlist/detail?id={self.pl[1]}&n=1"))
        ids = [t["id"] for t in d["playlist"]["trackIds"]]
        random.shuffle(ids); return ids[:30]

    def _download(self, sid):
        path = os.path.join(MUSIC_DIR, f"{sid}.mp3")
        if os.path.exists(path) and os.path.getsize(path) > 500000: return path
        r = http(f"https://music.163.com/song/media/outer/url?id={sid}.mp3", 40)
        if "audio" not in r.headers.get("Content-Type", ""): return None
        data = r.read()
        if len(data) < 500000: return None
        with open(path, "wb") as f: f.write(data)
        return path

    def _name(self, sid):
        try:
            s = json.load(http(f"https://music.163.com/api/song/detail?ids=[{sid}]"))["songs"][0]
            return f"{s['name']} - {s['artists'][0]['name']}"
        except Exception: return str(sid)

    def next(self):
        if self.busy: return
        self.busy = True
        self.ui_cb(f"♫ 找歌中…《{self.pl[0]}》")
        def work():
            try:
                for _ in range(25):
                    if not self.queue: self.queue = self._fetch_ids()
                    sid = self.queue.pop()
                    if sid in self.rejected: continue
                    try:
                        if has_lyrics(sid):
                            self.rejected.add(sid); log("skip vocal", sid); continue
                    except Exception as e:
                        log("lyric check err", sid, repr(e))     # 歌词接口抽风时放行，不卡住
                    p = self._download(sid)
                    if not p: continue
                    name = self._name(sid)
                    done = threading.Event(); ok = []
                    def play_main():
                        try:
                            if self.player.play(p):
                                if self.player.length_ms() < 45000:
                                    self.player.stop()
                                else:
                                    ok.append(1); self.cur = name; self.ui_cb("♫ " + name)
                        finally:
                            done.set()
                    self.run_main(play_main); done.wait(15)
                    if ok: return
                self.ui_cb("♫ 没找到能放的歌，再点一下")
            except Exception as e:
                log("music err", repr(e)); self.ui_cb("♫ 网络不通，歌没取到")
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()


def decorate(win):
    u = ctypes.windll.user32
    try:
        win.update_idletasks()
        hwnd = u.GetAncestor(win.winfo_id(), 2)
        ex = u.GetWindowLongW(hwnd, -20)
        u.SetWindowLongW(hwnd, -20, (ex | 0x80 | 0x08000000) & ~0x40000)
        dwm = ctypes.windll.dwmapi
        v = ctypes.c_int(2); dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(v), 4)
        c = ctypes.c_uint(0xFFFFFFFE); dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(c), 4)
        return hwnd
    except Exception as e:
        log("decorate err", repr(e)); return None


# =====================  主界面（整块 Canvas）  =====================
class App:
    def __init__(self, start, silent=False, durs=(FOCUS, REST, LONG)):
        single_instance()
        self.durs = durs; self.silent = silent
        self.mode = "focus"; self.long = False
        self.done_n = 0                      # 本轮循环已完成的番茄数(累计，%4 决定长休息)
        self.today = load_today()
        self.elapsed = max(0.0, time.time() - start)
        if self.elapsed >= durs[0]: self.elapsed = 0.0
        self.total = durs[0]; self.running = True; self._last = time.time()
        self.celebrate_until = 0.0; self.celeb_msg_pending = False
        self.scene_off = random.randrange(10); self.phase_log = []
        self.sounds = ensure_sounds()
        self.hidden_root = tk.Tk(); self.hidden_root.withdraw()
        r = self.root = tk.Toplevel(self.hidden_root)
        r.overrideredirect(True); r.attributes("-topmost", True); r.attributes("-alpha", ALPHA_FULL)
        r.resizable(False, False)
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        try: self.s = ctypes.windll.user32.GetDpiForSystem() / 96
        except Exception: self.s = 1.0
        self.pw, self.ph = int(W * self.s), int(H * self.s)
        r.geometry(f"{self.pw}x{self.ph}+{sw - self.pw - 24}+{sh - self.ph - 100}")
        r.configure(bg=BG)
        self.cv = tk.Canvas(r, width=self.pw, height=self.ph, bg=BG, highlightthickness=0, bd=0)
        self.cv.pack()
        self.music = Music(self.set_song, lambda fn: self.root.after(0, fn))
        self.buttons = {}
        self.expanded = True; self.pin_until = time.time() + PIN_SECONDS
        self._in_count = 0; self._out_since = None
        self.cur_alpha = self.target_alpha = ALPHA_FULL
        self.build()
        self.refresh_labels(first=True)
        self.hwnd = decorate(r)
        self.update_anchor()
        self.tick(); self.anim(); self.watch_music()
        if AUTO_COLLAPSE: self.hover_loop(); self.fade_loop()
        if not silent and time.time() - start < 5: self.root.after(400, lambda: self.sound("start"))

    def S(self, v): return v * self.s
    def font(self, px, bold=False, mono=False):
        return ("Consolas" if mono else "Microsoft YaHei UI", -int(round(px * self.s)), "bold" if bold else "normal")

    def sound(self, name):
        if not self.silent: play_sound(self.sounds[name])

    def add_button(self, name, x0, x1, y0, y1, text, color, cmd):
        S = self.S; h = y1 - y0
        self.cv.create_line(S(x0 + h / 2), S((y0 + y1) / 2), S(x1 - h / 2), S((y0 + y1) / 2), width=S(h),
                            capstyle="round", fill=PILL, tags=(name, name + "_bg"))
        t = self.cv.create_text(S((x0 + x1) / 2), S((y0 + y1) / 2), text=text, fill=color,
                                font=self.font(12), tags=(name, name + "_tx"))
        self.buttons[name] = dict(cmd=cmd, box=(S(x0), S(y0), S(x1), S(y1)), text=t)
        self.cv.tag_bind(name, "<Enter>", lambda e, n=name: self.cv.itemconfig(n + "_bg", fill=PILL_HOV))
        self.cv.tag_bind(name, "<Leave>", lambda e, n=name: self.cv.itemconfig(n + "_bg", fill=PILL))

    def set_btn(self, name, text=None, color=None):
        b = self.buttons[name]
        if text is not None: self.cv.itemconfig(b["text"], text=text)
        if color is not None: self.cv.itemconfig(b["text"], fill=color)

    def build(self):
        S = self.S; cv = self.cv
        self.bear_px = int(S(68))
        self.bear_item = cv.create_image(S(48), S(46), anchor="center")
        self.lab_round = cv.create_text(S(96), S(20), text="", anchor="w", fill=GOLD, font=self.font(12))
        self.lab_time = cv.create_text(S(95), S(52), text="25:00", anchor="w", fill=FG, font=self.font(34, True, True))
        cv.create_text(S(286), S(14), text="✕", fill=DIM, font=self.font(12), tags=("x",))
        cv.tag_bind("x", "<Enter>", lambda e: cv.itemconfig("x", fill=ACC)); cv.tag_bind("x", "<Leave>", lambda e: cv.itemconfig("x", fill=DIM))
        self.lab_today = cv.create_text(S(286), S(34), text="", anchor="e", fill=DIM, font=self.font(10))
        self.dots = []
        for i in range(SET):
            x = 241 + i * 12
            self.dots.append(cv.create_oval(S(x - 4), S(56), S(x + 4), S(64), fill=TRACK, outline=""))
        self.pb_x0, self.pb_x1, self.pb_y = S(18), S(282), S(94)
        self.pb_track = cv.create_line(self.pb_x0, self.pb_y, self.pb_x1, self.pb_y, width=S(6), capstyle="round", fill=TRACK)
        self.pb_fill = cv.create_line(self.pb_x0, self.pb_y, self.pb_x0 + 0.1, self.pb_y, width=S(6), capstyle="round", fill=GOLD)
        self.lab_msg = cv.create_text(S(18), S(113), text="", anchor="w", fill=DIM, font=self.font(12))
        self.lab_song = cv.create_text(S(18), S(131), text="♫ 点播放，随机来点纯音乐", anchor="w", fill=GOLD, font=self.font(11))
        self.add_button("play", 14, 78, 146, 170, "▶ 音乐", GOLD, self.on_play)
        self.add_button("next", 82, 112, 146, 170, "⏭", GOLD, self.on_next)
        self.add_button("pause", 116, 190, 146, 170, "⏱ 停表", DIM, self.on_pause)
        self.add_button("act", 194, 286, 146, 170, "提前休息", BTN_RED, self.on_act)
        self._press = None
        cv.bind("<Button-1>", self.press); cv.bind("<B1-Motion>", self.drag); cv.bind("<ButtonRelease-1>", self.release)

    def press(self, e):
        self._press = (e.x_root, e.y_root); self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def drag(self, e): self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def release(self, e):
        if not self._press: return
        moved = abs(e.x_root - self._press[0]) + abs(e.y_root - self._press[1]); self._press = None
        if moved > 5: self.update_anchor(); return        # 拖动结束：重新判断靠哪个角收放
        if not self.expanded: return
        if math.hypot(e.x - self.S(286), e.y - self.S(14)) < self.S(12): self.quit(); return
        for n, b in self.buttons.items():
            x0, y0, x1, y1 = b["box"]
            if x0 <= e.x <= x1 and y0 <= e.y <= y1: b["cmd"](); return

    # ---- 收起 / 展开 ----
    def apply_layout(self, expanded):
        """切换两套布局：展开=完整界面；收起=小熊+倒计时+细进度条，其余全部隐藏"""
        S = self.S; cv = self.cv
        if expanded:
            w, h = self.pw, self.ph
            self.bear_px = int(S(68)); bear_xy = (S(48), S(46)); time_xy = (S(95), S(52)); tfont = self.font(34, True, True)
            self.pb_x0, self.pb_x1, self.pb_y, pbw = S(18), S(282), S(94), S(6)
            state = "normal"
        else:
            w, h = int(CW * self.s), int(CH * self.s)
            self.bear_px = int(S(44)); bear_xy = (S(30), S(31)); time_xy = (S(58), S(30)); tfont = self.font(26, True, True)
            self.pb_x0, self.pb_x1, self.pb_y, pbw = S(12), S(CW - 12), S(CH - 8), S(4)
            state = "hidden"
        for t in ("x", "play", "next", "pause", "act", self.lab_round, self.lab_today, self.lab_msg, self.lab_song, *self.dots):
            cv.itemconfigure(t, state=state)
        cv.coords(self.bear_item, *bear_xy); cv.coords(self.lab_time, *time_xy); cv.itemconfigure(self.lab_time, font=tfont)
        cv.coords(self.pb_track, self.pb_x0, self.pb_y, self.pb_x1, self.pb_y)
        cv.itemconfigure(self.pb_track, width=pbw); cv.itemconfigure(self.pb_fill, width=pbw)
        cv.config(width=w, height=h)
        return w, h

    def update_anchor(self):
        """窗口中心在屏幕哪一半，就固定哪一边的边缘：放在右下角就向左上展开，放在左上角就向右下展开"""
        r = self.root; r.update_idletasks()
        cx = r.winfo_x() + r.winfo_width() / 2; cy = r.winfo_y() + r.winfo_height() / 2
        self.anchor = (cx > r.winfo_screenwidth() / 2, cy > r.winfo_screenheight() / 2)

    def set_expanded(self, flag):
        if flag == self.expanded: return
        r = self.root; r.update_idletasks()
        x, y, ow, oh = r.winfo_x(), r.winfo_y(), r.winfo_width(), r.winfo_height()
        self.expanded = flag
        nw, nh = self.apply_layout(flag)
        right, bottom = self.anchor
        nx = x + ow - nw if right else x
        ny = y + oh - nh if bottom else y
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        nx = max(0, min(nx, sw - nw)); ny = max(0, min(ny, sh - nh))
        r.geometry(f"{nw}x{nh}+{nx}+{ny}")
        self.target_alpha = ALPHA_FULL if flag else ALPHA_DIM
        self.render_progress()

    def cursor_pos(self):
        pt = wt.POINT(); ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)); return pt.x, pt.y

    def cursor_inside(self, margin=0):
        r = self.root; x, y = self.cursor_pos()
        return (r.winfo_x() - margin <= x <= r.winfo_x() + r.winfo_width() + margin and
                r.winfo_y() - margin <= y <= r.winfo_y() + r.winfo_height() + margin)

    def hover_loop(self):
        """每 80ms 看一眼鼠标：进来停留片刻就展开；离开一会儿才收起，拖动中和刚换阶段时不收"""
        try:
            now = time.time()
            inside = self.cursor_inside(0 if not self.expanded else 10)
            pinned = now < self.pin_until or self._press is not None
            if inside:
                self._out_since = None; self._in_count += 1
                if not self.expanded and self._in_count >= 2: self.set_expanded(True)
            else:
                self._in_count = 0
                if self.expanded and not pinned:
                    if self._out_since is None: self._out_since = now
                    elif now - self._out_since >= COLLAPSE_DELAY: self.set_expanded(False)
                else:
                    self._out_since = None
        except Exception as e:
            log("hover err", repr(e))
        self.root.after(80, self.hover_loop)

    def fade_loop(self):
        try:
            d = self.target_alpha - self.cur_alpha
            if abs(d) > 0.004:
                self.cur_alpha += d * 0.35 if abs(d) > 0.02 else d
                self.root.attributes("-alpha", self.cur_alpha)
        except Exception as e:
            log("fade err", repr(e))
        self.root.after(40, self.fade_loop)

    # ---- 音乐 ----
    def fit_text(self, text, font, maxw):
        """按真实像素宽度截断，放不下才加省略号"""
        import tkinter.font as tkfont
        f = tkfont.Font(font=font)
        if f.measure(text) <= maxw: return text
        while len(text) > 1 and f.measure(text + "…") > maxw: text = text[:-1]
        return text + "…"

    def set_song(self, text):
        def f():
            self.cv.itemconfig(self.lab_song, text=self.fit_text(text, self.font(11), self.S(264)))
            p = self.music.player
            self.set_btn("play", "⏸ 音乐" if (p.open_ and not p.paused) else "▶ 音乐")
        self.root.after(0, f)

    def on_play(self):
        p = self.music.player
        if p.open_:
            p.toggle(); self.set_btn("play", "▶ 音乐" if p.paused else "⏸ 音乐")
        else:
            self.music.next()

    def on_next(self): self.music.next()

    # ---- 计时：全自动循环 ----
    def phase_total(self, mode, long):
        return self.durs[0] if mode == "focus" else (self.durs[2] if long else self.durs[1])

    def refresh_labels(self, first=False):
        c = self.cv
        if self.mode == "focus":
            k = self.done_n % SET + 1
            c.itemconfig(self.lab_round, text=f"小熊陪你 · 专注 {k}/{SET}", fill=GOLD)
            c.itemconfig(self.pb_fill, fill=GOLD)
            self.set_btn("act", "提前休息", BTN_RED)
        else:
            c.itemconfig(self.lab_round, text="长休息 · 好好歇一歇" if self.long else "休息中", fill=TEAL)
            c.itemconfig(self.pb_fill, fill=TEAL)
            self.set_btn("act", "跳过休息", BTN_RED)
        filled = SET if (self.mode == "rest" and self.long) else self.done_n % SET
        for i, o in enumerate(self.dots): c.itemconfig(o, fill=GOLD if i < filled else TRACK)
        c.itemconfig(self.lab_today, text=f"今日 {self.today} 个")
        c.itemconfig(self.lab_time, fill=FG)
        if first: c.itemconfig(self.lab_msg, text=say("focus"), fill=DIM)

    def start_phase(self, mode, long=False, natural=False):
        prev = self.mode
        self.mode = mode; self.long = long; self.elapsed = 0.0; self._last = time.time()
        self.total = self.phase_total(mode, long); self.running = True
        self.scene_off = random.randrange(10)
        self.set_btn("pause", "⏱ 停表", DIM)
        self.refresh_labels()
        if natural:                                          # 自然走完：先庆祝几秒，再说正常的话
            self.celebrate_until = time.time() + (6.0 if prev == "focus" else 4.0); self.celeb_msg_pending = True
            msg = say("done" if prev == "focus" else "back")
            self.cv.itemconfig(self.lab_msg, text=msg, fill=ACC)
            self.pin_until = time.time() + PIN_SECONDS           # 换阶段时自动展开几秒，免得错过提示
            if AUTO_COLLAPSE: self.set_expanded(True)
        else:
            self.celebrate_until = 0.0; self.celeb_msg_pending = False
            self.cv.itemconfig(self.lab_msg, text=say("focus" if mode == "focus" else ("long" if long else "rest")), fill=DIM)
        self.sound("start" if mode == "focus" else ("done" if natural else "rest"))
        self.phase_log.append((mode, long, natural))

    def advance(self, natural):
        if self.mode == "focus":
            long = False
            if natural:
                self.today += 1; save_today(self.today); self.done_n += 1
                long = self.done_n % SET == 0
            self.start_phase("rest", long=long, natural=natural)
        else:
            self.start_phase("focus", natural=natural)

    def rest_cat(self):
        return "focus" if self.mode == "focus" else ("long" if self.long else "rest")

    def on_act(self): self.advance(natural=False)

    def on_pause(self):
        self.running = not self.running; self._last = time.time()
        self.set_btn("pause", "⏱ 停表" if self.running else "⏱ 继续", DIM if self.running else GOLD)
        self.cv.itemconfig(self.lab_time, fill=FG if self.running else GOLD)   # 收起时也能看出暂停了
        if not self.running:
            self.cv.itemconfig(self.lab_msg, text=say("pause"), fill=GOLD)
        else:
            self.cv.itemconfig(self.lab_msg, text=say(self.rest_cat()), fill=DIM)

    def render_progress(self):
        left = max(0, int(self.total - self.elapsed + 0.999))
        frac = min(1.0, self.elapsed / self.total)
        self.cv.coords(self.pb_fill, self.pb_x0, self.pb_y, self.pb_x0 + max(0.1, (self.pb_x1 - self.pb_x0) * frac), self.pb_y)
        self.cv.itemconfig(self.lab_time, text=f"{left // 60:02d}:{left % 60:02d}")
        return left

    def tick(self):
        now = time.time(); dt = now - self._last; self._last = now
        if self.running: self.elapsed += dt
        left = self.render_progress()
        if self.celeb_msg_pending and now >= self.celebrate_until:
            self.celeb_msg_pending = False
            self.cv.itemconfig(self.lab_msg, text=say(self.rest_cat()), fill=DIM)
        if left <= 0 and self.running: self.advance(natural=True)
        self.root.after(250, self.tick)

    # ---- 熊动画 ----
    def scene(self):
        if self.mode == "focus": lst, per = FOCUS_SCENES, 150.0
        else: lst, per = REST_SCENES, (100.0 if self.long else 60.0)
        return lst[(self.scene_off + int(self.elapsed // per)) % len(lst)]

    def anim(self):
        try:
            p = self.music.player
            st = "done" if time.time() < self.celebrate_until else self.mode
            img = render_bear(st, p.open_ and not p.paused, time.time(), self.bear_px, self.scene())
            self._tk = ImageTk.PhotoImage(img); self.cv.itemconfig(self.bear_item, image=self._tk)
        except Exception as e:
            log("anim err", repr(e))
        self.root.after(90, self.anim)

    def watch_music(self):
        if self.music.player.ended() and not self.music.busy: self.music.next()
        self.root.after(2000, self.watch_music)

    def quit(self):
        self.music.player.stop()
        try: os.remove(PID_FILE)
        except Exception: pass
        os._exit(0)

    def run(self): self.hidden_root.mainloop()


if __name__ == "__main__":
    a1 = sys.argv[1] if len(sys.argv) > 1 else ""
    start = float(a1) if a1.replace(".", "", 1).isdigit() else time.time()
    log("start v9", start)
    App(start).run()
