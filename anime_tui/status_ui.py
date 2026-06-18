import curses
import time
import json
import os
import signal
from pathlib import Path

def get_progress_bar(percent_str: str, width: int = 40) -> str:
    try:
        pct = float(percent_str.replace('%', ''))
    except:
        pct = 0.0
    filled = int(width * (pct / 100))
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {percent_str}"

def draw_ui(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    
    # Init colors
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    
    status_file = Path(os.path.expanduser("~/.cache/anime-tui/status.json"))
    
    while True:
        stdscr.erase()
        
        try:
            h, w = stdscr.getmaxyx()
        except:
            h, w = 24, 80
            
        header = "=== Фонові завантаження ==="
        stdscr.addstr(1, max(0, (w - len(header)) // 2), header, curses.color_pair(1) | curses.A_BOLD)
        
        try:
            if status_file.exists():
                data = json.loads(status_file.read_text(encoding="utf-8"))
                active = data.get("active", False)
                
                if active:
                    anime = data.get("anime", "")
                    ep = data.get("episode", "")
                    pct = data.get("percent", "0%")
                    spd = data.get("speed", "")
                    eta = data.get("eta", "")
                    cur = data.get("current", 1)
                    tot = data.get("total", 1)
                    
                    stdscr.addstr(4, 4, f"Завантаження {cur} з {tot}:", curses.A_BOLD)
                    stdscr.addstr(5, 4, f"Тайтл: ", curses.color_pair(1))
                    stdscr.addstr(f"{anime}")
                    stdscr.addstr(6, 4, f"Серія: ", curses.color_pair(1))
                    stdscr.addstr(f"{ep}")
                    
                    bar = get_progress_bar(pct, width=min(50, w - 20))
                    stdscr.addstr(8, 4, bar, curses.color_pair(2))
                    
                    stdscr.addstr(10, 4, f"Швидкість: ", curses.color_pair(3))
                    stdscr.addstr(f"{spd}")
                    stdscr.addstr(10, 30, f"Залишилося: ", curses.color_pair(3))
                    stdscr.addstr(f"{eta}")
                    
                else:
                    stdscr.addstr(6, 4, "Немає активних завантажень.", curses.color_pair(3))
            else:
                stdscr.addstr(6, 4, "Немає активних завантажень.", curses.color_pair(3))
        except Exception as e:
            stdscr.addstr(6, 4, f"Помилка читання статусу: {e}", curses.color_pair(4))
            
        footer = "Натисніть 'q' або 'Esc' для виходу | 'c' - скасувати завантаження"
        stdscr.addstr(h - 2, max(0, w - len(footer) - 2), footer, curses.A_DIM)
        
        stdscr.refresh()
        
        # Check for input
        c = stdscr.getch()
        if c in (ord('q'), ord('Q'), 27): # 27 is Esc
            break
        elif c in (ord('c'), ord('C')):
            try:
                if status_file.exists():
                    data = json.loads(status_file.read_text(encoding="utf-8"))
                    active = data.get("active", False)
                    pid = data.get("pid")
                    if active and pid:
                        try:
                            if os.name == 'nt':
                                import subprocess
                                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            else:
                                # Kill entire process group
                                os.killpg(os.getpgid(pid), signal.SIGTERM)
                        except:
                            pass
                        data["active"] = False
                        data["anime"] = "Завантаження скасовано"
                        data["percent"] = "0%"
                        status_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
            
        time.sleep(0.5)

def main():
    try:
        curses.wrapper(draw_ui)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
