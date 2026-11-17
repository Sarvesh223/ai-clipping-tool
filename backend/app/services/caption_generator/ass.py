"""Karaoke captions as ASS. Words are taken verbatim from Whisper; only grouping/line-wrapping is added."""
import re
TEMPLATES = {  # colours are ASS &HBBGGRR
 "bold_yellow": dict(font="Arial Black", size=84, primary="&H0000FFFF", secondary="&H00FFFFFF", outline="&H00000000", ow=6, back="&H00000000", bold=1),
 "clean_white": dict(font="Segoe UI", size=72, primary="&H00FFFFFF", secondary="&H00CCCCCC", outline="&H00202020", ow=3, back="&H80000000", bold=1),
 "neon_purple": dict(font="Arial Black", size=80, primary="&H00F65C8B", secondary="&H00FFFFFF", outline="&H00201010", ow=5, back="&H00000000", bold=1),
}
def _t(x):
    x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02}:{x%60:05.2f}"

def build_ass(words, clip_start, clip_end, W=1080, H=1920, template="bold_yellow", per_line=4,
              size=None, margin_v=None, uppercase=False, **over):
    t = {**TEMPLATES.get(template, TEMPLATES["bold_yellow"]), **over}
    size = size or t["size"] * (W / 1080)
    mv = margin_v if margin_v is not None else int(H * 0.22)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{t['font']},{int(size)},{t['primary']},{t['secondary']},{t['outline']},{t['back']},{t['bold']},0,0,0,100,100,0,0,1,{t['ow']},0,2,60,60,{mv},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    ws = [w for w in words if w.end > clip_start and w.start < clip_end and w.text.strip()]
    lines = []
    for i in range(0, len(ws), per_line):
        g = ws[i:i + per_line]
        s, e = max(g[0].start, clip_start) - clip_start, min(g[-1].end, clip_end) - clip_start
        txt = ""
        for j, w in enumerate(g):
            nxt = g[j + 1].start if j + 1 < len(g) else w.end
            cs = max(1, int(round((nxt - w.start) * 100)))
            word = w.text.strip().replace("{", "(").replace("}", ")")
            txt += f"{{\\kf{cs}}}{word.upper() if uppercase else word} "
        lines.append(f"Dialogue: 0,{_t(s)},{_t(e)},Default,,0,0,0,,{txt.strip()}")
    return head + "\n".join(lines) + "\n"
