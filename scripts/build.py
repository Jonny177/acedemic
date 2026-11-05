"""Build the academic archive with Python's standard library only."""

from datetime import date
from html import escape
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site"
STATIC = ROOT / "static"


def text(value):
    return escape(str(value), quote=True)


def display_date(value):
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {parsed.strftime('%B')} {parsed.year}"


def load_data():
    profile = json.loads((ROOT / "data/profile.json").read_text(encoding="utf-8"))
    drafts = json.loads((ROOT / "data/drafts.json").read_text(encoding="utf-8"))
    required = ("name", "role", "institution", "advisor", "email", "bio", "updated")
    for field in required:
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            raise ValueError(f"Missing profile field: {field}")
    seen = set()
    for draft in drafts:
        slug = draft["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
            raise ValueError(f"Invalid or duplicate draft slug: {slug}")
        seen.add(slug)
        for field in ("title", "short_title", "summary", "status", "added"):
            if not isinstance(draft.get(field), str) or not draft[field].strip():
                raise ValueError(f"Missing {field} in {slug}")
        if not isinstance(draft.get("tags"), list) or not draft["tags"]:
            raise ValueError(f"Missing tags in {slug}")
        if not isinstance(draft.get("pages"), int) or draft["pages"] < 1:
            raise ValueError(f"Invalid page count in {slug}")
        for field, extension in (("pdf", ".pdf"), ("tex", ".tex")):
            resource = (STATIC / draft[field]).resolve()
            if not resource.is_relative_to(STATIC.resolve()) or resource.suffix != extension:
                raise ValueError(f"Invalid {field} path in {slug}")
            if not resource.is_file():
                raise FileNotFoundError(resource)
        display_date(draft["added"])
    return profile, drafts


def notice():
    return '''<aside class="draft-notice" aria-label="Status of the manuscripts">
      <p class="notice-label">AI-generated working drafts</p>
      <p>These manuscripts are shared as exploratory working drafts.
      They are not presented as verified results.</p>
    </aside>'''


def document(profile, title, description, content, prefix="", kind="home", archive=False):
    name_tag = "h1" if kind == "home" else "div"
    home_current = ' aria-current="page"' if kind == "home" else ""
    archive_current = ' aria-current="page"' if kind == "archive" else ""
    script = f'<script src="{prefix}assets/archive.js" defer></script>' if archive else ""
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{text(description)}">
  <meta name="theme-color" content="#faf9f6">
  <title>{text(title)}</title>
  <link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{prefix}assets/styles.css">
  {script}
</head>
<body class="{kind}-page">
  <a class="skip-link" href="#main-content">Skip to content</a>
  <header class="site-header container">
    <div class="header-top">
      <{name_tag} class="site-name"><a href="{prefix}index.html">{text(profile['name'])}</a></{name_tag}>
      <a class="home-link" href="{text(profile['main_homepage'])}">Main homepage <span aria-hidden="true">↗</span></a>
    </div>
    <p class="site-subtitle">{text(profile['role'])} · {text(profile['institution'])}</p>
    <nav class="site-nav" aria-label="Main navigation">
      <a href="{prefix}index.html"{home_current}>Profile</a>
      <a href="{prefix}drafts/index.html"{archive_current}>Working drafts</a>
      <a href="{prefix}index.html#teaching">Teaching</a>
      <a href="{prefix}index.html#contact">Contact</a>
    </nav>
  </header>
  <main id="main-content" class="container">
    {content}
  </main>
  <footer class="site-footer container">
    <span>Maintained by {text(profile['name'])}</span>
    <span>Updated {text(display_date(profile['updated']))} · <a href="{text(profile['github'])}">GitHub</a></span>
  </footer>
</body>
</html>
'''


def tags(draft):
    return '<div class="tags" aria-label="Topics">' + "".join(
        f'<span class="tag">{text(tag)}</span>' for tag in draft["tags"]
    ) + "</div>"


def draft_entry(draft, prefix="", searchable=False):
    data = ""
    if searchable:
        searchable_text = " ".join([draft["title"], draft["summary"], *draft["tags"]])
        data = f' data-draft data-search-text="{text(searchable_text)}" data-tags="{text("|".join(draft["tags"]))}"'
    return f'''<article class="draft-entry"{data}>
      <h3 class="draft-title"><a href="{prefix}drafts/{text(draft['slug'])}/index.html">{text(draft['title'])}</a></h3>
      <p class="draft-meta">{text(draft['status'])} · {draft['pages']} pages</p>
      <p class="draft-summary">{text(draft['summary'])}</p>
      {tags(draft)}
      <p class="entry-links">
        <a href="{prefix}drafts/{text(draft['slug'])}/index.html">Details</a>
        <a href="{prefix}{text(draft['pdf'])}">PDF</a>
        <a href="{prefix}{text(draft['tex'])}" download>LaTeX source</a>
      </p>
    </article>'''


def home(profile, drafts):
    interests = "".join(f"<li>{text(item)}</li>" for item in profile["research_interests"])
    teaching = "".join(
        f'''<li><strong>{text(item['role'])}</strong>, {text(item['institution'])}<br>
        <em>{text(item['course'])}</em><br>
        <span class="muted">Academic years {text(' and '.join(item['academic_years']))}</span></li>'''
        for item in profile["teaching"]
    )
    content = f'''<section id="about" class="intro" aria-labelledby="about-heading">
      <h2 id="about-heading" class="section-heading">About</h2>
      <p>{text(profile['bio'])}</p>
      <dl class="profile-meta">
        <div><dt>Advisor</dt><dd>{text(profile['advisor'])}</dd></div>
        <div><dt>Email</dt><dd><a href="mailto:{text(profile['email'])}">{text(profile['email'])}</a></dd></div>
      </dl>
    </section>
    <section id="research" aria-labelledby="research-heading">
      <h2 id="research-heading" class="section-heading">Research interests</h2>
      <ul>{interests}</ul>
      <p>{text(profile['research_overview'])}</p>
    </section>
    <section id="working-drafts" aria-labelledby="drafts-heading">
      <h2 id="drafts-heading" class="section-heading">Working drafts <span class="muted">({len(drafts)})</span></h2>
      <p class="section-intro">Draft manuscripts on nodal geometry and quantitative unique continuation.</p>
      {notice()}
      <div class="draft-list">{''.join(draft_entry(draft) for draft in drafts)}</div>
      <p class="section-link"><a href="drafts/index.html">Browse and search all drafts <span aria-hidden="true">→</span></a></p>
    </section>
    <section id="teaching" aria-labelledby="teaching-heading">
      <h2 id="teaching-heading" class="section-heading">Teaching</h2>
      <ul class="teaching-list">{teaching}</ul>
    </section>
    <section id="contact" aria-labelledby="contact-heading">
      <h2 id="contact-heading" class="section-heading">Contact</h2>
      <p><a href="mailto:{text(profile['email'])}">{text(profile['email'])}</a><br>
      {text(profile['institution'])}</p>
      <p><a href="{text(profile['github'])}">GitHub</a> · <a href="{text(profile['main_homepage'])}">Main homepage</a></p>
    </section>'''
    return document(profile, f"{profile['name']} — Mathematics", "Academic profile, research interests, and AI-generated working drafts in partial differential equations and geometric analysis.", content)


def archive(profile, drafts):
    all_tags = sorted({tag for draft in drafts for tag in draft["tags"]})
    options = "".join(f'<option value="{text(tag)}">{text(tag)}</option>' for tag in all_tags)
    content = f'''<p class="breadcrumb"><a href="../index.html">Profile</a> / Working drafts</p>
    <h1 class="page-title">Working drafts</h1>
    <p class="section-intro">An archive of {len(drafts)} exploratory manuscripts. Search by title, topic, or summary.</p>
    {notice()}
    <form class="archive-tools" data-filters role="search" hidden>
      <div class="filter-field"><label for="draft-search">Search drafts</label>
      <input id="draft-search" type="search" data-search placeholder="e.g. nodal curves or biharmonic" autocomplete="off"></div>
      <div class="filter-field"><label for="draft-topic">Topic</label>
      <select id="draft-topic" data-tag-filter><option value="">All topics</option>{options}</select></div>
      <button type="button" data-reset>Reset</button>
    </form>
    <noscript><p>All drafts are listed below. Search and topic filtering require JavaScript.</p></noscript>
    <p class="results-count" data-count aria-live="polite" aria-atomic="true">{len(drafts)} drafts</p>
    <div class="draft-list">{''.join(draft_entry(draft, '../', True) for draft in drafts)}</div>
    <p class="empty-state" data-empty hidden>No drafts match this search. Try a different term or reset the filters.</p>
    <p class="back-link"><a href="../index.html">← Back to profile</a></p>'''
    return document(profile, f"Working drafts — {profile['name']}", "Search AI-generated exploratory drafts on biharmonic equations, vanishing order, Landis estimates, and parabolic nodal curves.", content, "../", "archive", True)


def detail(profile, draft):
    author = draft.get("author") or "Not specified in the supplied manuscript"
    manuscript_date = draft.get("manuscript_date") or "Not specified in the supplied manuscript"
    points = "".join(f"<li>{text(point)}</li>" for point in draft["focus_points"])
    pdf_size = (STATIC / draft["pdf"]).stat().st_size
    content = f'''<p class="breadcrumb"><a href="../../index.html">Profile</a> / <a href="../index.html">Working drafts</a></p>
    <h1 class="page-title">{text(draft['title'])}</h1>
    <p class="draft-meta">{text(draft['status'])} · {draft['pages']} pages</p>
    {notice()}
    <div class="detail-layout">
      <div class="detail-main">
        <section aria-labelledby="summary-heading">
          <h2 id="summary-heading" class="section-heading">About this draft</h2>
          <p>{text(draft['summary'])}</p>
          <ul>{points}</ul>
          {tags(draft)}
        </section>
        <section aria-labelledby="files-heading">
          <h2 id="files-heading" class="section-heading">Manuscript files</h2>
          <p class="download-links">
            <a href="../../{text(draft['pdf'])}">Read PDF</a>
            <a href="../../{text(draft['pdf'])}" download>Download PDF</a>
            <a href="../../{text(draft['tex'])}" download>Download LaTeX source</a>
          </p>
          <p class="muted">The PDF and LaTeX source are reproduced as supplied. The descriptions on this site summarize their subject matter; they do not certify the mathematical claims.</p>
        </section>
      </div>
      <aside class="detail-aside" aria-labelledby="record-heading">
        <h2 id="record-heading" class="section-heading">Record</h2>
        <dl class="document-meta">
          <div><dt>Status</dt><dd>{text(draft['status'])}</dd></div>
          <div><dt>Author</dt><dd>{text(author)}</dd></div>
          <div><dt>Manuscript date</dt><dd>{text(manuscript_date)}</dd></div>
          <div><dt>Added to this archive</dt><dd><time datetime="{text(draft['added'])}">{text(display_date(draft['added']))}</time></dd></div>
          <div><dt>Length</dt><dd>{draft['pages']} pages</dd></div>
          <div><dt>PDF size</dt><dd>{round(pdf_size / 1024)} KB</dd></div>
        </dl>
      </aside>
    </div>
    <p class="back-link"><a href="../index.html">← All working drafts</a></p>'''
    return document(profile, f"{draft['title']} — {profile['name']}", draft["summary"], content, "../../", "detail")


def write_page(path, markup):
    destination = OUT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markup, encoding="utf-8", newline="\n")


def main():
    profile, drafts = load_data()
    OUT.mkdir(exist_ok=True)
    # Only known generated HTML files are pruned; no recursive deletion is used.
    for old_page in (OUT / "drafts").glob("*/index.html"):
        if old_page.parent.name not in {draft["slug"] for draft in drafts}:
            old_page.unlink()
    shutil.copytree(STATIC, OUT, dirs_exist_ok=True)
    (OUT / ".nojekyll").touch()
    write_page("index.html", home(profile, drafts))
    write_page("drafts/index.html", archive(profile, drafts))
    for draft in drafts:
        write_page(f"drafts/{draft['slug']}/index.html", detail(profile, draft))
    print(f"Built {len(drafts) + 2} pages and copied manuscript files to {OUT}")


if __name__ == "__main__":
    main()
