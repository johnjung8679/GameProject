import importlib
import random
import subprocess
import sys
import tkinter as tk
from collections import Counter
from tkinter import messagebox, simpledialog
from urllib.parse import quote

import tkinter.ttk as ttk

try:
    import requests
except ImportError:
    requests = None


CATEGORIES = [
    ("ones", "1의 합"),
    ("twos", "2의 합"),
    ("threes", "3의 합"),
    ("fours", "4의 합"),
    ("fives", "5의 합"),
    ("sixes", "6의 합"),
    ("four_kind", "포카드"),
    ("full_house", "풀하우스"),
    ("small_straight", "스몰 스트레이트"),
    ("large_straight", "라지 스트레이트"),
    ("yacht", "야추"),
    ("chance", "찬스"),
]
CATEGORY_DISPLAY_MAP = {code: display for code, display in CATEGORIES}

WEATHER_THEMES = {
    "sunny": {
        "bg": "#ffe27a",
        "fg": "#2c2100",
        "ability_name": "햇살 찬스",
        "ability_desc": "이번 턴에 원하는 주사위 하나를 6으로 바꿀 수 있습니다.",
        "ability_key": "set_die_to_six",
    },
    "cloudy": {
        "bg": "#d6e4f0",
        "fg": "#1f2a44",
        "ability_name": "바람 찬스",
        "ability_desc": "선택한 주사위 두 개까지 다시 굴립니다.",
        "ability_key": "reroll_selected",
    },
    "rain": {
        "bg": "#9ec5f8",
        "fg": "#132d4b",
        "ability_name": "빗방울 찬스",
        "ability_desc": "이번 점수에 +5점을 추가합니다.",
        "ability_key": "add_five_points",
    },
    "snow": {
        "bg": "#f3f8ff",
        "fg": "#2a2f36",
        "ability_name": "눈꽃 찬스",
        "ability_desc": "선택한 주사위 두 개의 값을 서로 바꿉니다.",
        "ability_key": "swap_dice",
    },
    "storm": {
        "bg": "#494166",
        "fg": "#f1f1f1",
        "ability_name": "번개 찬스",
        "ability_desc": "주사위 전체를 한 번 더 굴립니다 (굴림 횟수 무시).",
        "ability_key": "full_reroll",
    },
}

API_TEST_URL = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude=0&longitude=0&current=temperature_2m"
)

IP_GEOLOCATION_URL = (
    "http://ip-api.com/json/?fields=status,message,city,lat,lon"
)

if requests is not None:
    from requests.exceptions import RequestException
else:
    RequestException = Exception


def ensure_requests(root: tk.Tk | None = None, show_success: bool = True) -> bool:
    global requests, RequestException
    if requests is not None:
        return True

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        requests = importlib.import_module("requests")
        RequestException = requests.exceptions.RequestException
        if show_success and root is not None:
            try:
                messagebox.showinfo(
                    "라이브러리 설치 완료",
                    "'requests' 라이브러리가 자동으로 설치되었습니다.",
                    parent=root,
                )
            except Exception:
                pass
        return True
    except subprocess.CalledProcessError as exc:
        error_text = f"requests 설치 중 오류가 발생했습니다.\n\n{exc}"
    except Exception as exc:
        error_text = f"requests 설치 중 예기치 못한 오류가 발생했습니다.\n\n{exc}"
    else:
        error_text = None

    if root is not None:
        try:
            messagebox.showerror("라이브러리 설치 실패", error_text or "알 수 없는 오류입니다.", parent=root)
        except Exception:
            pass
    else:
        print(error_text or "알 수 없는 오류입니다.", file=sys.stderr)
    return False


class DiceView(tk.Canvas):
    PIP_POSITIONS = {
        1: [(0.5, 0.5)],
        2: [(0.25, 0.25), (0.75, 0.75)],
        3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
        4: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)],
        5: [(0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75), (0.5, 0.5)],
        6: [
            (0.25, 0.25),
            (0.25, 0.5),
            (0.25, 0.75),
            (0.75, 0.25),
            (0.75, 0.5),
            (0.75, 0.75),
        ],
    }

    def __init__(self, master, index: int, command, size: int = 100) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            highlightthickness=0,
            bg=master.cget("bg"),
        )
        self.index = index
        self.command = command
        self.size = size
        self.bind("<Button-1>", self.on_click)

    def on_click(self, _event) -> None:
        if self.command:
            self.command(self.index)

    def render(self, value: int, held: bool, theme_fg: str) -> None:
        self.delete("all")
        size = self.size
        pad = size * 0.08
        outline_color = "#d43f3f" if held else "#202020"
        outline_width = 4 if held else 2
        die_fill = "#fafafa" if not held else "#ffe5b4"

        self.create_rectangle(
            pad,
            pad,
            size - pad,
            size - pad,
            fill=die_fill,
            outline=outline_color,
            width=outline_width,
        )

        if value == 0:
            self.create_text(
                size / 2,
                size / 2,
                text="?",
                font=("Helvetica", int(size * 0.38), "bold"),
                fill=theme_fg,
            )
            return

        radius = size * 0.07
        pip_fill = "#1f1f1f"
        for x_frac, y_frac in self.PIP_POSITIONS.get(value, []):
            x = pad + (size - 2 * pad) * x_frac
            y = pad + (size - 2 * pad) * y_frac
            self.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=pip_fill,
                outline=pip_fill,
            )


def classify_weather(code: int) -> str:
    if code in {0}:
        return "sunny"
    if code in {1, 2, 3, 45, 48}:
        return "cloudy"
    if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "snow"
    if code in {95, 96, 99}:
        return "storm"
    return "cloudy"


def calculate_score(category: str, dice: list[int]) -> int:
    counts = Counter(dice)
    total = sum(dice)
    if category == "ones":
        return dice.count(1)
    if category == "twos":
        return 2 * dice.count(2)
    if category == "threes":
        return 3 * dice.count(3)
    if category == "fours":
        return 4 * dice.count(4)
    if category == "fives":
        return 5 * dice.count(5)
    if category == "sixes":
        return 6 * dice.count(6)
    if category == "four_kind":
        for value, count in counts.items():
            if count >= 4:
                return total
        return 0
    if category == "full_house":
        if sorted(counts.values()) == [2, 3]:
            return 25
        return 0
    if category == "small_straight":
        unique = sorted(set(dice))
        straights = [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]
        for straight in straights:
            if straight.issubset(unique):
                return 30
        return 0
    if category == "large_straight":
        if set(dice) in ({1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}):
            return 40
        return 0
    if category == "yacht":
        if len(counts) == 1:
            return 50
        return 0
    if category == "chance":
        return total
    return 0


class WeatherYachtApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Weather Yacht")
        self.root.geometry("1100x820")
        self.root.minsize(950, 700)
        self.root.resizable(True, True)
        self.is_fullscreen = False
        self.window_geometry = self.root.geometry()
        self.fullscreen_button: tk.Button | None = None
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.root.bind_all("<MouseWheel>", self.handle_mousewheel)

        self.frames: dict[str, tk.Frame] = {}
        self.players: list[dict] = []
        self.player_name_vars: list[tk.StringVar] = []
        self.player_entries: list[tk.Entry] = []

        self.current_theme = WEATHER_THEMES["cloudy"]
        self.weather_context = {
            "city": "Seoul",
            "temperature": None,
            "code": None,
            "condition_key": "cloudy",
            "latitude": None,
            "longitude": None,
        }

        self.dice: list[int] = [0] * 5
        self.held: list[bool] = [False] * 5
        self.rolls_left = 3
        self.current_player_index = 0
        self.score_labels: dict[str, list[tk.Label]] = {}
        self.total_labels: list[tk.Label] = []

        self.status_var = tk.StringVar()
        self.weather_info_var = tk.StringVar()

        self.player_count_var = tk.IntVar(value=2)
        self.location_var = tk.StringVar(value="Seoul")
        self.detected_location: dict | None = None
        self._auto_detection_in_progress = False
        self._auto_detection_scheduled = False

        self.create_frames()
        self.show_frame("start")
        self.schedule_auto_location_detection()
        self.set_fullscreen(True)

    def create_frames(self) -> None:
        self.frames["start"] = tk.Frame(self.root, bg=self.current_theme["bg"])
        self.frames["setup"] = tk.Frame(self.root, bg=self.current_theme["bg"])
        self.frames["game"] = tk.Frame(self.root, bg=self.current_theme["bg"])

        self.build_start_frame()
        self.build_setup_frame()
        self.build_game_frame()

    def get_fullscreen_button_label(self) -> str:
        return "전체화면 해제 (Esc)" if self.is_fullscreen else "전체화면 실행 (F11)"

    def update_fullscreen_button(self) -> None:
        if self.fullscreen_button is not None:
            self.fullscreen_button.config(text=self.get_fullscreen_button_label())

    def set_fullscreen(self, enabled: bool) -> None:
        if enabled == self.is_fullscreen:
            return
        if enabled:
            try:
                self.window_geometry = self.root.geometry()
            except Exception:
                self.window_geometry = "1100x820"
        self.is_fullscreen = enabled
        try:
            self.root.attributes("-fullscreen", enabled)
        except tk.TclError:
            if enabled:
                self.root.state("zoomed")
            else:
                self.root.state("normal")
        if not enabled and self.window_geometry:
            self.root.geometry(self.window_geometry)
        self.update_fullscreen_button()

    def toggle_fullscreen(self, event=None) -> None:
        self.set_fullscreen(not self.is_fullscreen)

    def exit_fullscreen(self, event=None) -> None:
        self.set_fullscreen(False)

    def return_to_start(self) -> None:
        if messagebox.askyesno("처음 화면", "진행 중인 게임을 종료하고 처음 화면으로 돌아가시겠습니까?"):
            self.show_frame("start")

    def confirm_exit(self) -> None:
        if messagebox.askyesno("게임 종료", "게임을 종료하시겠습니까?"):
            self.root.destroy()

    def handle_mousewheel(self, event) -> None:
        game_frame = self.frames.get("game")
        if game_frame is None or not game_frame.winfo_ismapped():
            return
        try:
            pointer_widget = self.root.winfo_containing(*self.root.winfo_pointerxy())
        except Exception:
            pointer_widget = event.widget

        canvas = self._locate_scroll_canvas(pointer_widget)
        if canvas is None or not canvas.winfo_exists():
            return
        try:
            delta = int(-1 * (event.delta / 120))
        except Exception:
            return
        canvas.yview_scroll(delta, "units")

    def _locate_scroll_canvas(self, widget: tk.Widget | None) -> tk.Canvas | None:
        if widget is None:
            return None
        category_canvas = getattr(self, "category_canvas", None)
        score_canvas = getattr(self, "score_canvas", None)

        current = widget
        while current is not None:
            if current is category_canvas:
                return category_canvas
            if current is score_canvas:
                return score_canvas
            current = getattr(current, "master", None)
        return None

    def schedule_auto_location_detection(self) -> None:
        if self._auto_detection_scheduled:
            return
        self._auto_detection_scheduled = True
        self.root.after(400, lambda: self.auto_detect_location(silent=True))

    def auto_detect_location(self, *, silent: bool) -> None:
        if requests is None or self._auto_detection_in_progress:
            return
        if silent and self.detected_location is not None:
            return
        if not ensure_requests(self.root, show_success=False):
            return

        self._auto_detection_in_progress = True
        loading: tk.Toplevel | None = None
        try:
            if not silent:
                loading = self.show_loading("IP 기반으로 현재 위치를 확인하는 중입니다...")
            self.root.update_idletasks()

            response = requests.get(IP_GEOLOCATION_URL, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise ValueError(data.get("message") or "위치 정보를 가져오지 못했습니다.")

            city = data.get("city")
            latitude = data.get("lat")
            longitude = data.get("lon")

            if not city or latitude is None or longitude is None:
                raise ValueError("필수 위치 정보가 누락되었습니다.")

            self.detected_location = {
                "city": city,
                "lat": latitude,
                "lon": longitude,
            }
            self.location_var.set(city)
            self.status_var.set(f"자동 감지된 위치: {city}")

            if not silent:
                try:
                    messagebox.showinfo("위치 자동 감지", f"현재 위치를 {city}로 설정했습니다.")
                except Exception:
                    pass
        except Exception as exc:
            if not silent:
                try:
                    messagebox.showwarning("위치 자동 감지 실패", f"현재 위치를 확인하지 못했습니다.\n\n사유: {exc}")
                except Exception:
                    pass
        finally:
            self.hide_loading(loading)
            self._auto_detection_in_progress = False

    def build_start_frame(self) -> None:
        frame = self.frames["start"]
        for widget in frame.winfo_children():
            widget.destroy()

        title = tk.Label(
            frame,
            text="Weather Yacht",
            font=("Helvetica", 36, "bold"),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        )
        title.pack(pady=60)

        start_btn = tk.Button(
            frame,
            text="게임 시작",
            font=("Helvetica", 18),
            width=15,
            command=lambda: self.show_frame("setup"),
        )
        start_btn.pack(pady=20)

        how_to_btn = tk.Button(
            frame,
            text="게임 방법",
            font=("Helvetica", 18),
            width=15,
            command=self.show_rules,
        )
        how_to_btn.pack(pady=10)
        self.fullscreen_button = tk.Button(
            frame,
            text=self.get_fullscreen_button_label(),
            font=("Helvetica", 14),
            width=18,
            command=self.toggle_fullscreen,
        )
        self.fullscreen_button.pack(pady=10)
        tk.Label(
            frame,
            text="단축키: F11 전체화면, Esc 전체화면 해제",
            font=("Helvetica", 12),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        ).pack(pady=5)

    def build_setup_frame(self) -> None:
        frame = self.frames["setup"]
        for widget in frame.winfo_children():
            widget.destroy()

        tk.Label(
            frame,
            text="게임 설정",
            font=("Helvetica", 28, "bold"),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        ).pack(pady=30)

        selector = tk.Frame(frame, bg=self.current_theme["bg"])
        selector.pack(pady=20)

        tk.Label(
            selector,
            text="플레이어 수 (1~4명):",
            font=("Helvetica", 16),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        ).grid(row=0, column=0, padx=10, pady=5, sticky="e")

        count_box = tk.Spinbox(
            selector,
            from_=1,
            to=4,
            width=5,
            font=("Helvetica", 16),
            textvariable=self.player_count_var,
            command=self.update_player_entries,
        )
        count_box.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        tk.Label(
            selector,
            text="도시 이름 (영문):",
            font=("Helvetica", 16),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        ).grid(row=1, column=0, padx=10, pady=5, sticky="e")

        tk.Entry(
            selector,
            textvariable=self.location_var,
            font=("Helvetica", 16),
            width=18,
        ).grid(row=1, column=1, padx=10, pady=5, sticky="w")

        tk.Button(
            selector,
            text="위치 자동 감지",
            font=("Helvetica", 14),
            command=lambda: self.auto_detect_location(silent=False),
        ).grid(row=1, column=2, padx=10, pady=5, sticky="w")

        self.names_container = tk.Frame(frame, bg=self.current_theme["bg"])
        self.names_container.pack(pady=30)
        self.update_player_entries()

        tk.Button(
            frame,
            text="시작하기",
            font=("Helvetica", 18),
            width=15,
            command=self.prepare_game,
        ).pack(pady=20)

        tk.Button(
            frame,
            text="처음으로",
            font=("Helvetica", 14),
            command=lambda: self.show_frame("start"),
        ).pack()

    def build_game_frame(self) -> None:
        frame = self.frames["game"]
        for widget in frame.winfo_children():
            widget.destroy()

        header = tk.Frame(frame, bg=self.current_theme["bg"])
        header.pack(fill="x", pady=10)

        self.current_player_label = tk.Label(
            header,
            text="",
            font=("Helvetica", 20, "bold"),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        )
        self.current_player_label.pack(side="left", padx=20)

        weather_label = tk.Label(
            header,
            textvariable=self.weather_info_var,
            font=("Helvetica", 14),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        )
        weather_label.pack(side="right", padx=20)

        actions = tk.Frame(frame, bg=self.current_theme["bg"])
        actions.pack(fill="x", padx=20, pady=(0, 10))
        tk.Button(
            actions,
            text="게임 방법",
            font=("Helvetica", 12),
            command=self.show_rules,
            width=12,
        ).pack(side="left", padx=5)
        tk.Button(
            actions,
            text="처음 화면",
            font=("Helvetica", 12),
            command=self.return_to_start,
            width=12,
        ).pack(side="left", padx=5)
        tk.Button(
            actions,
            text="게임 종료",
            font=("Helvetica", 12),
            command=self.confirm_exit,
            width=12,
        ).pack(side="right", padx=5)

        dice_section = tk.Frame(frame, bg=self.current_theme["bg"])
        dice_section.pack(pady=20)

        self.dice_views: list[DiceView] = []
        for i in range(5):
            view = DiceView(
                dice_section,
                index=i,
                command=self.toggle_hold,
                size=110,
            )
            view.grid(row=0, column=i, padx=12)
            self.dice_views.append(view)

        controls = tk.Frame(frame, bg=self.current_theme["bg"])
        controls.pack(pady=10)

        self.rolls_label = tk.Label(
            controls,
            text="남은 굴림: 3",
            font=("Helvetica", 16),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        )
        self.rolls_label.grid(row=0, column=0, padx=10)

        self.roll_button = tk.Button(
            controls,
            text="주사위 굴리기",
            font=("Helvetica", 16),
            width=15,
            command=self.roll_dice,
        )
        self.roll_button.grid(row=0, column=1, padx=10)

        self.ability_button = tk.Button(
            controls,
            text="찬스 사용",
            font=("Helvetica", 16),
            width=15,
            command=self.use_weather_ability,
        )
        self.ability_button.grid(row=0, column=2, padx=10)

        self.status_label = tk.Label(
            frame,
            textvariable=self.status_var,
            font=("Helvetica", 14),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
        )
        self.status_label.pack(pady=10)

        self.category_frame = tk.LabelFrame(
            frame,
            text="카테고리 선택",
            font=("Helvetica", 16, "bold"),
        )
        self.category_frame.pack(side="left", fill="both", expand=False, padx=20, pady=10)

        self.category_canvas = tk.Canvas(
            self.category_frame,
            borderwidth=0,
            highlightthickness=0,
            width=230,
            bg=self.category_frame.cget("background"),
        )
        self.category_scrollbar = tk.Scrollbar(
            self.category_frame,
            orient="vertical",
            command=self.category_canvas.yview,
        )
        self.category_inner = tk.Frame(self.category_canvas)
        self.category_inner.bind(
            "<Configure>",
            lambda event: self.category_canvas.configure(
                scrollregion=self.category_canvas.bbox("all")
            ),
        )
        self.category_canvas.create_window((0, 0), window=self.category_inner, anchor="nw")
        self.category_canvas.configure(yscrollcommand=self.category_scrollbar.set)
        self.category_canvas.pack(side="left", fill="both", expand=True)
        self.category_scrollbar.pack(side="right", fill="y")

        self.category_buttons: dict[str, tk.Button] = {}
        for idx, (code, display) in enumerate(CATEGORIES):
            btn = tk.Button(
                self.category_inner,
                text=display,
                font=("Helvetica", 14),
                width=18,
                command=lambda c=code: self.record_score(c),
            )
            btn.grid(row=idx, column=0, padx=10, pady=4, sticky="ew")
            self.category_buttons[code] = btn

        self.score_container = tk.Frame(frame, bg=self.current_theme["bg"])
        self.score_container.pack(side="right", fill="both", expand=True, padx=20, pady=10)

        self.score_canvas = tk.Canvas(
            self.score_container,
            borderwidth=0,
            highlightthickness=0,
            bg=self.current_theme["bg"],
        )
        self.score_scrollbar = tk.Scrollbar(
            self.score_container,
            orient="vertical",
            command=self.score_canvas.yview,
        )
        self.score_inner = tk.Frame(self.score_canvas, bg=self.current_theme["bg"])
        self.score_inner.bind(
            "<Configure>",
            lambda event: self.score_canvas.configure(
                scrollregion=self.score_canvas.bbox("all")
            ),
        )
        self.score_canvas.create_window((0, 0), window=self.score_inner, anchor="nw")
        self.score_canvas.configure(yscrollcommand=self.score_scrollbar.set)
        self.score_canvas.pack(side="left", fill="both", expand=True)
        self.score_scrollbar.pack(side="right", fill="y")

        self.score_frame = self.score_inner

    def update_player_entries(self) -> None:
        existing_names = [var.get() for var in self.player_name_vars]
        for widget in self.names_container.winfo_children():
            widget.destroy()
        self.player_entries.clear()
        self.player_name_vars.clear()

        count = self.player_count_var.get()
        for idx in range(count):
            default_name = f"플레이어 {idx + 1}"
            initial_value = existing_names[idx] if idx < len(existing_names) else default_name
            name_text = initial_value or default_name

            label = tk.Label(
                self.names_container,
                text=f"플레이어 {idx + 1} 이름:",
                font=("Helvetica", 14),
                bg=self.current_theme["bg"],
                fg=self.current_theme["fg"],
            )
            label.grid(row=idx, column=0, padx=10, pady=5, sticky="e")

            var = tk.StringVar(value=name_text)
            entry = tk.Entry(
                self.names_container,
                textvariable=var,
                font=("Helvetica", 14),
                width=18,
            )
            entry.grid(row=idx, column=1, padx=10, pady=5, sticky="w")
            self.player_entries.append(entry)
            self.player_name_vars.append(var)

    def prepare_game(self) -> None:
        count = self.player_count_var.get()
        if count < 1 or count > 4:
            messagebox.showerror("오류", "플레이어 수는 1명에서 4명 사이여야 합니다.")
            return

        names = [var.get().strip() or f"플레이어 {idx + 1}" for idx, var in enumerate(self.player_name_vars)]

        city = self.location_var.get().strip() or "Seoul"
        latitude = None
        longitude = None
        if self.detected_location:
            detected_city = self.detected_location.get("city")
            if isinstance(detected_city, str) and detected_city.casefold() == city.casefold():
                latitude = self.detected_location.get("lat")
                longitude = self.detected_location.get("lon")

        loading = self.show_loading("인터넷 연결 확인 및 날씨를 불러오는 중입니다...")
        self.root.update_idletasks()

        weather = None
        try:
            if not ensure_requests(self.root, show_success=False):
                return
            if not self.verify_api_connection():
                return
            weather = self.fetch_weather(city, latitude, longitude)
        finally:
            self.hide_loading(loading)

        if weather is None:
            messagebox.showerror(
                "날씨 정보 오류",
                "선택한 도시의 날씨를 불러올 수 없습니다.\n인터넷 연결과 입력한 도시 이름을 확인해주세요.",
            )
            return

        condition = weather["condition"]
        temperature = weather["temperature"]
        code = weather["code"]

        latitude = weather.get("latitude")
        longitude = weather.get("longitude")

        self.weather_context = {
            "city": city,
            "temperature": temperature,
            "code": code,
            "condition_key": condition,
            "latitude": latitude,
            "longitude": longitude,
        }
        self.apply_theme(condition)

        self.players = []
        for name in names:
            self.players.append(
                {
                    "name": name,
                    "scores": {},
                    "ability_used": False,
                    "pending_bonus": 0,
                }
            )

        self.setup_scoreboard()
        self.reset_game_state()
        self.show_frame("game")
        self.start_turn()

    def verify_api_connection(self) -> bool:
        if not ensure_requests(self.root, show_success=False):
            return False
        try:
            response = requests.get(API_TEST_URL, timeout=5)
            response.raise_for_status()
            return True
        except RequestException as exc:
            messagebox.showerror(
                "인터넷 연결 필요",
                "Open-Meteo API에 연결할 수 없습니다.\n"
                "인터넷 상태 또는 SSL 인증서를 확인한 뒤 다시 시도해주세요.\n\n"
                f"오류: {exc}",
            )
            return False

    def fetch_weather(
        self,
        city: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict | None:
        if requests is None:
            return None

        try:
            target_lat = latitude
            target_lon = longitude

            if target_lat is None or target_lon is None:
                geo_url = (
                    "https://geocoding-api.open-meteo.com/v1/search?"
                    f"name={quote(city)}&count=1&language=ko&format=json"
                )
                geo_resp = requests.get(geo_url, timeout=10)
                geo_resp.raise_for_status()
                geo_data = geo_resp.json()
                if not geo_data.get("results"):
                    return None
                result = geo_data["results"][0]
                target_lat = result["latitude"]
                target_lon = result["longitude"]

            weather_url = (
                "https://api.open-meteo.com/v1/forecast?"
                f"latitude={target_lat}&longitude={target_lon}&current=temperature_2m,weather_code"
            )
            weather_resp = requests.get(weather_url, timeout=10)
            weather_resp.raise_for_status()
            weather_data = weather_resp.json()
            current = weather_data.get("current")
            if not current:
                return None
            temperature = current.get("temperature_2m")
            code = current.get("weather_code", 1)
            condition = classify_weather(code)
            return {
                "temperature": temperature,
                "code": code,
                "condition": condition,
                "latitude": target_lat,
                "longitude": target_lon,
            }
        except Exception:
            return None

    def apply_theme(self, condition: str) -> None:
        self.current_theme = WEATHER_THEMES.get(condition, WEATHER_THEMES["cloudy"])
        for frame in self.frames.values():
            frame.configure(bg=self.current_theme["bg"])
        self.root.configure(bg=self.current_theme["bg"])
        self.build_start_frame()
        self.build_setup_frame()
        self.build_game_frame()

    def setup_scoreboard(self) -> None:
        for widget in self.score_frame.winfo_children():
            widget.destroy()

        header_font = ("Helvetica", 16, "bold")
        cell_font = ("Helvetica", 14)

        category_header = tk.Label(
            self.score_frame,
            text="카테고리",
            font=header_font,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            width=18,
        )
        category_header.grid(row=0, column=0, padx=5, pady=5)

        self.score_labels = {code: [] for code, _ in CATEGORIES}
        self.total_labels = []

        for col, player in enumerate(self.players, start=1):
            player_label = tk.Label(
                self.score_frame,
                text=player["name"],
                font=header_font,
                bg=self.current_theme["bg"],
                fg=self.current_theme["fg"],
                width=12,
            )
            player_label.grid(row=0, column=col, padx=5, pady=5)

        for row, (code, display) in enumerate(CATEGORIES, start=1):
            label = tk.Label(
                self.score_frame,
                text=display,
                font=cell_font,
                bg=self.current_theme["bg"],
                fg=self.current_theme["fg"],
                width=18,
                anchor="w",
            )
            label.grid(row=row, column=0, padx=5, pady=3, sticky="w")
            for col in range(len(self.players)):
                lbl = tk.Label(
                    self.score_frame,
                    text="-",
                    font=cell_font,
                    bg="white",
                    fg="black",
                    width=10,
                    relief="ridge",
                    borderwidth=2,
                )
                lbl.grid(row=row, column=col + 1, padx=3, pady=3)
                self.score_labels[code].append(lbl)

        total_row = len(CATEGORIES) + 1
        total_label = tk.Label(
            self.score_frame,
            text="총점",
            font=header_font,
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            width=18,
        )
        total_label.grid(row=total_row, column=0, padx=5, pady=5)

        for col in range(len(self.players)):
            lbl = tk.Label(
                self.score_frame,
                text="0",
                font=header_font,
                bg=self.current_theme["bg"],
                fg=self.current_theme["fg"],
                width=10,
            )
            lbl.grid(row=total_row, column=col + 1, padx=5, pady=5)
            self.total_labels.append(lbl)

        self.score_frame.update_idletasks()
        if hasattr(self, "score_canvas"):
            self.score_canvas.configure(scrollregion=self.score_canvas.bbox("all"))
            self.score_canvas.yview_moveto(0)

    def show_loading(self, message: str) -> tk.Toplevel:
        self.root.update_idletasks()
        top = tk.Toplevel(self.root)
        top.title("연결 중...")
        top.resizable(False, False)
        top.configure(bg=self.current_theme["bg"])
        width, height = 320, 160
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        x_pos = root_x + (root_w // 2) - (width // 2)
        y_pos = root_y + (root_h // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        top.transient(self.root)
        top.grab_set()
        top.protocol("WM_DELETE_WINDOW", lambda: None)

        tk.Label(
            top,
            text=message,
            font=("Helvetica", 13),
            bg=self.current_theme["bg"],
            fg=self.current_theme["fg"],
            wraplength=280,
            justify="center",
        ).pack(pady=(35, 15), padx=20)

        progress = ttk.Progressbar(top, mode="indeterminate", length=220)
        progress.pack(pady=10)
        progress.start(10)
        top.progressbar = progress  # type: ignore[attr-defined]
        top.update_idletasks()
        return top

    def hide_loading(self, window: tk.Toplevel | None) -> None:
        if window is None:
            return
        try:
            progress = getattr(window, "progressbar", None)
            if progress is not None:
                progress.stop()
            window.grab_release()
            window.destroy()
        except tk.TclError:
            pass

    def reset_game_state(self) -> None:
        self.dice = [0] * 5
        self.held = [False] * 5
        self.rolls_left = 3
        self.current_player_index = 0
        self.status_var.set("")
        self.weather_info_var.set(self.describe_weather())
        self.update_dice_display()
        self.update_rolls_label()
        self.update_category_buttons()
        self.update_ability_button()

    def describe_weather(self) -> str:
        city = self.weather_context["city"]
        temp = self.weather_context["temperature"]
        condition_key = self.weather_context["condition_key"]
        theme = WEATHER_THEMES.get(condition_key, WEATHER_THEMES["cloudy"])
        ability_name = theme["ability_name"]
        if temp is None:
            return f"{city}: {ability_name}"
        return f"{city}: {temp:.1f}°C, {ability_name}"

    def start_turn(self) -> None:
        player = self.players[self.current_player_index]
        self.dice = [0] * 5
        self.held = [False] * 5
        self.rolls_left = 3
        self.status_var.set(f"{player['name']} 차례입니다. 주사위를 굴려주세요.")
        self.current_player_label.config(text=f"현재 플레이어: {player['name']}")
        self.update_rolls_label()
        self.update_dice_display()
        self.update_category_buttons()
        self.update_ability_button()

    def roll_dice(self) -> None:
        if self.rolls_left <= 0:
            messagebox.showinfo("안내", "더 이상 굴릴 수 없습니다. 카테고리를 선택하세요.")
            return

        for idx in range(5):
            if not self.held[idx]:
                self.dice[idx] = random.randint(1, 6)

        self.rolls_left -= 1
        self.status_var.set(
            f"주사위를 굴렸습니다. 남은 굴림 {self.rolls_left}회."
        )
        self.update_rolls_label()
        self.update_dice_display()

    def force_reroll(self) -> None:
        self.held = [False] * 5
        for idx in range(5):
            self.dice[idx] = random.randint(1, 6)
        self.status_var.set("번개 찬스로 주사위를 다시 굴렸습니다.")
        self.update_dice_display()

    def update_rolls_label(self) -> None:
        self.rolls_label.config(text=f"남은 굴림: {self.rolls_left}")

    def update_dice_display(self) -> None:
        if not hasattr(self, "dice_views"):
            return
        for idx, view in enumerate(self.dice_views):
            value = self.dice[idx]
            view.render(value, self.held[idx], self.current_theme["fg"])
        self.update_category_buttons()

    def toggle_hold(self, index: int) -> None:
        if self.dice[index] == 0:
            return
        self.held[index] = not self.held[index]
        self.update_dice_display()

    def update_category_buttons(self) -> None:
        if not getattr(self, "category_buttons", None):
            return
        if not self.players:
            return

        player = self.players[self.current_player_index]
        dice_ready = all(value > 0 for value in self.dice)
        bonus = player.get("pending_bonus", 0)

        for code, button in self.category_buttons.items():
            base_text = CATEGORY_DISPLAY_MAP.get(code, code)
            if code in player["scores"]:
                button.config(state="disabled", text=f"{base_text} (기록됨)")
                continue

            button.config(state="normal")
            if dice_ready:
                expected = calculate_score(code, self.dice)
                total_expected = expected + bonus
                if bonus:
                    button.config(text=f"{base_text} (예상 {total_expected}점, 보너스 포함)")
                else:
                    button.config(text=f"{base_text} (예상 {expected}점)")
            else:
                button.config(text=base_text)

    def update_ability_button(self) -> None:
        player = self.players[self.current_player_index]
        theme = self.current_theme
        desc = theme["ability_desc"]
        name = theme["ability_name"]
        self.ability_button.config(text=f"{name} 사용")

        if player["ability_used"]:
            self.ability_button.config(state="disabled")
            self.status_var.set(f"{player['name']}은(는) 이미 찬스를 사용했습니다.")
        else:
            self.ability_button.config(state="normal")
            self.status_var.set(f"{player['name']} 차례입니다. {desc}")

    def use_weather_ability(self) -> None:
        player = self.players[self.current_player_index]
        if player["ability_used"]:
            messagebox.showinfo("안내", "이미 찬스를 사용했습니다.")
            return

        ability = self.current_theme["ability_key"]
        applied = False

        if ability == "set_die_to_six":
            applied = self.ability_set_die()
        elif ability == "reroll_selected":
            applied = self.ability_reroll_selected()
        elif ability == "add_five_points":
            player["pending_bonus"] += 5
            self.status_var.set("빗방울 찬스를 사용했습니다! 다음 점수에 +5점이 추가됩니다.")
            applied = True
        elif ability == "swap_dice":
            applied = self.ability_swap_dice()
        elif ability == "full_reroll":
            applied = self.ability_full_reroll()

        if applied:
            player["ability_used"] = True
            self.ability_button.config(state="disabled")

    def ability_set_die(self) -> bool:
        if all(value == 0 for value in self.dice):
            messagebox.showinfo("안내", "먼저 주사위를 굴려주세요.")
            return False
        index = simpledialog.askinteger(
            "햇살 찬스",
            "6으로 바꿀 주사위 위치를 입력하세요 (1~5):",
            minvalue=1,
            maxvalue=5,
            parent=self.root,
        )
        if index is None:
            return False
        self.dice[index - 1] = 6
        self.status_var.set("햇살 찬스로 주사위 하나를 6으로 변경했습니다.")
        self.update_dice_display()
        return True

    def ability_reroll_selected(self) -> bool:
        if all(value == 0 for value in self.dice):
            messagebox.showinfo("안내", "먼저 주사위를 굴려주세요.")
            return False
        raw = simpledialog.askstring(
            "바람 찬스",
            "다시 굴릴 주사위 위치를 입력하세요 (예: 1,3), 최대 2개:",
            parent=self.root,
        )
        if not raw:
            return False
        try:
            parts = [int(part.strip()) for part in raw.split(",")]
        except ValueError:
            messagebox.showerror("오류", "숫자와 콤마만 입력하세요.")
            return False
        if len(parts) == 0 or len(parts) > 2:
            messagebox.showerror("오류", "최대 2개의 주사위를 선택할 수 있습니다.")
            return False
        for part in parts:
            if part < 1 or part > 5:
                messagebox.showerror("오류", "주사위 위치는 1에서 5 사이입니다.")
                return False
        for part in parts:
            idx = part - 1
            self.held[idx] = False
            self.dice[idx] = random.randint(1, 6)
        self.status_var.set("바람 찬스로 선택한 주사위를 다시 굴렸습니다.")
        self.update_dice_display()
        return True

    def ability_swap_dice(self) -> bool:
        if all(value == 0 for value in self.dice):
            messagebox.showinfo("안내", "먼저 주사위를 굴려주세요.")
            return False
        raw = simpledialog.askstring(
            "눈꽃 찬스",
            "서로 값을 바꿀 두 주사위 위치를 입력하세요 (예: 2,5):",
            parent=self.root,
        )
        if not raw:
            return False
        try:
            first, second = [int(part.strip()) for part in raw.split(",")]
        except ValueError:
            messagebox.showerror("오류", "콤마로 구분된 두 숫자를 입력하세요.")
            return False
        if first < 1 or first > 5 or second < 1 or second > 5:
            messagebox.showerror("오류", "주사위 위치는 1에서 5 사이입니다.")
            return False
        idx1 = first - 1
        idx2 = second - 1
        self.dice[idx1], self.dice[idx2] = self.dice[idx2], self.dice[idx1]
        self.status_var.set("눈꽃 찬스로 두 주사위의 값을 서로 바꿨습니다.")
        self.update_dice_display()
        return True

    def ability_full_reroll(self) -> bool:
        if all(value == 0 for value in self.dice):
            messagebox.showinfo("안내", "먼저 주사위를 굴려주세요.")
            return False
        self.force_reroll()
        return True

    def record_score(self, category: str) -> None:
        player = self.players[self.current_player_index]
        if category in player["scores"]:
            messagebox.showinfo("안내", "이미 기록한 카테고리입니다.")
            return
        if all(value == 0 for value in self.dice):
            messagebox.showinfo("안내", "먼저 주사위를 굴려주세요.")
            return

        score = calculate_score(category, self.dice)
        bonus = player.get("pending_bonus", 0)
        if bonus:
            score += bonus
            player["pending_bonus"] = 0
            self.status_var.set(f"찬스 보너스로 +{bonus}점이 추가되었습니다.")
        else:
            self.status_var.set("")

        player["scores"][category] = score
        self.score_labels[category][self.current_player_index].config(text=str(score))
        self.update_totals()
        self.advance_turn()

    def update_totals(self) -> None:
        for idx, player in enumerate(self.players):
            total = sum(player["scores"].values())
            self.total_labels[idx].config(text=str(total))

    def advance_turn(self) -> None:
        finished = all(
            len(player["scores"]) == len(CATEGORIES) for player in self.players
        )
        if finished:
            self.finish_game()
            return
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.start_turn()

    def finish_game(self) -> None:
        totals = [sum(player["scores"].values()) for player in self.players]
        max_score = max(totals)
        winners = [
            player["name"] for player, total in zip(self.players, totals) if total == max_score
        ]
        if len(winners) == 1:
            winner_text = f"우승자는 {winners[0]}! 점수: {max_score}"
        else:
            names = ", ".join(winners)
            winner_text = f"공동 우승: {names}! 점수: {max_score}"

        detail_lines = [
            f"{player['name']}: {total}점"
            for player, total in zip(self.players, totals)
        ]
        messagebox.showinfo("게임 종료", winner_text + "\n\n" + "\n".join(detail_lines))

        retry = messagebox.askyesno("다시 플레이", "다시 플레이하시겠습니까?")
        if retry:
            for player in self.players:
                player["scores"].clear()
                player["ability_used"] = False
                player["pending_bonus"] = 0
            self.setup_scoreboard()
            self.reset_game_state()
            self.start_turn()
        else:
            self.show_frame("start")

    def show_rules(self) -> None:
        rules = tk.Toplevel(self.root)
        rules.title("게임 방법")
        rules.geometry("520x600")
        rules.resizable(False, False)

        text = (
            "◆ Weather Yacht 인터페이스\n"
            "1. 원하는 도시를 입력하고 플레이어 수를 선택합니다.\n"
            "2. 날씨에 따라 배경과 특별 찬스가 결정됩니다.\n"
            "3. 각 플레이어는 차례마다 최대 3번 주사위를 굴릴 수 있고, 주사위를 선택해 고정할 수 있습니다.\n"
            "4. 굴림 이후 비어 있는 카테고리에 점수를 기록해야 합니다.\n\n"
            "◆ 기본 규칙\n"
            "- 주사위는 총 5개를 사용하며 각 카테고리는 한 번만 기록할 수 있습니다.\n"
            "- 포카드: 같은 눈이 4개 이상이면 주사위 합계를 점수로 얻습니다.\n"
            "- 풀하우스: 같은 눈 3개 + 2개 조합이면 25점입니다.\n"
            "- 스몰 스트레이트: 연속한 4개의 눈이 나오면 30점입니다.\n"
            "- 라지 스트레이트: 1-5 또는 2-6이 나오면 40점입니다.\n"
            "- 야추: 모든 주사위가 같은 눈이면 50점입니다.\n"
            "- 찬스: 나온 눈의 합계를 그대로 점수로 얻습니다.\n\n"
            "◆ 날씨 찬스\n"
            "- 맑음: 햇살 찬스로 원하는 주사위 하나를 6으로 바꿀 수 있습니다.\n"
            "- 흐림: 바람 찬스로 주사위 두 개까지 다시 굴릴 수 있습니다.\n"
            "- 비: 빗방울 찬스로 해당 턴 점수에 +5점을 더합니다.\n"
            "- 눈: 눈꽃 찬스로 주사위 두 개의 위치를 교환합니다.\n"
            "- 폭풍: 번개 찬스로 주사위를 한 번 더 모두 굴립니다.\n"
            "각 찬스는 플레이어마다 1회만 사용할 수 있습니다.\n\n"
            "모든 카테고리가 채워지면 가장 높은 점수를 얻은 플레이어가 승리합니다!"
        )

        tk.Label(
            rules,
            text="게임 방법",
            font=("Helvetica", 20, "bold"),
        ).pack(pady=15)

        text_widget = tk.Text(
            rules,
            wrap="word",
            font=("Helvetica", 12),
        )
        text_widget.pack(fill="both", expand=True, padx=15, pady=10)
        text_widget.insert("1.0", text)
        text_widget.config(state="disabled")

        tk.Button(
            rules,
            text="닫기",
            font=("Helvetica", 12),
            command=rules.destroy,
        ).pack(pady=10)

    def show_frame(self, name: str) -> None:
        for frame_name, frame in self.frames.items():
            if frame_name == name:
                frame.pack(fill="both", expand=True)
                frame.tkraise()
            else:
                frame.pack_forget()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    if not ensure_requests(root, show_success=False):
        root.destroy()
        return
    root.deiconify()
    app = WeatherYachtApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
