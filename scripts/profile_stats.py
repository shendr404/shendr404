import os, json, urllib.request, datetime, html
from collections import Counter
from pathlib import Path

owner = os.environ["PROFILE_OWNER"]
headers = {"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
def api(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

query = """query($login:String!){user(login:$login){contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions totalPullRequestReviewContributions contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
result = api("https://api.github.com/graphql", {"query":query,"variables":{"login":owner}})
if result.get("errors"):
    raise RuntimeError(result["errors"])
c = result["data"]["user"]["contributionsCollection"]
days = [d for w in c["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
today = datetime.datetime.now(datetime.timezone.utc).date()
days = sorted((d for d in days if d["date"] <= today.isoformat()), key=lambda d:d["date"])
longest = current = 0
for d in days:
    current = current + 1 if d["contributionCount"] else 0
    longest = max(longest,current)
if days and days[-1]["date"] == today.isoformat() and not days[-1]["contributionCount"]:
    current = 0
    for d in reversed(days[:-1]):
        if not d["contributionCount"]: break
        current += 1
repos = []
page = 1
while True:
    batch = api(f"https://api.github.com/users/{owner}/repos?type=owner&per_page=100&page={page}")
    repos.extend(batch)
    if len(batch)<100: break
    page += 1
langs = Counter()
for repo in repos:
    if not repo["archived"] and repo["name"] != owner:
        langs.update(api(repo["languages_url"]))
total = sum(langs.values())
def make(theme):
    dark = theme == "dark"
    bg, fg, muted, border, accent = ("#0d1117","#e6edf3","#8b949e","#30363d","#39d5c5") if dark else ("#ffffff","#24292f","#57606a","#d0d7de","#087e8b")
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="840" height="365" viewBox="0 0 840 365" role="img"><title>GitHub activity and repository languages</title><rect x="1" y="1" width="838" height="363" rx="12" fill="{bg}" stroke="{border}"/>']
    def txt(x,y,value,size=15,color=fg):
        s.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}">{html.escape(str(value))}</text>')
    txt(24,32,"GitHub activity · last year",21,accent)
    metrics=[("Contributions",c["contributionCalendar"]["totalContributions"]),("Commits",c["totalCommitContributions"]),("Pull requests",c["totalPullRequestContributions"]),("Reviews",c["totalPullRequestReviewContributions"]),("Current streak",f"{current} days"),("Longest streak",f"{longest} days")]
    for i,(label,val) in enumerate(metrics):
        x=24+(i%3)*270; y=64+(i//3)*64
        txt(x,y,label,14,muted);txt(x,y+26,val,24)
    txt(24,202,"Repository languages · public, including forks",17,accent)
    colors=["#3572A5","#f1e05a","#3178c6","#f34b7d","#00ADD8","#89e051"]
    top=langs.most_common(5)
    if len(langs)>5: top.append(("Other",total-sum(v for _,v in top)))
    x=24
    for i,(name,v) in enumerate(top):
        width=792*v/total if total else 0
        s.append(f'<rect x="{x:.2f}" y="218" width="{width:.2f}" height="12" fill="{colors[i]}"/>')
        x+=width
        lx=24+(i%3)*270; ly=255+(i//3)*25
        txt(lx,ly,f"{name}: {v/total:.1%}",14)
    if not total: txt(24,255,"No language data available",14,muted)
    txt(24,330,"Public repository code composition, not individual authorship.",12,muted)
    txt(24,348,f"Updated {today.isoformat()} UTC · public repositories: {len(repos)}",12,muted)
    s.append("</svg>")
    Path(f"assets/activity-{theme}.svg").write_text("".join(s),encoding="utf-8")
for theme in ("dark","light"): make(theme)
