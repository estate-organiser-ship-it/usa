# post-queue

Scheduled blog posts for the usa site, waiting for their publish date.

**Nothing here is on the live website.** GitHub Pages builds from `main` only,
so every post in `posts/` returns 404 until `.github/workflows/drip-publish.yml`
copies it onto `main` on its date.

| File | What it is |
|---|---|
| `queue.json` | the schedule: one date and slug per post, plus the IndexNow key |
| `posts/<slug>/index.html` | the finished page, built and compliance checked |
| `sources/<slug>.md` | every claim in that post with its primary source |
| `scripts/drip_publish.py` | copies a due post onto main, updates the blog index and sitemap |
| `workflows/drip-publish.yml` | the install copy of the workflow (see below) |

## Schedule

- **2026-10-02** 09:00 Melbourne: `what-to-do-when-someone-dies`

## Changing the schedule

Edit `queue.json` on this branch and push. Nothing else needs to change. A date
in the past publishes on the next scheduled run.

## Publishing one early

Run the **Scheduled blog drip** workflow manually with `dry_run` unticked and
`force_slug` set to the slug.

## Installing the workflow

`workflows/drip-publish.yml` has to be copied to `.github/workflows/drip-publish.yml`
on `main` before any of this runs. It lives here because the token used to build
this branch lacks the GitHub `workflow` scope and cannot write to
`.github/workflows/`.
