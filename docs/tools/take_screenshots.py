"""Capture README/PDF screenshots of the running app (documentation tooling only).

Requirements (not needed to run SettleUp itself):
    pip install playwright
It drives the Microsoft Edge that is already installed on Windows (channel="msedge"),
so no extra browser download is needed.

Usage, with the backend on :8000 (seeded) and the frontend on :5173 running:
    python docs/tools/take_screenshots.py
"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

API = "http://localhost:8000/api/v1"
WEB = "http://localhost:5173"
OUT = Path(__file__).resolve().parents[1] / "screenshots"
EMAIL, PASSWORD = "sarvesh@example.com", "Password@123"  # seed-script test account


def api(path, body=None, token=None):
    request = urllib.request.Request(f"{API}{path}", data=json.dumps(body).encode() if body else None)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    token = api("/auth/login", {"email": EMAIL, "password": PASSWORD})["access_token"]
    groups = api("/groups", token=token)
    room = next(g for g in groups if g["name"] == "Room 204")
    gid = room["id"]
    expense_id = api(f"/groups/{gid}/expenses?category=food", token=token)["items"][0]["id"]

    pages = [
        ("03_dashboard", "/dashboard"),
        ("04_groups", "/groups"),
        ("05_create_group", "/groups/new"),
        ("06_group_expenses", f"/groups/{gid}"),
        ("07_group_members", f"/groups/{gid}/members"),
        ("08_add_expense", f"/groups/{gid}/expenses/new"),
        ("09_expense_detail", f"/expenses/{expense_id}"),
        ("10_edit_expense", f"/expenses/{expense_id}/edit"),
        ("11_balances", f"/groups/{gid}/balances"),
        ("12_settle_up", f"/groups/{gid}/settle"),
        ("13_settlement_history", f"/groups/{gid}/settlements"),
        ("14_profile", "/profile"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")

        guest = browser.new_context(viewport={"width": 1440, "height": 900})
        page = guest.new_page()
        for name, path in (("01_login", "/login"), ("02_register", "/register")):
            page.goto(WEB + path, wait_until="networkidle")
            page.screenshot(path=OUT / f"{name}.png")
        guest.close()

        def logged_in_context(**kwargs):
            context = browser.new_context(**kwargs)
            context.add_init_script(f"localStorage.setItem('settleup_token', {json.dumps(token)})")
            return context

        desktop = logged_in_context(viewport={"width": 1440, "height": 900})
        page = desktop.new_page()
        for name, path in pages:
            page.goto(WEB + path, wait_until="networkidle")
            page.wait_for_timeout(400)
            page.screenshot(path=OUT / f"{name}.png", full_page=True)
            print("saved", name)
        desktop.close()

        mobile = logged_in_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True)
        page = mobile.new_page()
        for name, path in (("15_mobile_dashboard", "/dashboard"), ("16_mobile_group", f"/groups/{gid}")):
            page.goto(WEB + path, wait_until="networkidle")
            page.wait_for_timeout(400)
            page.screenshot(path=OUT / f"{name}.png")
            print("saved", name)
        mobile.close()
        browser.close()


if __name__ == "__main__":
    sys.exit(main())
