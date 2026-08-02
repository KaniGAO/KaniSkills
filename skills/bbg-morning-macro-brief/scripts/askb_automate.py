#!/usr/bin/env python3
"""
askb_automate.py — optional helper to drive Bloomberg ASKB headlessly.

Flow: detect the ASKB window -> paste the consolidated workflow prompt ->
wait for ASKB to finish -> screenshot/read the answer -> save to
input/bbg_paste.txt.

REQUIREMENTS (only if you actually use this):
    pip install pyautogui pytesseract
    # macOS also needs:  brew install tesseract
    # Windows:           the Terminal is a Windows GUI app

This script is OPTIONAL. The primary workflow is to paste the prompt from
references/bbg_askb_workflow.md into ASKB manually and copy the reply yourself.

Run:  python scripts/askb_automate.py
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PROMPT_PATH = os.path.join(SKILL_ROOT, "references", "bbg_askb_workflow.md")
OUT_PATH = os.path.join(SKILL_ROOT, "input", "bbg_paste.txt")

# The consolidated prompt sits between the "▼ COPY" and "▲ END COPY" markers.
def load_prompt() -> str:
    txt = open(PROMPT_PATH, encoding="utf-8").read()
    start = txt.find("▼ COPY")
    end = txt.find("▲ END COPY")
    if start == -1 or end == -1:
        raise RuntimeError("markers not found in bbg_askb_workflow.md")
    block = txt[start:end]
    # strip the marker lines themselves
    lines = block.splitlines()
    lines = lines[1:-1]
    return "\n".join(lines).strip()


def capture() -> str:
    """Drive ASKB headlessly and save the answer to input/bbg_paste.txt.

    Returns the output path. Raises RuntimeError if automation deps are missing
    or the clipboard read fails (in which case a screenshot fallback is used).
    """
    try:
        import pyautogui
    except ImportError:
        raise RuntimeError(
            "pyautogui not installed. Run: pip install pyautogui pyperclip")

    prompt = load_prompt()
    print("Prompt loaded (%d chars). Switch to the Bloomberg ASKB window NOW."
          % len(prompt))
    for i in range(5, 0, -1):
        print("   pasting in %d..." % i)
        time.sleep(1)

    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(prompt, interval=0.001)
    pyautogui.press("enter")
    print("Prompt sent. Waiting for ASKB to finish (90s)...")
    time.sleep(90)

    # Read back: copy the ASKB answer to clipboard via Ctrl+A / Ctrl+C, then
    # rely on pyperclip; fall back to a screenshot if clipboard is empty.
    try:
        import pyperclip
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "c")
        time.sleep(2)
        answer = pyperclip.paste()
    except Exception:
        answer = ""

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    if not answer.strip():
        # Screenshot fallback — you read it manually and paste into bbg_paste.txt
        shot = os.path.join(SKILL_ROOT, "input", "askb_screenshot.png")
        pyautogui.screenshot(shot)
        msg = ("Clipboard empty — saved screenshot to %s. Paste the text into %s"
               % (shot, OUT_PATH))
        print(msg)
        raise RuntimeError(msg)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(answer)
    print("Saved ASKB answer -> %s (%d chars)" % (OUT_PATH, len(answer)))
    return OUT_PATH


def main():
    capture()


if __name__ == "__main__":
    main()
