#!/usr/bin/env python3
"""
Regenerates ShipVault's homepage app grid + stats + sitemap.xml from the
tracker's progress.json, so the shipped site always has real, crawlable
HTML instead of depending on a client-side fetch for its core content.

Usage: python3 bake.py
Run this from the hub project root before every `vercel --prod` deploy.
"""
import json
import re
import urllib.request

TRACKER_URL = "https://raw.githubusercontent.com/ProfessorInfluence/thirty-day-webapp-challenge/main/progress.json"
SITE_URL = "https://shipvault.vercel.app"

# slug overrides for apps whose kebab-case name doesn't match their repo/page slug
SLUG_OVERRIDES = {
    "StreakForge": "streakforge",
    "InvoiceSnap": "invoicesnap",
    "QRStudio": "qrstudio",
}


def slugify(name):
    if name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[name]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def card_html(app, has_page):
    live = app["status"] == "done"
    slug = slugify(app["name"])
    title_html = f'<a href="/apps/{slug}">{app["name"]}</a>' if (live and has_page) else app["name"]
    actions = ""
    if live:
        actions = (
            '<div class="card-actions">'
            f'<a class="a-try" href="{app["live_url"]}" target="_blank" rel="noopener">Try free</a>'
            f'<a class="a-buy" href="{app.get("stripe_payment_link","#")}" target="_blank" rel="noopener">'
            f'Pro ${app["price_usd"]}{"/mo" if app.get("billing")=="monthly" else ""}</a>'
            "</div>"
        )
    return f'''<div class="card {"live" if live else "pending"}" data-day="{app["day"]}">
      <div class="card-top">
        <span class="day-badge">DAY {app["day"]}</span>
        <span class="{"status-live" if live else "status-pending"}">{"LIVE" if live else "COMING SOON"}</span>
      </div>
      <h3>{title_html}</h3>
      <div class="idea">{app["idea"]}</div>
      {actions}
    </div>'''


def main():
    with urllib.request.urlopen(TRACKER_URL) as r:
        data = json.load(r)
    apps = sorted(data["apps"], key=lambda a: a["day"])
    live_count = sum(1 for a in apps if a["status"] == "done")

    # which live apps already have a dedicated static page in apps/
    import os
    pages_dir = os.path.join(os.path.dirname(__file__), "apps")
    existing_pages = set()
    if os.path.isdir(pages_dir):
        existing_pages = {f[:-5] for f in os.listdir(pages_dir) if f.endswith(".html") and not f.startswith("_")}

    cards = "\n".join(card_html(a, slugify(a["name"]) in existing_pages) for a in apps)

    template_path = os.path.join(os.path.dirname(__file__), "template.html")
    with open(template_path) as f:
        tpl = f.read()

    out = (
        tpl.replace("{{APP_CARDS}}", cards)
        .replace("{{LIVE_COUNT}}", str(live_count))
        .replace("{{TOTAL_COUNT}}", str(len(apps)))
    )
    out_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(out_path, "w") as f:
        f.write(out)
    print(f"Wrote {out_path} ({live_count}/{len(apps)} live)")

    # sitemap
    urls = [SITE_URL + "/"]
    for a in apps:
        if a["status"] == "done" and slugify(a["name"]) in existing_pages:
            urls.append(f"{SITE_URL}/apps/{slugify(a['name'])}")
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
        + "\n</urlset>\n"
    )
    sitemap_path = os.path.join(os.path.dirname(__file__), "sitemap.xml")
    with open(sitemap_path, "w") as f:
        f.write(sitemap)
    print(f"Wrote {sitemap_path} ({len(urls)} urls)")


if __name__ == "__main__":
    main()
