import re, csv
from pathlib import Path
from bs4 import BeautifulSoup
from common import get_page_html

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

def slugify(title: str):
    return title.strip().replace(" ", "_")

def parse_infobox(html: str):
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one(".portable-infobox, .infobox")  # fandom infobox
    out = {}
    if not box:
        return out
    # başlık
    title = box.select_one(".pi-title, .infobox-title")
    if title:
        out["name"] = title.get_text(strip=True)
    # satırlar
    for row in box.select(".pi-item, .infobox-item"):
        label = row.select_one(".pi-data-label, .infobox-header")
        value = row.select_one(".pi-data-value, .infobox-data")
        if not label or not value:
            continue
        key = re.sub(r"[^a-z0-9_]+", "_", label.get_text(strip=True).lower())
        val = " ".join(value.get_text(" ", strip=True).split())
        out[key] = val
    return out

def extract_traits_skills(html: str):
    soup = BeautifulSoup(html, "lxml")
    traits = []
    skills = {}
    for h in soup.select("h2, h3"):
        head = h.get_text(" ", strip=True).lower()
        if "trait" in head:
            ul = h.find_next("ul")
            if ul:
                for li in ul.select("li"):
                    t = li.get_text(" ", strip=True)
                    if t:
                        traits.append(t)
        if "skill" in head:
            table = h.find_next("table")
            if table:
                for tr in table.select("tr"):
                    tds = [td.get_text(" ", strip=True) for td in tr.select("td")]
                    if len(tds) >= 2:
                        skill_key = re.sub(r"[^a-z0-9_]+", "_", tds[0].lower())
                        try:
                            val = int(re.findall(r"\d+", tds[1])[0])
                        except Exception:
                            val = None
                        skills[skill_key] = val
    return traits, skills

def main():
    lords_list = (ROOT / "lords_list.txt").read_text(encoding="utf-8").splitlines()
    rows_lords, rows_traits, rows_skills = [], [], []

    for title in filter(None, lords_list):
        html = get_page_html(title)
        info = parse_infobox(html)
        traits, skills = extract_traits_skills(html)

        ext_id = slugify(title)
        row = {
            "ext_id": ext_id,
            "name": info.get("name") or title.replace("_"," "),
            "gender": info.get("gender"),
            "age": int(re.findall(r"\d+", info.get("age",""))[0]) if info.get("age") and re.findall(r"\d+", info.get("age","")) else None,
            "culture_id": None,   # 2. hafta maplenecek
            "level": int(re.findall(r"\d+", info.get("level",""))[0]) if info.get("level") and re.findall(r"\d+", info.get("level","")) else None,
            "sp_per_lvl": None,
            "sum_stats": None,
            "traits": "; ".join(traits[:20]),
            "source_url": f"https://mountandblade.fandom.com/wiki/{ext_id}"
        }
        rows_lords.append(row)

        for t in traits:
            rows_traits.append({"ext_id": ext_id, "trait": t})

        for sk, val in skills.items():
            rows_skills.append({"ext_id": ext_id, "skill_key": sk, "value": val})

    # yaz
    if rows_lords:
        with open(PROC/"lords.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows_lords[0].keys()))
            w.writeheader(); w.writerows(rows_lords)

    if rows_traits:
        with open(PROC/"lord_traits.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ext_id","trait"])
            w.writeheader(); w.writerows(rows_traits)

    if rows_skills:
        with open(PROC/"lord_skills.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ext_id","skill_key","value"])
            w.writeheader(); w.writerows(rows_skills)

if __name__ == "__main__":
    main()
