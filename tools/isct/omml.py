"""Tiny LaTeX-subset to OMML converter, enough for the formulas of one paper."""
from xml.sax.saxutils import escape

SYMBOLS = {
    r"\lambda": "λ", r"\rho": "ρ", r"\theta": "θ", r"\gamma": "γ", r"\beta": "β",
    r"\tau": "τ", r"\le": "≤", r"\ge": "≥", r"\cdot": "·", r"\in": "∈",
    r"\infty": "∞", r"\Leftrightarrow": "⇔", r"\ne": "≠", r"\circ": "∘",
    r"\times": "×", r"\approx": "≈", r"\quad": " ", r",": " ",
    r"\mu": "μ", r"\sigma": "σ", r"\alpha": "α", r"\to": "→",
    r"\{": "{", r"\}": "}",
}

MATH_FONT = ('<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>'
             '<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>')


class Parser:
    def __init__(self, src: str, sz: int):
        self.s = src
        self.i = 0
        self.sz = sz

    # -- low level -------------------------------------------------------
    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ""

    def read_cmd(self):
        j = self.i + 1
        if j < len(self.s) and not self.s[j].isalpha():
            self.i = j + 1
            return "\\" + self.s[j]
        while j < len(self.s) and self.s[j].isalpha():
            j += 1
        cmd = self.s[self.i:j]
        self.i = j
        return cmd

    def run(self, text: str, upright: bool = False) -> str:
        sty = '<m:rPr><m:sty m:val="p"/></m:rPr>' if upright else ""
        return (f"<m:r>{sty}{MATH_FONT.format(sz=self.sz)}"
                f'<m:t xml:space="preserve">{escape(text)}</m:t></m:r>')

    def group(self) -> str:
        while self.peek() == " ":
            self.i += 1
        if self.peek() == "{":
            self.i += 1
            out = self.expr(stop="}")
            self.i += 1
            return out
        return self.atom()

    def raw_group(self) -> str:
        assert self.peek() == "{", self.s
        depth, j = 0, self.i
        while True:
            c = self.s[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        text = self.s[self.i + 1:j]
        self.i = j + 1
        return text

    # -- grammar ---------------------------------------------------------
    def expr(self, stop: str = "") -> str:
        parts = []
        while self.i < len(self.s):
            c = self.peek()
            if stop and c == stop:
                break
            if stop == "right" and self.s.startswith(r"\right", self.i):
                break
            parts.append(self.term())
        return "".join(parts)

    def term(self) -> str:
        base = self.atom()
        sub = sup = None
        while self.peek() in ("_", "^"):
            c = self.peek()
            self.i += 1
            g = self.group()
            if c == "_":
                sub = g
            else:
                sup = g
        if sub is not None and sup is not None:
            return (f"<m:sSubSup><m:e>{base}</m:e><m:sub>{sub}</m:sub>"
                    f"<m:sup>{sup}</m:sup></m:sSubSup>")
        if sub is not None:
            return f"<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"
        if sup is not None:
            return f"<m:sSup><m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>"
        return base

    def atom(self) -> str:
        c = self.peek()
        if c == " ":
            self.i += 1
            return ""
        if c == "{":
            self.i += 1
            out = self.expr(stop="}")
            self.i += 1
            return out
        if c == "\\":
            cmd = self.read_cmd()
            if cmd == r"\frac":
                num = self.group()
                den = self.group()
                return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"
            if cmd == r"\hat":
                e = self.group()
                return (f'<m:acc><m:accPr><m:chr m:val="̂"/></m:accPr>'
                        f"<m:e>{e}</m:e></m:acc>")
            if cmd == r"\mathrm":
                return self.run(self.raw_group(), upright=True)
            if cmd == r"\text":
                return self.run(self.raw_group(), upright=True)
            if cmd in (r"\max", r"\min", r"\arg", r"\ln"):
                return self.run(cmd[1:], upright=True)
            if cmd == r"\sum":
                sub = sup = ""
                while self.peek() in ("_", "^"):
                    c2 = self.peek()
                    self.i += 1
                    g = self.group()
                    if c2 == "_":
                        sub = g
                    else:
                        sup = g
                hide = "" if sup else '<m:supHide m:val="1"/>'
                body = self.term()
                return (f'<m:nary><m:naryPr><m:chr m:val="∑"/>'
                        f'<m:limLoc m:val="undOvr"/>{hide}</m:naryPr>'
                        f"<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup>"
                        f"<m:e>{body}</m:e></m:nary>")
            if cmd == r"\left":
                beg = self.peek()
                self.i += 1
                inner = self.expr(stop="right")
                self.read_cmd()  # \right
                end = self.peek()
                self.i += 1
                return (f'<m:d><m:dPr><m:begChr m:val="{escape(beg)}"/>'
                        f'<m:endChr m:val="{escape(end)}"/></m:dPr>'
                        f"<m:e>{inner}</m:e></m:d>")
            if cmd in SYMBOLS:
                return self.run(SYMBOLS[cmd])
            raise ValueError(f"unknown command {cmd} in {self.s}")
        # plain character run: letters/digits/operators until a special char
        j = self.i
        out = []
        while j < len(self.s) and self.s[j] not in "\\{}_^ ":
            out.append(self.s[j])
            j += 1
            # attach scripts to the last character only
            if j < len(self.s) and self.s[j] in "_^":
                if len(out) > 1:
                    j -= 1
                    out.pop()
                break
        self.i = j
        text = "".join(out).replace("-", "−")
        return self.run(text)


def omath(src: str, sz: int = 20) -> str:
    return f"<m:oMath>{Parser(src, sz).expr()}</m:oMath>"
