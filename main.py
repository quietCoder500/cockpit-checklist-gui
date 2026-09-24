"""Offline, keyboard-first routine checklist for small computers."""
from __future__ import annotations

import json
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = Path.home() / ".daily_checklist_state.json"
BG = "#000000"
PANEL = "#000000"
PANEL_DARK = "#000000"
LINE = "#3c4b58"
MUTED = "#83939c"
GREEN = "#69ec7d"
CYAN = "#62e7e4"
AMBER = "#f1bd54"
WHITE = "#d5e1e5"
FONT = "DejaVu Sans Mono"


DEFAULT_CONFIG = {
    "page_names": ["Great", "Average", "Poor"],
    "phases": [
        {"id": "morning", "name": "Morning", "pages": {
            "Great": ["Make bed", "Brush teeth", "Shave", "Get dressed", "Eat breakfast", "Go for a walk"],
            "Average": ["Make bed", "Brush teeth", "Shave", "Eat breakfast"],
            "Poor": ["Brush teeth", "Eat something"]}},
        {"id": "workday", "name": "Workday", "pages": {
            "Great": ["Review today's priorities", "Drink water", "Take a proper lunch break", "Go for a short walk", "Tidy work area"],
            "Average": ["Review today's priorities", "Drink water", "Take a lunch break"],
            "Poor": ["Drink water", "Eat lunch"]}},
        {"id": "evening", "name": "Evening", "pages": {
            "Great": ["Go for a walk", "Prepare for tomorrow", "Tidy living space", "Brush teeth", "Set out clothes"],
            "Average": ["Prepare for tomorrow", "Brush teeth", "Set out clothes"],
            "Poor": ["Brush teeth", "Set alarm"]}},
    ],
}


def load_json(path: Path, fallback):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return fallback


class ChecklistApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = load_json(CONFIG_PATH, DEFAULT_CONFIG)
        self.phases = self.config.get("phases", DEFAULT_CONFIG["phases"])
        self.modes = self.config.get("page_names", DEFAULT_CONFIG["page_names"])
        if not self.phases or not self.modes:
            self.config = DEFAULT_CONFIG
            self.phases = self.config["phases"]
            self.modes = self.config["page_names"]
        saved = load_json(STATE_PATH, {})
        self.phase_index = next((i for i, p in enumerate(self.phases) if p["id"] == saved.get("phase")), 0)
        self.mode_index = self.modes.index(saved["mode"]) if saved.get("mode") in self.modes else min(1, len(self.modes)-1)
        self.selected_row = 0
        self.nav_group = "tasks"
        self.day = date.today().isoformat()
        self.checks = saved.get("checks", {}) if saved.get("day") == self.day else {}
        self.skips = saved.get("skips", {}) if saved.get("day") == self.day else {}
        self.expanded = saved.get("expanded", True) if saved.get("day") == self.day else True
        self.undo_stack = []
        self._style()
        self._build()
        self._draw()
        self.root.bind_all("<Up>", lambda event: self._move(-1))
        self.root.bind_all("<Down>", lambda event: self._move(1))
        self.root.bind_all("<Left>", lambda event: self._horizontal(-1))
        self.root.bind_all("<Right>", lambda event: self._horizontal(1))
        self.root.bind_all("<Return>", self._enter)
        self.root.bind_all("<space>", self._enter)
        self.root.bind_all("<s>", self._skip)
        self.root.bind_all("<S>", self._skip)
        self.root.bind_all("<u>", self._undo)
        self.root.bind_all("<U>", self._undo)
        self.root.bind_all("<Tab>", self._tab)
        self.root.bind_all("<Shift-Tab>", self._shift_tab)
        self.root.after(1000, self._tick)

    def _style(self):
        self.root.title("Daily Checklist")
        self.root.configure(bg=BG)
        self.root.geometry("1100x660")
        self.root.minsize(760, 480)
        self.root.option_add("*Font", (FONT, 10))

    def _label(self, parent, text, *, color=WHITE, size=10, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=kwargs.pop("bg", PANEL), fg=color,
                        font=(FONT, size, "bold" if bold else "normal"), **kwargs)

    def _panel(self, parent, title, width=None):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1,
                         width=width)
        frame.pack_propagate(False)
        head = tk.Frame(frame, bg="#f1f3f2", height=34)
        head.pack(fill="x")
        head.pack_propagate(False)
        title_label = self._label(head, title, color="#000000", size=9, bold=True, bg="#f1f3f2")
        title_label.pack(side="left", padx=10, pady=8)
        return frame, title_label

    def _build(self):
        outer = tk.Frame(self.root, bg="#000000", padx=12, pady=9,
                         highlightbackground="#56616a", highlightthickness=2)
        outer.pack(fill="both", expand=True, padx=12, pady=12)
        top = tk.Frame(outer, bg="#000000")
        top.pack(fill="x", pady=(0, 8))
        self.system_label = self._label(top, "●  PERSONAL ROUTINE SYSTEM", color="#c4d0d3", bg="#000000", size=9, bold=True)
        self.system_label.pack(side="left")
        self.clock_label = self._label(top, "--:--", color=GREEN, bg="#000000", size=16, bold=True)
        self.clock_label.pack(side="right")
        self.date_label = self._label(top, "", color=WHITE, bg="#000000", size=9)
        self.date_label.pack(side="right", padx=18)
        tk.Frame(outer, bg=LINE, height=1).pack(fill="x", pady=(0, 9))

        instruments = tk.Frame(outer, bg="#000000")
        instruments.pack(fill="x", pady=(0, 9))
        for title, key in (("SYSTEM", "NORMAL"), ("DAY MODE", "mode"), ("PHASE PROGRESS", "progress"), ("LOCAL DATE", "today")):
            box = tk.Frame(instruments, bg=PANEL_DARK, highlightbackground=LINE, highlightthickness=1, height=50)
            box.pack(side="left", fill="x", expand=True, padx=(0, 6))
            box.pack_propagate(False)
            self._label(box, title, color=MUTED, size=8, bg=PANEL_DARK).pack(anchor="w", padx=8, pady=(5, 0))
            label = self._label(box, key if key == "NORMAL" else "", color=GREEN if key in ("NORMAL", "mode", "progress") else WHITE,
                                size=10, bold=True, bg=PANEL_DARK)
            label.pack(anchor="w", padx=8)
            if key == "mode": self.mode_readout = label
            elif key == "progress": self.progress_readout = label
            elif key == "today": self.today_readout = label

        body = tk.Frame(outer, bg="#000000")
        body.pack(fill="both", expand=True)
        self.phase_panel, _ = self._panel(body, "TIME PHASE")
        self.phase_panel.pack(side="left", fill="y", padx=(0, 8))
        self.phase_panel.configure(width=180)
        self.phase_buttons = []
        self.phase_container = tk.Frame(self.phase_panel, bg=PANEL)
        self.phase_container.pack(fill="both", expand=True, padx=7, pady=8)
        for i, phase in enumerate(self.phases):
            button = tk.Button(self.phase_container, text=f"0{i+1}   {phase['name'].upper()}",
                               command=lambda index=i: self._choose_phase(index), anchor="w",
                               relief="raised", bd=2, padx=9, pady=11, cursor="hand2",
                               font=(FONT, 9, "bold"), highlightthickness=1)
            button.pack(fill="x", pady=4)
            self.phase_buttons.append(button)
        self._label(self.phase_panel, "CHOOSE WHEN", color=MUTED, size=7).pack(anchor="w", padx=9, pady=(2, 8))

        self.list_panel, self.list_heading = self._panel(body, "CHECKLIST")
        self.list_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.dropdown_button = tk.Button(self.list_heading.master, text="▼", command=self._toggle_dropdown,
                                         relief="raised", bd=2, padx=9, pady=1, cursor="hand2",
                                         font=(FONT, 8, "bold"), bg="#aebbb9", fg="#071012",
                                         activebackground="#c6d0cd", activeforeground="#071012")
        self.dropdown_button.pack(side="right", padx=7, pady=3)
        pagebar = tk.Frame(self.list_panel, bg=PANEL, height=42)
        pagebar.pack(fill="x")
        self._label(pagebar, "BRAIN DAY", color=MUTED, size=8, bg=PANEL).pack(side="left", padx=10, pady=6)
        self.mode_buttons = []
        for i, mode in enumerate(self.modes):
            button = tk.Button(pagebar, text=mode.upper(), command=lambda index=i: self._choose_mode(index),
                               relief="raised", bd=2, padx=12, pady=5, cursor="hand2",
                               font=(FONT, 8, "bold"), highlightthickness=1)
            button.pack(side="left", padx=(8 if i == 0 else 3, 2), pady=6)
            self.mode_buttons.append(button)
        action_keys = tk.Frame(pagebar, bg=PANEL)
        action_keys.pack(side="right", padx=5)
        self.skip_button = tk.Button(action_keys, text="SKIP TODAY", command=self._skip,
                                     relief="raised", bd=2, padx=7, pady=4, cursor="hand2",
                                     font=(FONT, 7, "bold"), bg="#59656a", fg="#d0dada",
                                     activebackground="#aebbb9", activeforeground="#071012")
        self.skip_button.pack(side="left", padx=2)
        self.undo_button = tk.Button(action_keys, text="UNDO", command=self._undo,
                                     relief="raised", bd=2, padx=7, pady=4, cursor="hand2",
                                     font=(FONT, 7, "bold"), bg="#59656a", fg="#d0dada",
                                     activebackground="#aebbb9", activeforeground="#071012")
        self.undo_button.pack(side="left", padx=2)
        caption = tk.Frame(self.list_panel, bg=PANEL_DARK)
        caption.pack(fill="x")
        self._label(caption, "ITEM", color=MUTED, size=8, bg=PANEL_DARK).pack(side="left", padx=12, pady=7)
        self._label(caption, "STATUS", color=MUTED, size=8, bg=PANEL_DARK).pack(side="right", padx=12, pady=7)
        self.tasks_frame = tk.Frame(self.list_panel, bg=PANEL)
        self.tasks_frame.pack(fill="both", expand=True, padx=7, pady=5)
        foot = tk.Frame(self.list_panel, bg="#000000")
        foot.pack(fill="x", side="bottom")
        self.remaining_label = self._label(foot, "REMAINING 00", color=MUTED, bg="#000000", size=8)
        self.remaining_label.pack(side="left", padx=10, pady=8)
        self.complete_label = self._label(foot, "IN PROGRESS", color=AMBER, bg="#000000", size=8)
        self.complete_label.pack(side="right", padx=10, pady=8)

        self.status_panel, _ = self._panel(body, "ROUTINE STATUS")
        self.status_panel.pack(side="left", fill="y")
        self.status_panel.configure(width=185)
        self.phase_status = self._status_field("ACTIVE PHASE")
        self.mode_status = self._status_field("BRAIN DAY", color=GREEN)
        self.count_status = self._status_field("DONE / SKIPPED")
        tk.Frame(self.status_panel, bg=LINE, height=1).pack(fill="x", padx=9, pady=7)
        self._label(self.status_panel, "●  PROGRESS SAVED\n    ON THIS DEVICE", color="#99aaa1", size=8, justify="left").pack(anchor="w", padx=11, pady=7)
        self._label(self.status_panel, "CLICK A BUTTON TO SWITCH\nOR USE TAB + ARROWS", color=CYAN, size=7, justify="left").pack(anchor="w", padx=10, pady=10, side="bottom")

        bottom = tk.Frame(outer, bg="#000000")
        bottom.pack(fill="x", pady=(8, 0))
        self._label(bottom, "DAILY CHECKLIST", color="#bdc9cd", bg="#000000", size=8).pack(side="left")
        self._label(bottom, "TAB: MOVE   ·   ARROWS: NAVIGATE   ·   ENTER: CHECK   ·   S: SKIP   ·   U: UNDO", color=MUTED, bg="#000000", size=7).pack(side="right")

    def _status_field(self, title, color=WHITE):
        block = tk.Frame(self.status_panel, bg=PANEL, padx=10, pady=11)
        block.pack(fill="x")
        self._label(block, title, color=MUTED, size=8).pack(anchor="w")
        value = self._label(block, "", color=color, size=10, bold=True)
        value.pack(anchor="w", pady=(5, 0))
        tk.Frame(self.status_panel, bg=LINE, height=1).pack(fill="x", padx=9)
        return value

    def _active_phase(self): return self.phases[self.phase_index]
    def _items(self): return self._active_phase().get("pages", {}).get(self.modes[self.mode_index], [])
    def _key(self): return self._active_phase()["id"] + ":" + self.modes[self.mode_index]

    def _draw(self):
        phase, mode, tasks = self._active_phase(), self.modes[self.mode_index], self._items()
        checked = self.checks.get(self._key(), [])
        skipped = self.skips.get(self._key(), [])
        self.phase_panel.configure(highlightthickness=2 if self.nav_group == "phases" else 1,
                                   highlightbackground=CYAN if self.nav_group == "phases" else LINE)
        self.list_panel.configure(highlightthickness=2 if self.nav_group == "tasks" else 1,
                                  highlightbackground=CYAN if self.nav_group == "tasks" else LINE)
        self.phase_container.configure(highlightthickness=2 if self.nav_group == "phases" else 0,
                                       highlightbackground=CYAN)
        self.list_panel.winfo_children()[1].configure(highlightthickness=2 if self.nav_group == "modes" else 0,
                                                      highlightbackground=CYAN)
        for i, button in enumerate(self.phase_buttons):
            active = i == self.phase_index
            button.configure(bg="#aebbb9" if active else "#59656a",
                             fg="#071012" if active else "#d0dada",
                             activebackground="#c6d0cd", activeforeground="#071012",
                             relief="sunken" if active else "raised", bd=2,
                             highlightthickness=1, highlightbackground=CYAN if active else "#879295")
        for i, button in enumerate(self.mode_buttons):
            active = i == self.mode_index
            button.configure(bg="#aebbb9" if active else "#59656a",
                             fg="#071012" if active else "#d0dada",
                             activebackground="#c6d0cd", activeforeground="#071012",
                             relief="sunken" if active else "raised", bd=2,
                             highlightthickness=1, highlightbackground=CYAN if active else "#879295")
        self.list_heading.configure(text=f"{phase['name'].upper()} CHECKLIST")
        for child in self.tasks_frame.winfo_children(): child.destroy()
        if not self.expanded:
            resolved = set(checked) | set(skipped)
            message = "ALL TASKS COMPLETE" if tasks and len(checked) >= len(tasks) else "LIST CLEARED · SOME SKIPPED" if tasks and len(resolved) >= len(tasks) else "CHECKLIST COLLAPSED"
            self._label(self.tasks_frame, f"{message}   ·   PRESS ENTER TO OPEN", color=GREEN if tasks and len(checked) >= len(tasks) else AMBER if tasks and len(resolved) >= len(tasks) else MUTED, bg=PANEL, size=9).pack(anchor="w", padx=12, pady=18)
        elif not tasks:
            self._label(self.tasks_frame, "NO ITEMS CONFIGURED", color=MUTED, bg=PANEL, size=9).pack(anchor="w", padx=10, pady=15)
        for i, text in enumerate(tasks if self.expanded else []):
            done = i in checked
            skipped_item = i in skipped
            selected = self.nav_group == "tasks" and i == self.selected_row
            row = tk.Frame(self.tasks_frame, bg="#000000",
                           highlightthickness=1 if selected else 0,
                           highlightbackground=CYAN)
            row.pack(fill="x", pady=1)
            check = "✓" if done else "–" if skipped_item else " "
            fg = "#95ac9a" if done else AMBER if skipped_item else GREEN
            mark_color = GREEN if done else AMBER if skipped_item else "#669a73"
            self._label(row, f"[{check}]", color=mark_color, size=11, bold=True, bg=row["bg"]).pack(side="left", padx=(9, 10), pady=9)
            self._label(row, text.upper(), color=fg, size=9, bg=row["bg"], anchor="w").pack(side="left", fill="x", expand=True, pady=9)
            state_text = "COMPLETE" if done else "SKIPPED" if skipped_item else "STANDBY"
            state_color = GREEN if done else AMBER if skipped_item else "#71818a"
            self._label(row, state_text, color=state_color, size=7, bg=row["bg"]).pack(side="right", padx=9)
            row.bind("<Button-1>", lambda event, index=i: self._toggle(index))
            for child in row.winfo_children(): child.bind("<Button-1>", lambda event, index=i: self._toggle(index))
        count, skip_count, total = len(checked), len(skipped), len(tasks)
        remaining = max(0, total - count - skip_count)
        self.mode_readout.configure(text=mode.upper())
        self.progress_readout.configure(text=f"{count + skip_count:02d} / {total:02d}")
        self.today_readout.configure(text=self.day)
        self.phase_status.configure(text=phase["name"].upper())
        self.mode_status.configure(text=mode.upper())
        self.count_status.configure(text=f"{count:02d} DONE  {skip_count:02d} SKIP")
        self.remaining_label.configure(text=f"REMAINING {remaining:02d}")
        complete = total > 0 and remaining == 0
        all_done = complete and skip_count == 0
        self.complete_label.configure(text="PHASE COMPLETE" if all_done else "LIST CLEARED" if complete else "IN PROGRESS",
                                       fg=GREEN if all_done else AMBER)
        self.undo_button.configure(state="normal" if self.undo_stack else "disabled")
        self.dropdown_button.configure(text="▼" if self.expanded else "▶",
                                       relief="sunken" if self.expanded else "raised")
        self.date_label.configure(text=datetime.now().strftime("%a %b %d").upper())
        self._save()

    def _save(self):
        try:
            STATE_PATH.write_text(json.dumps({"day": self.day, "phase": self._active_phase()["id"],
                "mode": self.modes[self.mode_index], "checks": self.checks, "skips": self.skips,
                "expanded": self.expanded}, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _choose_phase(self, index):
        self.phase_index = index; self.selected_row = 0; self.nav_group = "phases"; self._open_unfinished(); self._draw()
    def _choose_mode(self, index):
        self.mode_index = index; self.selected_row = 0; self.nav_group = "modes"; self._open_unfinished(); self._draw()
    def _open_unfinished(self):
        tasks = self._items()
        resolved = set(self.checks.get(self._key(), [])) | set(self.skips.get(self._key(), []))
        self.expanded = not (tasks and len(resolved) >= len(tasks))
    def _toggle_dropdown(self):
        self.expanded = not self.expanded
        self._draw()
    def _toggle(self, index=None):
        tasks = self._items()
        if not tasks: return
        if index is not None: self.selected_row = index
        self.selected_row = max(0, min(self.selected_row, len(tasks)-1))
        key = self._key()
        checked, skipped = self.checks.get(key, []), self.skips.get(key, [])
        self._remember_undo(key)
        was_checked = self.selected_row in checked
        if was_checked:
            self.checks[key] = [i for i in checked if i != self.selected_row]
        else:
            self.checks[key] = sorted(checked + [self.selected_row])
            self.skips[key] = [i for i in skipped if i != self.selected_row]
            self._advance_after_action(tasks)
        self._close_if_resolved(tasks, key)
        self.nav_group = "tasks"; self._draw()
    def _remember_undo(self, key):
        self.undo_stack.append({"key": key, "checks": list(self.checks.get(key, [])),
                                "skips": list(self.skips.get(key, [])),
                                "cursor": self.selected_row, "expanded": self.expanded})
        self.undo_stack = self.undo_stack[-30:]
    def _advance_after_action(self, tasks):
        resolved = set(self.checks.get(self._key(), [])) | set(self.skips.get(self._key(), []))
        following = next((i for i in range(self.selected_row + 1, len(tasks)) if i not in resolved), None)
        if following is None:
            following = next((i for i in range(self.selected_row) if i not in resolved), self.selected_row)
        self.selected_row = following
    def _close_if_resolved(self, tasks, key):
        resolved = set(self.checks.get(key, [])) | set(self.skips.get(key, []))
        self.expanded = not (tasks and len(resolved) >= len(tasks))
    def _skip(self, _event=None):
        tasks = self._items()
        if not tasks: return "break"
        self.selected_row = max(0, min(self.selected_row, len(tasks)-1))
        key = self._key()
        checked, skipped = self.checks.get(key, []), self.skips.get(key, [])
        if self.selected_row not in skipped:
            self._remember_undo(key)
            self.checks[key] = [i for i in checked if i != self.selected_row]
            self.skips[key] = sorted(skipped + [self.selected_row])
            self._advance_after_action(tasks)
            self._close_if_resolved(tasks, key)
            self.nav_group = "tasks"
            self._draw()
        return "break"
    def _undo(self, _event=None):
        if not self.undo_stack: return "break"
        previous = self.undo_stack.pop()
        key = previous["key"]
        self.checks[key], self.skips[key] = previous["checks"], previous["skips"]
        self.selected_row, self.expanded = previous["cursor"], previous["expanded"]
        self.nav_group = "tasks"
        self._draw()
        return "break"
    def _move(self, delta):
        if self.nav_group == "phases": self._choose_phase((self.phase_index + delta) % len(self.phases)); return
        if self.nav_group == "modes": self._choose_mode((self.mode_index + delta) % len(self.modes)); return
        if not self.expanded: self.expanded = True
        self.selected_row = max(0, min(max(0, len(self._items())-1), self.selected_row + delta)); self._draw()
    def _horizontal(self, delta):
        if self.nav_group == "modes": self._choose_mode((self.mode_index + delta) % len(self.modes))
        else: self._choose_phase((self.phase_index + delta) % len(self.phases))
    def _enter(self, _event=None):
        if self.nav_group == "phases": self.nav_group = "modes"
        elif self.nav_group == "modes": self.nav_group = "tasks"
        elif not self.expanded: self.expanded = True; self._draw(); return "break"
        else: self._toggle(); return "break"
        self._draw(); return "break"
    def _tab(self, _event=None):
        self.nav_group = {"phases":"modes", "modes":"tasks", "tasks":"phases"}[self.nav_group]
        self._draw(); return "break"
    def _shift_tab(self, _event=None):
        self.nav_group = {"phases":"tasks", "modes":"phases", "tasks":"modes"}[self.nav_group]
        self._draw(); return "break"
    def _tick(self):
        now = date.today().isoformat()
        if now != self.day:
            self.day, self.checks, self.skips = now, {}, {}
            self.undo_stack.clear()
            self.expanded = True
        self.clock_label.configure(text=datetime.now().strftime("%H:%M"))
        self.date_label.configure(text=datetime.now().strftime("%a %b %d").upper())
        self._draw()
        self.root.after(15000, self._tick)


def main():
    root = tk.Tk()
    try:
        ChecklistApp(root)
    except (KeyError, TypeError, ValueError) as exc:
        messagebox.showerror("Invalid config.json", f"Could not read checklist configuration:\n{exc}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
