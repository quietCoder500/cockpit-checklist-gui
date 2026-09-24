# Daily Checklist

An offline, keyboard-first checklist GUI made with Python's standard-library Tkinter. It is designed to run on a small Linux computer without opening a web browser or using a network connection.

## Run on this PC

Install Python 3 with Tk support, then run:

```sh
python main.py
```

On Windows, `py main.py` may be used instead. No packages or network access are required.

## Run on Raspberry Pi OS

Install Tkinter if it is not already installed (`sudo apt install python3-tk`), copy this folder to the Pi, and run `python3 main.py` from its desktop session. The app is small and uses no browser engine.

## Change checklist content

Edit `config.json` in a text editor. Each phase contains separate task arrays for Great, Average, and Poor. The app reads this file at startup; restart the app after editing it. Keep the JSON syntax valid (double quotes and commas).

## Controls and saved data

- Arrow left/right: change phase; when the page selector is active, change brain-day page.
- Tab / Shift+Tab: move between phase, page, and task selection.
- Arrow up/down: move through the active selection or task list.
- Enter or Space: move into the next selection group or check/uncheck a task.
- S: skip the selected task for today; skipped items are shown separately from completed items.
- U: undo the last check or skip.
- You can also click a time-phase or brain-day key directly to switch immediately.
- The checklist dropdown closes when every task is complete or skipped; select its header arrow to open or close it.
- Click a phase/page button or task row to select it.

Selection, today's checks, and skips are saved locally in `~/.daily_checklist_state.json` (in the current user's home folder). Checks and skips clear automatically when the date changes. Undo applies during the current app session.
