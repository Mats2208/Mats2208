"""Render the README's chart from public GitHub commit contributions."""

import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


USERNAME = "Mats2208"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "commit-activity.svg"
MONTH_NAMES = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def public_commits(months, now):
    fields = []
    for index, month in enumerate(months):
        next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
        first = f"{month}T00:00:00Z"
        last = min(f"{next_month - timedelta(days=1)}T23:59:59Z", now)
        fields.append(f'''
            month{index}: contributionsCollection(from: "{first}", to: "{last}") {{
                totalRepositoriesWithContributedCommits
                commitContributionsByRepository(maxRepositories: 100) {{
                    repository {{ visibility owner {{ login }} }}
                    contributions(first: 1) {{ totalCount }}
                }}
            }}
        ''')

    query = f'{{ user(login: "{USERNAME}") {{ {" ".join(fields)} }} }}'
    reply = subprocess.check_output(
        ["gh", "api", "graphql", "-f", f"query={query}"], text=True
    )
    user = json.loads(reply)["data"]["user"]
    counts = []
    for index in range(len(months)):
        month = user[f"month{index}"]
        groups = month["commitContributionsByRepository"]
        if len(groups) != month["totalRepositoriesWithContributedCommits"]:
            raise ValueError(f"Incomplete repository breakdown for {months[index]}")
        owned = community = 0
        for group in groups:
            repo = group["repository"]
            if repo["visibility"] != "PUBLIC":
                continue
            count = group["contributions"]["totalCount"]
            if repo["owner"]["login"].casefold() == USERNAME.casefold():
                owned += count
            else:
                community += count
        counts.append((owned, community))
    return counts


def render(months, counts):
    """Compact 400x140 card, the same size as the GitRanks card it sits next to."""
    personal = sum(own for own, _ in counts)
    community = sum(other for _, other in counts)
    largest = max(1, max(sum(pair) for pair in counts))
    left, right, bottom, height = 150, 384, 112, 64
    pitch = (right - left) / len(months)
    bar = 12

    marks = []
    for fraction in (0, 0.5, 1):
        y = bottom - fraction * height
        marks.append(f'<path class="grid" d="M{left} {y:g}H{right}"/>')

    for index, (month, (own, other)) in enumerate(zip(months, counts)):
        x = left + index * pitch + (pitch - bar) / 2
        own_height = own / largest * height
        other_height = other / largest * height
        month_name = MONTH_NAMES[month.month - 1]
        marks.append(f'''
  <g>
    <title>{month_name} {month.year} · Own repos {own:,} · Other repos {other:,}</title>
    <rect class="own" x="{x:.2f}" y="{bottom - own_height:.2f}" width="{bar}" height="{own_height:.2f}"/>
    <rect class="other" x="{x:.2f}" y="{bottom - own_height - other_height:.2f}" width="{bar}" height="{other_height:.2f}"/>
  </g>
  <text class="axis" x="{x + bar / 2:.2f}" y="127" text-anchor="middle">{month_name[0]}</text>''')

    period = f"{MONTH_NAMES[months[0].month - 1]} {months[0].year} – {MONTH_NAMES[months[-1].month - 1]} {months[-1].year}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="140" viewBox="0 0 400 140" role="img" aria-labelledby="title description">
  <title id="title">Public commit activity</title>
  <desc id="description">{period}. {personal:,} commits in own repositories and {community:,} in community and organization repositories.</desc>
  <style>
    .card {{fill:#fff;stroke:#d0d7de}}
    text {{font-family:system-ui,-apple-system,sans-serif;fill:#1f2328}}
    .label {{font-size:10px;font-weight:600;letter-spacing:1.6px;fill:#59636e}}
    .total {{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:21px;font-weight:700}}
    .muted,.axis {{fill:#59636e}}
    .muted {{font-size:11px}}
    .axis {{font-size:9px}}
    .grid {{stroke:#d8dee4;stroke-width:1}}
    .own {{fill:#cf222e}}
    .other {{fill:#0969da}}
    @media(prefers-color-scheme:dark) {{
      .card {{fill:#161b22;stroke:#30363d}}
      text {{fill:#f0f6fc}}
      .label,.muted,.axis {{fill:#b1bac4}}
      .grid {{stroke:#30363d}}
      .own {{fill:#ff5c5c}}
      .other {{fill:#58a6ff}}
    }}
  </style>
  <rect class="card" x=".5" y=".5" width="399" height="139" rx="10"/>
  <text class="label" x="16" y="26">PUBLIC COMMITS</text>
  <text class="label" x="384" y="26" text-anchor="end">{period.upper()}</text>
  <text class="total" x="16" y="62">{personal:,}</text>
  <rect class="own" x="16" y="70" width="8" height="8" rx="2"/>
  <text class="muted" x="29" y="78">own repos</text>
  <text class="total" x="16" y="106">{community:,}</text>
  <rect class="other" x="16" y="114" width="8" height="8" rx="2"/>
  <text class="muted" x="29" y="122">community &amp; orgs</text>
  {"".join(marks)}
</svg>
'''


def main():
    now = datetime.now(timezone.utc)
    current_month = now.year * 12 + now.month - 1
    months = [date(number // 12, number % 12 + 1, 1) for number in range(current_month - 11, current_month + 1)]
    counts = public_commits(months, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    OUTPUT.write_text(render(months, counts), encoding="utf-8")


if __name__ == "__main__":
    main()
