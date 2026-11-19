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
    personal = sum(own for own, _ in counts)
    community = sum(other for _, other in counts)
    largest = max(sum(pair) for pair in counts)
    step = max(1, (largest + 29) // 30 * 10)
    ceiling = step * 3
    bottom, height = 215, 96

    marks = []
    for value in range(0, ceiling + 1, step):
        y = bottom - value / ceiling * height
        marks.append(f'<path class="grid" d="M55 {y:g}H501"/>')
        marks.append(f'<text class="axis" x="46" y="{y + 4:g}" text-anchor="end">{value:,}</text>')

    for index, (month, (own, other)) in enumerate(zip(months, counts)):
        x = 69 + index * 36
        own_height = own / ceiling * height
        other_height = other / ceiling * height
        month_name = MONTH_NAMES[month.month - 1]
        label = f"{month_name} {month.year}"
        marks.append(f'''
          <g>
            <title>{label} · Own repos {own:,} · Other repos {other:,}</title>
            <rect class="own" x="{x}" y="{bottom - own_height:.2f}" width="22" height="{own_height:.2f}"/>
            <rect class="other" x="{x}" y="{bottom - own_height - other_height:.2f}" width="22" height="{other_height:.2f}"/>
          </g>
          <text class="axis" x="{x + 11}" y="237" text-anchor="middle">{month_name}</text>''')

    period = f"{MONTH_NAMES[months[0].month - 1]} {months[0].year} – {MONTH_NAMES[months[-1].month - 1]} {months[-1].year}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="254" viewBox="0 0 520 254" role="img" aria-labelledby="title description">
  <title id="title">Public commit activity</title>
  <desc id="description">{period}. {personal:,} commits in own repositories and {community:,} in community and organization repositories.</desc>
  <style>
    .card {{fill:#fff;stroke:#d0d7de}}
    text {{font-family:system-ui,-apple-system,sans-serif;fill:#1f2328}}
    .heading {{font-size:21px;font-weight:700}}
    .muted,.axis {{fill:#59636e}}
    .muted,.legend {{font-size:15px}}
    .axis {{font-size:13px}}
    .total {{font-size:20px;font-weight:700}}
    .grid {{stroke:#d8dee4;stroke-width:1}}
    .own {{fill:#cf222e}}
    .other {{fill:#0969da}}
    @media(prefers-color-scheme:dark) {{
      .card {{fill:#161b22;stroke:#30363d}}
      text {{fill:#f0f6fc}}
      .muted,.axis {{fill:#b1bac4}}
      .grid {{stroke:#30363d}}
      .own {{fill:#ff5c5c}}
      .other {{fill:#58a6ff}}
    }}
  </style>
  <rect class="card" x=".5" y=".5" width="519" height="253" rx="12"/>
  <text class="heading" x="21" y="31">Public commit activity</text>
  <text class="muted" x="21" y="54">{period} · GitHub</text>
  <rect class="own" x="21" y="79" width="10" height="10" rx="2"/>
  <text class="legend" x="39" y="89"><tspan class="total">{personal:,}</tspan> commits · own repos</text>
  <rect class="other" x="250" y="79" width="10" height="10" rx="2"/>
  <text class="legend" x="268" y="89"><tspan class="total">{community:,}</tspan> commits · community &amp; orgs</text>
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
