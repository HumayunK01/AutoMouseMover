import os
import urllib.request
import resvg_py

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(ROOT_DIR, "assets", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

icons = [
    'inbox', 'moon', 'sun', 'mouse-pointer-2', 'wind', 'route',
    'ghost', 'shield', 'refresh-cw', 'orbit', 'zap', 'shuffle',
    'timer', 'clock', 'play', 'square', 'log-out', 'x'
]

colors = {
    'white': '#ffffff',
    'dark': '#1e293b',       # For light mode text/buttons
    'light': '#f8fafc',      # For dark mode text/buttons
    'primary': '#4f46e5',    # Brand Indigo
    'muted': '#64748b',      # Neutral muted
}

for icon in icons:
    url = f'https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{icon}.svg'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        raw_svg = urllib.request.urlopen(req).read().decode('utf-8')
        for cname, chex in colors.items():
            colored_svg = raw_svg.replace('stroke="currentColor"', f'stroke="{chex}"')
            if 'stroke=' not in colored_svg:
                colored_svg = colored_svg.replace('<svg ', f'<svg stroke="{chex}" ')
            colored_svg = colored_svg.replace('width="24"', 'width="64"').replace('height="24"', 'height="64"')
            if 'stroke-width=' in colored_svg:
                colored_svg = colored_svg.replace('stroke-width="2"', 'stroke-width="2.3"')
            png_bytes = resvg_py.svg_to_bytes(colored_svg)
            fname = os.path.join(ICONS_DIR, f'{icon}_{cname}.png')
            with open(fname, 'wb') as f:
                f.write(png_bytes)
        print(f'Successfully generated {icon}')
    except Exception as e:
        print(f'Error on {icon}: {e}')

print(f"All icons successfully generated in: {ICONS_DIR}")
