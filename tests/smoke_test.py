# -*- coding: utf-8 -*-
"""Cross-platform smoke test: start the window, run a short full cycle, click the buttons,
collapse/expand, and (on macOS) exercise the afplay-based player. Prints every step."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bear_pomodoro as b

def say(*a): print(*a, flush=True)
fails = []
def check(name, ok):
    say(("PASS " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

say("platform", sys.platform, "player", b.Player.__name__)
a = b.App(time.time(), silent=True, durs=(3, 2, 2))
r = a.root

def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        a.hidden_root.update(); time.sleep(0.02)

pump(1.0)
say("expanded size", r.winfo_width(), r.winfo_height(), "scale", a.s)
check("window has size", r.winfo_width() > 100 and r.winfo_height() > 100)
check("cursor readable", len(a.cursor_pos()) == 2)
try:
    from PIL import ImageGrab
    ImageGrab.grab().save("smoke_screen.png"); say("screenshot saved")
except Exception as e:
    say("screenshot skipped:", repr(e))

pump(4.5)
say("phases", a.phase_log)
check("auto cycle focus->rest->focus", [p[0] for p in a.phase_log[:2]] == ["rest", "focus"])
a.on_pause(); check("pause", a.running is False)
a.on_pause(); check("resume", a.running is True)
a.on_act(); check("early rest", a.mode in ("rest", "focus"))
a.set_expanded(False); pump(0.3); cw = r.winfo_width()
a.set_expanded(True); pump(0.3); ew = r.winfo_width()
say("collapsed/expanded width", cw, ew)
check("collapse smaller than expand", cw < ew)
check("bear frame renders", b.render_bear("focus", False, time.time(), 68, "book").size == (68, 68))

if b.IS_MAC:
    p = b.Player()
    ok = p.play(a.sounds["done"])
    check("afplay starts", ok and p.proc is not None)
    say("length_ms", p.length_ms())
    check("length read", p.length_ms() > 1000)
    p.toggle(); check("pause via SIGSTOP", p.paused is True)
    p.toggle(); check("resume via SIGCONT", p.paused is False)
    p.stop(); check("stop", p.open_ is False)
    b.play_sound(a.sounds["start"]); say("play_sound called")

say("RESULT", "FAILED: " + ", ".join(fails) if fails else "ALL PASSED")
os._exit(1 if fails else 0)
