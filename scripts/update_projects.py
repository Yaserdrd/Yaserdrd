"""Build a small animated project showcase from the owner's public repositories."""
import json
import os
import textwrap
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OWNER = os.environ.get('PROFILE_OWNER', 'Yaserdrd')
OVERRIDES = {
    'phishing-website-risk-analyzer': ('Phishing Website Risk Analyzer', 'An educational URL risk analysis prototype with transparent heuristics and an optional locally trained model.', 'Python  /  Streamlit  /  scikit-learn'),
    'spamguard': ('SpamGuard', 'An English SMS spam classifier with a React interface and reproducible machine learning notebooks.', 'Python  /  scikit-learn  /  React'),
}


def load_repos():
    if os.environ.get('PROFILE_FIXTURE'):
        return json.loads(Path(os.environ['PROFILE_FIXTURE']).read_text())
    repos = []
    for page in range(1, 11):
        url = f'https://api.github.com/users/{OWNER}/repos?type=owner&sort=created&direction=desc&per_page=100&page={page}'
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-project-showcase'}
        token = os.environ.get('GH_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            batch = json.load(response)
        repos.extend(batch)
        if len(batch) < 100:
            break
    return repos


def eligible(repo):
    return (not repo.get('fork') and not repo.get('archived') and not repo.get('private')
            and repo['name'].lower() != OWNER.lower()
            and repo.get('owner', {}).get('login', OWNER).lower() == OWNER.lower())


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(name, size)


def lines_that_fit(draw, text, fnt, width, limit):
    lines = []
    line = ''
    for word in text.split():
        candidate = f'{line} {word}'.strip()
        if draw.textlength(candidate, font=fnt) <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
            while draw.textlength(line, font=fnt) > width:
                part = line
                while draw.textlength(part, font=fnt) > width:
                    part = part[:-1]
                lines.append(part)
                line = line[len(part):]
    if line:
        lines.append(line)
    if len(lines) > limit:
        lines = lines[:limit]
        while draw.textlength(lines[-1] + '...', font=fnt) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += '...'
    return lines


def slide(repo, index, total):
    image = Image.new('RGB', (740, 220), '#f3f6ff')
    draw = ImageDraw.Draw(image)
    title, desc, tags = OVERRIDES.get(repo['name'], (
        repo['name'].replace('-', ' ').replace('_', ' '),
        repo.get('description') or 'Explore the code and documentation in this repository.',
        repo.get('language') or 'Source code on GitHub'))
    draw.text((25, 17), f'{index + 1:02d} / {total:02d}', fill='#656d76', font=font(12))
    title_lines = lines_that_fit(draw, title, font(23, True), 685, 2)
    y = 43
    for line in title_lines:
        draw.text((25, y), line, fill='#0969da', font=font(23, True))
        y += 29
    y += 10
    for line in lines_that_fit(draw, desc, font(15), 685, 3):
        draw.text((25, y), line, fill='#343c48', font=font(15))
        y += 22
    draw.text((25, 195), textwrap.shorten(tags, width=90), fill='#65548a', font=font(12))
    return image


def main():
    repos = [r for r in load_repos() if eligible(r)][:3]
    if not repos:
        raise SystemExit('No eligible public projects; preserving existing showcase.')
    slides = [slide(repo, i, len(repos)) for i, repo in enumerate(repos)]
    frames, durations = [], []
    for i, image in enumerate(slides):
        frames.append(image.quantize(colors=128))
        durations.append(6000)
        if len(slides) > 1:
            following = slides[(i + 1) % len(slides)]
            for step in range(1, 9):
                frames.append(Image.blend(image, following, step / 8).quantize(colors=128))
                durations.append(80)
    output = ROOT / 'assets' / 'latest-projects.gif'
    output.parent.mkdir(exist_ok=True)
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    readme = ROOT / 'README.md'
    content = readme.read_text()
    import re
    alt = 'Latest projects: ' + '; '.join(OVERRIDES.get(r['name'], (r['name'],))[0] for r in repos) + '. Open my repositories.'
    content = re.sub(r'(src="assets/latest-projects.gif" width="740" alt=")[^"]*(")', lambda m: m[1] + alt.replace('&', '&amp;').replace('"', '&quot;') + m[2], content)
    readme.write_text(content)
    print(f'Built {len(repos)} project slides: {output.stat().st_size} bytes')


if __name__ == '__main__':
    main()
