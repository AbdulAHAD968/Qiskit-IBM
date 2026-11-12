"""Draw the favicon set and the link-preview card for the website.

    python web/make_icons.py

Writes web/favicon.svg, web/favicon-32.png, web/apple-touch-icon.png and
web/og.png (1200 x 630, for WhatsApp, LinkedIn, Slack and X previews). The
mark is the screening question itself: two partners joined as a couple, both
tested (coral), above the affected child (ink).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CREAM, CARD, INK, BODY, MUTED, CORAL, HAIR = "#faf9f5", "#efe9de", "#141413", "#3d3d3a", "#6c6a64", "#c2613f", "#d9d1c6"
FONTS = Path("C:/Windows/Fonts")


def font(names, size):
    for n in names:
        for base in (FONTS, Path("/usr/share/fonts/truetype/dejavu")):
            p = base / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#faf9f5"/>
  <path d="M20 22h24M32 22v14M32 36v10" stroke="#141413" stroke-width="3" fill="none" stroke-linecap="round"/>
  <rect x="9" y="13" width="18" height="18" rx="2" fill="#c2613f"/>
  <circle cx="46" cy="22" r="9" fill="#c2613f"/>
  <circle cx="32" cy="50" r="7" fill="#141413"/>
</svg>
"""


def mark(size):
    """The same mark as the SVG, drawn at a pixel size."""
    s = size / 64
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=14 * s, fill=CREAM)
    w = max(1, round(3 * s))
    d.line([(20 * s, 22 * s), (44 * s, 22 * s)], fill=INK, width=w)
    d.line([(32 * s, 22 * s), (32 * s, 46 * s)], fill=INK, width=w)
    d.rounded_rectangle([9 * s, 13 * s, 27 * s, 31 * s], radius=2 * s, fill=CORAL)
    d.ellipse([37 * s, 13 * s, 55 * s, 31 * s], fill=CORAL)
    d.ellipse([25 * s, 43 * s, 39 * s, 57 * s], fill=INK)
    return im


def og():
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    serif = font(["georgia.ttf", "DejaVuSerif.ttf"], 128)
    sans = font(["segoeui.ttf", "DejaVuSans.ttf"], 34)
    sans_b = font(["segoeuib.ttf", "DejaVuSans-Bold.ttf"], 24)
    small = font(["segoeui.ttf", "DejaVuSans.ttf"], 24)
    d.text((80, 70), "QISKIT FALL FEST 2026  /  HEALTHCARE", font=sans_b, fill=CORAL)
    d.text((74, 112), "Kinship", font=serif, fill=INK)
    d.multiline_text((80, 282), "Which relatives should a field officer test\nwith four kits? A quantum circuit plans it.",
                     font=sans, fill=BODY, spacing=10)
    d.text((80, 552), "Thalassaemia cascade screening in Pakistan  |  QAOA in Qiskit", font=small, fill=MUTED)

    # a small family: parents, the affected child, two siblings and two cousins they may marry
    ox, oy = 726, 120
    def sq(x, y, fill=None, out=INK, r=22):
        d.rectangle([x - r, y - r, x + r, y + r], fill=fill or CREAM, outline=out, width=4)
    def ci(x, y, fill=None, out=INK, r=22):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill or CREAM, outline=out, width=4)
    pts = {"f": (ox + 70, oy + 40), "m": (ox + 200, oy + 40), "u": (ox + 300, oy + 40), "a": (ox + 400, oy + 40)}
    d.line([pts["f"], pts["m"]], fill=HAIR, width=4)
    d.line([pts["u"], pts["a"]], fill=HAIR, width=4)
    kids1 = [ox + 40, ox + 120, ox + 200]
    kids2 = [ox + 310, ox + 390]
    for xs, (a, b) in ((kids1, ("f", "m")), (kids2, ("u", "a"))):
        mx = (pts[a][0] + pts[b][0]) // 2
        d.line([(mx, oy + 40), (mx, oy + 120)], fill=HAIR, width=4)
        d.line([(xs[0], oy + 120), (xs[-1], oy + 120)], fill=HAIR, width=4)
        for x in xs:
            d.line([(x, oy + 120), (x, oy + 158)], fill=HAIR, width=4)
    sq(*pts["f"], fill="#e7cdbf"); ci(*pts["m"], fill="#e7cdbf"); sq(*pts["u"]); ci(*pts["a"])
    ci(kids1[0], oy + 180, fill=INK)                     # affected child
    sq(kids1[1], oy + 180, fill=CORAL, out=CORAL); sq(kids1[2], oy + 180, fill=CORAL, out=CORAL)
    ci(kids2[0], oy + 180, fill=CORAL, out=CORAL); ci(kids2[1], oy + 180, fill=CORAL, out=CORAL)
    # the two couples the plan tests in full
    for x1, x2, dep in ((kids1[1], kids2[0], 70), (kids1[2], kids2[1], 54)):
        pts_curve = []
        for i in range(41):
            t = i / 40
            x = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * ((x1 + x2) / 2) + t * t * x2
            y = (oy + 210) + 2 * (1 - t) * t * dep * 2
            pts_curve.append((x, y))
        d.line(pts_curve, fill=CORAL, width=6, joint="curve")
    d.text((ox + 10, oy + 330), "4 kits, 2 couples fully tested,", font=small, fill=BODY)
    d.text((ox + 10, oy + 362), "the exact optimum of 210 plans", font=small, fill=BODY)
    im.save(HERE / "og.png", optimize=True)


if __name__ == "__main__":
    (HERE / "favicon.svg").write_text(SVG, encoding="utf-8")
    mark(32).save(HERE / "favicon-32.png")
    big = Image.new("RGB", (180, 180), CREAM)
    big.paste(mark(180), (0, 0), mark(180))
    big.save(HERE / "apple-touch-icon.png")
    og()
    print("wrote favicon.svg, favicon-32.png, apple-touch-icon.png, og.png")
