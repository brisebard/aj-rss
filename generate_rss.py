import json
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

API_URL = "https://ecran-total.fr/wp-json/wp/v2/job"
PER_PAGE = 100

ALLOWED_TYPES = {"types-job-cdi", "types-job-cdd"}
TYPE_LABELS = {
    "types-job-cdi": "CDI",
    "types-job-cdd": "CDD",
}

FEED_TITLE = "Ecran Total – Offres CDI / CDD"
FEED_LINK  = "https://ecran-total.fr/jobs/"
FEED_DESC  = "Offres d'emploi en CDI et CDD publiées sur Ecran Total"
FEED_URL   = "https://github.com"  # remplacé automatiquement, pas critique


def fetch_all_jobs():
    jobs = []
    page = 1
    while True:
        url = f"{API_URL}?per_page={PER_PAGE}&page={page}&status=publish"
        req = urllib.request.Request(url, headers={"User-Agent": "rss-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            data = json.loads(resp.read().decode("utf-8"))
        if not data:
            break
        jobs.extend(data)
        if page >= total_pages:
            break
        page += 1
    return jobs


def filter_jobs(jobs):
    items = []
    for job in jobs:
        classes = set(job.get("class_list", []))
        matched = classes & ALLOWED_TYPES
        if not matched:
            continue
        type_slug = next(iter(matched))
        label = TYPE_LABELS[type_slug]

        raw_title = job.get("title", {}).get("rendered", "Sans titre")
        # Décoder les entités HTML basiques
        raw_title = raw_title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#039;", "'").replace("&nbsp;", " ").strip()
        title = f"[{label}] {raw_title}"

        link = job.get("link", "")
        date_str = job.get("date_gmt") or job.get("date", "")
        if date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        else:
            pub_date = ""

        guid = job.get("guid", {}).get("rendered", link)

        items.append({"title": title, "link": link, "pubDate": pub_date, "guid": guid})
    return items


def build_rss(items):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{escape(FEED_TITLE)}</title>",
        f"    <link>{escape(FEED_LINK)}</link>",
        f"    <description>{escape(FEED_DESC)}</description>",
        "    <language>fr-FR</language>",
        f"    <lastBuildDate>{now}</lastBuildDate>",
    ]
    for item in items:
        lines += [
            "    <item>",
            f"      <title>{escape(item['title'])}</title>",
            f"      <link>{escape(item['link'])}</link>",
            f"      <pubDate>{escape(item['pubDate'])}</pubDate>",
            f'      <guid isPermaLink="false">{escape(item["guid"])}</guid>',
            "    </item>",
        ]
    lines += ["  </channel>", "</rss>"]
    return "\n".join(lines)


if __name__ == "__main__":
    print("Récupération des offres...")
    jobs = fetch_all_jobs()
    print(f"{len(jobs)} offres récupérées")
    items = filter_jobs(jobs)
    print(f"{len(items)} offres CDI/CDD retenues")
    rss = build_rss(items)
    with open("docs/rss.xml", "w", encoding="utf-8") as f:
        f.write(rss)
    print("docs/rss.xml généré avec succès")
