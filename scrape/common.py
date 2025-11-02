import os, time, json, hashlib
from pathlib import Path
import requests

BASE = "https://mountandblade.fandom.com"
API  = f"{BASE}/api.php"

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "GoodFellas-DB/1.0 (contact: team@example.com)"}

def cache_path(key: str) -> Path:
    h = hashlib.sha1(key.encode()).hexdigest()
    return RAW_DIR / f"{h}.json"

def get_json(params: dict, sleep=1.2):
    params = {**params, "format": "json"}
    key = API + "?" + "&".join(f"{k}={v}" for k,v in sorted(params.items()))
    cp = cache_path(key)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    resp = requests.get(API, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    cp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(sleep)  # saygılı gecikme
    return data

def get_page_html(title: str):
    # MediaWiki parse API: HTML döndürür
    data = get_json({
        "action": "parse",
        "page": title,
        "prop": "text|links|categories",
        "redirects": "1"
    })
    html = data.get("parse", {}).get("text", {}).get("*", "")
    return html
