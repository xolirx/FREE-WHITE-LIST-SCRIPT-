#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import base64
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

SOURCES = {
    "WHITE_LIST_1": {
        "url": "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        "filename": "XOLIRX-WHITE-LIST-1.txt",
        "title": "XOLIRX WHITE LIST 🤍",
        "announce": "XOLIRX WHITE LIST 🤍 — безлимит, обновляется каждый час",
    },
    "WHITE_LIST_2": {
        "url": "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-all.txt",
        "filename": "XOLIRX-WHITE-LIST-2.txt",
        "title": "XOLIRX WHITE LIST 2 🤍",
        "announce": "XOLIRX WHITE LIST 2 🤍 — безлимит, обновляется каждый час",
    },
}

REPO_DIR = Path(__file__).parent.resolve()
UPDATE_INTERVAL = 3600
TIMEZONE = timezone(timedelta(hours=3))

TOTAL_BYTES = 1099511627776
EXPIRE_UNIX = 4102444800

GIT_BRANCH_FALLBACK = "main"


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"


def setup_logger():
    logger = logging.getLogger("xolirx")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


log = setup_logger()


def banner():
    print(f"""{Colors.CYAN}{Colors.BOLD}
    ╔══════════════════════════════════════════════╗
    ║   XOLIRX WHITE LIST  🤍  —  автообновление   ║
    ║        Happ · Provider · Subscription        ║
    ╚══════════════════════════════════════════════╝
    {Colors.RESET}""")


def ts():
    return datetime.now(TIMEZONE).strftime("%H:%M:%S")


def info(msg):
    print(f"{Colors.DIM}[{ts()}]{Colors.RESET} {Colors.CYAN}ℹ{Colors.RESET}  {msg}")


def ok(msg):
    print(f"{Colors.DIM}[{ts()}]{Colors.RESET} {Colors.GREEN}✔{Colors.RESET}  {msg}")


def warn(msg):
    print(f"{Colors.DIM}[{ts()}]{Colors.RESET} {Colors.YELLOW}⚠{Colors.RESET}  {msg}")


def err(msg):
    print(f"{Colors.DIM}[{ts()}]{Colors.RESET} {Colors.RED}✘{Colors.RESET}  {msg}")


def fetch(url, retries=3, timeout=30):
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "XOLIRX-WhiteList/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            return data.decode("utf-8", errors="replace")
        except (URLError, HTTPError, TimeoutError, OSError) as e:
            last_exc = e
            warn(f"Попытка {attempt}/{retries} — {e}")
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Не удалось скачать {url}: {last_exc}")


def b64_utf8(text):
    safe = text.replace("\r", " ").replace("\n", " ").strip()
    return base64.b64encode(safe.encode("utf-8")).decode("ascii")


def strip_headers(raw):
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        lines.append(s)
    return "\n".join(lines)


def build_subscription(body, title, provider_source, announce_text):
    now = datetime.now(TIMEZONE).strftime("%Y-%m-%d / %H:%M (Moscow)")
    link_count = len([l for l in body.splitlines() if l.strip()])
    announce_b64 = b64_utf8(announce_text)

    headers = [
        f"# profile-title: {title}",
        "# profile-update-interval: 1",
        f"# subscription-userinfo: upload=0; download=0; total={TOTAL_BYTES}; expire={EXPIRE_UNIX}",
        f"# announce: base64:{announce_b64}",
        f"# Date/Time: {now}",
        f"# Count: {link_count}",
        f"# Source: {provider_source}",
        "# Provider: XOLIRX WHITE LIST 🤍",
        "# profile-web-page-url: https://github.com/xolirx/FREE-WHITE-LIST-SCRIPT-",
        "",
    ]
    return "\n".join(headers) + body + "\n"


def write_file(path, content):
    if path.exists():
        old = path.read_text(encoding="utf-8", errors="replace")
        if old == content:
            return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return True


def run_git(*args, check=True):
    return subprocess.run(
        ["git", *args],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=check,
    )


def get_current_branch():
    try:
        r = run_git("rev-parse", "--abbrev-ref", "HEAD")
        branch = r.stdout.strip()
        if branch and branch != "HEAD":
            return branch
    except subprocess.CalledProcessError:
        pass
    return GIT_BRANCH_FALLBACK


def git_commit_and_push(changed_files):
    if not changed_files:
        return False

    try:
        run_git("rev-parse", "--is-inside-work-tree")
    except subprocess.CalledProcessError:
        warn("Это не git-репозиторий — пуш пропущен")
        return False

    try:
        run_git("add", *changed_files)

        diff = run_git("diff", "--cached", "--quiet", check=False)
        if diff.returncode == 0:
            info("Нет изменений для коммита")
            return False

        stamp = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S MSK")
        run_git("commit", "-m", f"🤍 Auto-update: {stamp}")

        branch = get_current_branch()

        try:
            run_git("fetch", "origin", branch, check=False)
            run_git("pull", "--rebase", "--autostash", "origin", branch, check=False)

            run_git("push", "origin", f"HEAD:{branch}")
            ok(f"Запушено в origin/{branch} — {stamp}")
            return True
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            err(f"Ошибка push: {stderr}")
            return False

    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        err(f"Git error: {stderr}")
        return False


def update_all():
    updated = []
    failed = 0

    for key, cfg in SOURCES.items():
        info(f"Скачиваю {cfg['title']} …")
        try:
            raw = fetch(cfg["url"])
            body = strip_headers(raw)
            if not body:
                raise RuntimeError("Источник пустой после очистки заголовков")

            content = build_subscription(
                body,
                cfg["title"],
                cfg["url"],
                cfg["announce"],
            )
            path = REPO_DIR / cfg["filename"]

            if write_file(path, content):
                count = len([l for l in body.splitlines() if l.strip()])
                ok(f"{cfg['filename']} обновлён ({count} серверов)")
                updated.append(cfg["filename"])
            else:
                info(f"{cfg['filename']} без изменений")
        except Exception as e:
            failed += 1
            err(f"Ошибка {key}: {e}")

    if updated:
        git_commit_and_push(updated)
    else:
        info("Все файлы актуальны — пуш не требуется")

    return failed


def main():
    banner()

    if not (REPO_DIR / ".git").exists():
        warn(f"Папка {REPO_DIR} не является git-репозиторием.")
        warn("Скрипт будет только обновлять файлы локально, без пуша.")
        print()

    info(f"Рабочая папка: {REPO_DIR}")
    info(f"Интервал обновления: {UPDATE_INTERVAL // 60} мин")
    print()

    iteration = 0
    try:
        while True:
            iteration += 1
            print(f"{Colors.BOLD}{Colors.MAGENTA}── Цикл #{iteration} ─────────────"
                  f"─────────────────{Colors.RESET}")

            try:
                failed = update_all()
                if failed:
                    warn(f"Завершено с {failed} ошибками")
                else:
                    ok("Цикл завершён успешно")
            except Exception as e:
                err(f"Критическая ошибка цикла: {e}")

            next_run = datetime.now(TIMEZONE) + timedelta(seconds=UPDATE_INTERVAL)
            print()
            info(f"Следующее обновление в {next_run.strftime('%H:%M:%S')} MSK")
            print()

            try:
                time.sleep(UPDATE_INTERVAL)
            except KeyboardInterrupt:
                raise

    except KeyboardInterrupt:
        print()
        warn("Остановлено пользователем (Ctrl+C)")
        sys.exit(0)


if __name__ == "__main__":
    main()