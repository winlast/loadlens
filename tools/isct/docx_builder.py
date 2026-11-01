"""
Builds an LNCS-style .docx on top of the Springer template supplied by the
organisers. The template's styles, numbering, page geometry and running heads
are kept; the body is regenerated with the same direct formatting the template
uses for each kind of paragraph.
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from omml import omath

TNR = "Times New Roman"
TEXT_W = 6918  # twips, 12.2 cm


def rpr(sz=20, b=False, i=False, sup=False, font=TNR, highlight=None):
    out = [f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}" w:cs="{font}"/>']
    if b:
        out.append('<w:b/><w:bCs/>')
    if i:
        out.append('<w:i/><w:iCs/>')
    out.append('<w:color w:val="000000"/>')
    out.append(f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>')
    if highlight:
        out.append(f'<w:highlight w:val="{highlight}"/>')
    if sup:
        out.append('<w:vertAlign w:val="superscript"/>')
    out.append('<w:lang w:val="en-US"/>')
    return "<w:rPr>" + "".join(out) + "</w:rPr>"


def run(text, **fmt):
    return f'<w:r>{rpr(**fmt)}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def tab_run(sz=20):
    return f"<w:r>{rpr(sz=sz)}<w:tab/></w:r>"


TOKEN = re.compile(r"(\$[^$]+\$|\{/?(?:b|i|sup|hl)\})")


def rich(text, sz=20, b=False, i=False):
    """Inline markup: {b}..{/b}, {i}..{/i}, {sup}..{/sup}, {hl}..{/hl}, $math$."""
    out = []
    state = {"b": b, "i": i, "sup": False, "hl": False}
    for tok in TOKEN.split(text):
        if not tok:
            continue
        m = re.fullmatch(r"\{(/?)(b|i|sup|hl)\}", tok)
        if m:
            state[m.group(2)] = not m.group(1)
            continue
        if tok.startswith("$") and tok.endswith("$") and len(tok) > 2:
            out.append(omath(tok[1:-1], sz=sz))
            continue
        out.append(run(tok, sz=sz, b=state["b"], i=state["i"], sup=state["sup"],
                       highlight="yellow" if state["hl"] else None))
    return "".join(out)


def ppr(before=0, after=0, left=0, right=0, first=None, hanging=None, jc="both",
        keep_next=False, keep_lines=False, num=None, tabs=None, line=240, sz=20):
    out = []
    if keep_next:
        out.append('<w:keepNext/>')
    if keep_lines:
        out.append('<w:keepLines/>')
    out.append('<w:widowControl/>')
    if num:
        out.append(f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>')
    if tabs:
        out.append('<w:tabs>' + "".join(
            f'<w:tab w:val="{v}" w:pos="{p}"/>' for v, p in tabs) + '</w:tabs>')
    out.append(f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>')
    ind = f'<w:ind w:left="{left}" w:right="{right}"'
    if hanging is not None:
        ind += f' w:hanging="{hanging}"'
    else:
        ind += f' w:firstLine="{first if first is not None else 0}"'
    out.append(ind + '/>')
    out.append(f'<w:jc w:val="{jc}"/>')
    out.append(rpr(sz=sz))
    return "<w:pPr>" + "".join(out) + "</w:pPr>"


def para(content, **kw):
    return f"<w:p>{ppr(**kw)}{content}</w:p>"


class Doc:
    def __init__(self):
        self.body: list[str] = []
        self.media: list[tuple[str, Path, str]] = []  # (rid, path, content type)
        self.fig_no = 0
        self.tab_no = 0
        self.eq_no = 0
        self.after_block = True  # next body paragraph has no indent

    # ---- front matter ---------------------------------------------------
    def title(self, text):
        self.body.append(para(run(text, sz=28, b=True), after=480, jc="center",
                              keep_next=True, keep_lines=True, sz=28))

    def raw_para(self, content, **kw):
        self.body.append(para(content, **kw))

    def abstract(self, text):
        self.body.append(para(run("Abstract. ", sz=18, b=True) + rich(text, sz=18),
                              before=600, after=0, left=567, right=567, jc="both", sz=18))

    def keywords(self, text):
        self.body.append(para(run("Keywords:", sz=18, b=True) + run(" " + text, sz=18),
                              before=220, after=360, left=567, right=567, hanging=567,
                              jc="left", sz=18))

    # ---- headings and text -----------------------------------------------
    def h1(self, text):
        self.body.append(para(run(text, sz=24, b=True), before=360, after=240, left=567,
                              hanging=567, jc="left", keep_next=True, keep_lines=True,
                              num=(1, 0), sz=24))
        self.after_block = True
        self._last_h1 = True

    def h2(self, text):
        before = 0 if getattr(self, "_last_h1", False) else 240
        self.body.append(para(run(text, sz=20, b=True), before=before, after=160, left=567,
                              hanging=567, jc="left", keep_next=True, keep_lines=True,
                              num=(1, 1), sz=20))
        self.after_block = True
        self._last_h1 = False

    def p(self, text, runin=None):
        first = 0 if self.after_block else 227
        content = ""
        if runin:
            content += run(runin + " ", sz=20, b=True)
        content += rich(text)
        self.body.append(para(content, first=first, jc="both"))
        self.after_block = False
        self._last_h1 = False

    def eq(self, latex):
        """
        Displayed equation: centred on its own line, number in parentheses at the
        right margin. A borderless three-cell row keeps the formula in display
        mode (full-size fractions), which a tab-separated line would not.
        """
        self.eq_no += 1
        side, mid = 800, TEXT_W - 1600
        math = (f'<m:oMathPara><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr>'
                f'{omath(latex, sz=20)}</m:oMathPara>')
        nil = "".join(f'<w:{b} w:val="nil"/>' for b in
                      ("top", "left", "bottom", "right", "insideH", "insideV"))

        def cell(w, content, jc):
            return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                    f'{para(content, before=60, after=60, jc=jc)}</w:tc>')

        self.body.append(
            f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:jc w:val="center"/>'
            f'<w:tblBorders>{nil}</w:tblBorders><w:tblLayout w:type="fixed"/>'
            '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
            '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
            '<w:tblLook w:val="0000"/></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="{side}"/><w:gridCol w:w="{mid}"/><w:gridCol w:w="{side}"/></w:tblGrid>'
            f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{cell(side, "", "left")}{cell(mid, math, "center")}'
            f'{cell(side, run(f"({self.eq_no})", sz=20), "right")}</w:tr></w:tbl>')
        self.after_block = True
        return self.eq_no

    # ---- floats -------------------------------------------------------------
    def figure(self, png: Path, svg: Path | None, width_cm: float, height_cm: float,
               caption: str, note: str | None, source: str):
        self.fig_no += 1
        n = self.fig_no
        rid_png = f"rIdFig{n}png"
        self.media.append((rid_png, png, "image/png"))
        ext = ""
        if svg is not None:
            rid_svg = f"rIdFig{n}svg"
            self.media.append((rid_svg, svg, "image/svg+xml"))
            ext = ('<a:extLst><a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}">'
                   '<asvg:svgBlip xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" '
                   f'r:embed="{rid_svg}"/></a:ext></a:extLst>')
        cx, cy = int(width_cm * 360000), int(height_cm * 360000)
        drawing = (
            '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{100 + n}" name="Figure {n}" descr="Figure {n}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{100 + n}" name="fig{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid_png}">{ext}</a:blip><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
        self.body.append(para(drawing, before=240, after=0, jc="center", keep_next=True))
        jc = "center" if len(caption) < 90 else "both"
        self.body.append(para(run(f"Fig. {n}.", sz=18, b=True) + rich(" " + caption, sz=18),
                              before=120, after=0, jc=jc, keep_next=True, sz=18))
        if note:
            self.body.append(para(rich(note, sz=18), before=0, after=0, jc="both",
                                  keep_next=True, sz=18))
        self.body.append(para(rich(source, sz=18), before=0, after=240, jc="both", sz=18))
        self.after_block = True
        return n

    def table(self, caption: str, header: list[str], rows: list[list[str]],
              widths: list[int], aligns: list[str], note: str | None, source: str):
        self.tab_no += 1
        n = self.tab_no
        jc = "center" if len(caption) < 90 else "both"
        self.body.append(para(run(f"Table {n}.", sz=18, b=True) + rich(" " + caption, sz=18),
                              before=240, after=120, jc=jc, keep_next=True, sz=18))
        total = sum(widths)
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/>'
               '<w:tblLayout w:type="fixed"/>'
               '<w:tblCellMar><w:top w:w="15" w:type="dxa"/><w:left w:w="57" w:type="dxa"/>'
               '<w:bottom w:w="15" w:type="dxa"/><w:right w:w="57" w:type="dxa"/></w:tblCellMar>'
               '<w:tblLook w:val="0000"/></w:tblPr>'
               f'<w:tblGrid>{grid}</w:tblGrid>']
        all_rows = [header] + rows
        for r_i, row in enumerate(all_rows):
            cells = []
            for c_i, text in enumerate(row):
                borders = []
                if r_i == 0:
                    borders += ['<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>',
                                '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>']
                if r_i == len(all_rows) - 1:
                    borders.append('<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>')
                tcb = f"<w:tcBorders>{''.join(borders)}</w:tcBorders>" if borders else ""
                align = aligns[c_i]
                content = rich(text, sz=18, b=False)
                cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[c_i]}" w:type="dxa"/>{tcb}'
                             '<w:vAlign w:val="center"/></w:tcPr>'
                             f'{para(content, jc=align, keep_next=r_i < len(all_rows) - 1, sz=18)}</w:tc>')
            hdr = '<w:tblHeader/>' if r_i == 0 else ''
            xml.append(f'<w:tr><w:trPr><w:cantSplit/>{hdr}</w:trPr>{"".join(cells)}</w:tr>')
        xml.append('</w:tbl>')
        self.body.append("".join(xml))
        if note:
            self.body.append(para(rich(note, sz=18), before=60, after=0, jc="both", sz=18))
        self.body.append(para(rich(source, sz=18), before=0 if note else 60, after=240,
                              jc="both", sz=18))
        self.after_block = True
        return n

    # ---- back matter -----------------------------------------------------
    def runin9(self, head, text, before=240):
        self.body.append(para(run(head + " ", sz=18, b=True) + rich(text, sz=18),
                              before=before, after=0, jc="both", sz=18))

    def references(self, items: list[str]):
        self.body.append(para(run("References", sz=24, b=True), before=360, after=240,
                              left=567, hanging=567, jc="left", keep_next=True, sz=24))
        for it in items:
            self.body.append(para(rich(it, sz=18), left=341, hanging=114, jc="both",
                                  num=(2, 0), sz=18))

    # ---- packaging ---------------------------------------------------------
    def save(self, template_dir: Path, out: Path, running_authors: str, running_title: str):
        work = out.with_suffix(".build")
        if work.exists():
            shutil.rmtree(work)
        if Path(template_dir).is_file():
            # the organisers' template as supplied (.docx)
            with zipfile.ZipFile(template_dir) as z:
                z.extractall(work)
        else:
            shutil.copytree(template_dir, work)
        # drop the sample chart of the template
        for rel in ("word/charts",):
            shutil.rmtree(work / rel, ignore_errors=True)
        docxml = (work / "word/document.xml").read_text(encoding="utf-8")
        head = docxml[:docxml.index("<w:body>") + len("<w:body>")]
        sect = re.search(r"<w:sectPr.*?</w:sectPr>", docxml, re.S).group(0)
        if "w:gutter" not in sect:
            sect = sect.replace("<w:pgMar ", '<w:pgMar w:gutter="0" ')
        if "xmlns:asvg" not in head:
            pass
        body = "".join(self.body)
        (work / "word/document.xml").write_text(head + body + sect + "</w:body></w:document>",
                                                encoding="utf-8")
        # relationships
        rels_p = work / "word/_rels/document.xml.rels"
        rels = rels_p.read_text(encoding="utf-8")
        rels = re.sub(r'<Relationship Id="rId7"[^>]*chart[^>]*/>', "", rels)
        rels = re.sub(r'<Relationship Id="rId8"[^>]*/>', "", rels)
        media_dir = work / "word/media"
        media_dir.mkdir(exist_ok=True)
        add = []
        for rid, path, ctype in self.media:
            name = path.name
            shutil.copy(path, media_dir / name)
            add.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                       f'officeDocument/2006/relationships/image" Target="media/{name}"/>')
        rels = rels.replace("</Relationships>", "".join(add) + "</Relationships>")
        rels_p.write_text(rels, encoding="utf-8")
        # content types
        ct_p = work / "[Content_Types].xml"
        ct = ct_p.read_text(encoding="utf-8")
        ct = re.sub(r'<Override PartName="/word/charts/[^"]*"[^>]*/>', "", ct)
        for ext, mime in (("png", "image/png"), ("svg", "image/svg+xml")):
            if f'Extension="{ext}"' not in ct:
                ct = ct.replace("<Default ", f'<Default Extension="{ext}" ContentType="{mime}"/><Default ', 1)
        ct_p.write_text(ct, encoding="utf-8")
        # running heads
        for hdr, text in (("header1.xml", running_authors), ("header2.xml", running_title)):
            hp = work / "word" / hdr
            h = hp.read_text(encoding="utf-8")
            h = h.replace("F. Author and S. Author", escape(running_authors))
            h = h.replace("Contribution Title (shortened if too long)", escape(running_title))
            hp.write_text(h, encoding="utf-8")
        # core properties
        cp = work / "docProps/core.xml"
        if cp.exists():
            c = cp.read_text(encoding="utf-8")
            c = re.sub(r"<dc:title>.*?</dc:title>", f"<dc:title>{escape(running_title)}</dc:title>", c)
            c = re.sub(r"<dc:creator>.*?</dc:creator>", f"<dc:creator>{escape(running_authors)}</dc:creator>", c)
            cp.write_text(c, encoding="utf-8")
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            ct_first = work / "[Content_Types].xml"
            z.write(ct_first, "[Content_Types].xml")
            for f in sorted(work.rglob("*")):
                if f.is_file() and f != ct_first:
                    z.write(f, f.relative_to(work).as_posix())
        shutil.rmtree(work)
