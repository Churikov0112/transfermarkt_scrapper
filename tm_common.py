import json
import os
import random
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.transfermarkt.com"
NATIONAL_TEAMS_URL = "https://www.transfermarkt.com/statistik/weltrangliste"
DEFAULT_HTTP_TIMEOUT = float(os.getenv("TM_HTTP_TIMEOUT", "30"))
DEFAULT_HTTP_MAX_RETRIES = int(os.getenv("TM_HTTP_MAX_RETRIES", "5"))
DEFAULT_HTTP_BACKOFF_BASE = float(os.getenv("TM_HTTP_BACKOFF_BASE", "1.0"))
DEFAULT_HTTP_BACKOFF_MAX = float(os.getenv("TM_HTTP_BACKOFF_MAX", "20.0"))
DEFAULT_RETRY_STATUSES = {429, 500, 502, 503, 504}


def create_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return session


def _sleep_with_backoff(attempt, base_delay, max_delay):
    delay = min(max_delay, base_delay * (2 ** attempt))
    jitter = random.uniform(0, base_delay)
    time.sleep(delay + jitter)


def request_with_retries(
    session,
    method,
    url,
    *,
    timeout=DEFAULT_HTTP_TIMEOUT,
    max_retries=DEFAULT_HTTP_MAX_RETRIES,
    backoff_base=DEFAULT_HTTP_BACKOFF_BASE,
    backoff_max=DEFAULT_HTTP_BACKOFF_MAX,
    retry_statuses=DEFAULT_RETRY_STATUSES,
    **kwargs,
):
    last_exc = None
    for attempt in range(max_retries):
        try:
            response = session.request(method, url, timeout=timeout, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            if attempt >= max_retries - 1:
                raise
            _sleep_with_backoff(attempt, backoff_base, backoff_max)
            continue

        if response.status_code in retry_statuses and attempt < max_retries - 1:
            try:
                response.close()
            except Exception:
                pass
            _sleep_with_backoff(attempt, backoff_base, backoff_max)
            continue

        return response

    if last_exc:
        raise last_exc

    return response


def get_soup(session, url, timeout=DEFAULT_HTTP_TIMEOUT, max_retries=DEFAULT_HTTP_MAX_RETRIES):
    response = request_with_retries(session, "GET", url, timeout=timeout, max_retries=max_retries)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_json(session, url, timeout=DEFAULT_HTTP_TIMEOUT, max_retries=DEFAULT_HTTP_MAX_RETRIES, retry_statuses=None):
    statuses = DEFAULT_RETRY_STATUSES if retry_statuses is None else retry_statuses
    response = request_with_retries(
        session,
        "GET",
        url,
        timeout=timeout,
        max_retries=max_retries,
        retry_statuses=statuses,
    )
    response.raise_for_status()
    return response.json()


def extract_id_from_url(url, entity_type="player"):
    if not url:
        return None

    match = None
    if entity_type == "player":
        match = re.search(r"/spieler/(\d+)(?:$|\?)", url)
        if not match:
            match = re.search(r"/profil/spieler/(\d+)(?:$|\?)", url)
    elif entity_type in {"team", "club"}:
        match = re.search(r"/verein/(\d+)(?:$|/|\?)", url)

    return match.group(1) if match else None


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_absolute_url(url):
    if not url:
        return None
    if url.startswith("http"):
        return url
    return urljoin(BASE_URL, url)
