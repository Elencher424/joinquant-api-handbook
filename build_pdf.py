"""Render catalog.json as a searchable, linked Chinese PDF handbook."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
OUTPUT = ROOT / "JoinQuant_API_Handbook.pdf"

font_candidates = [
    ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
     "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/PingFang.ttc"),
]
font_pair = next(((regular, bold) for regular, bold in font_candidates
                  if Path(regular).exists() and Path(bold).exists()), None)
if not font_pair:
    raise RuntimeError("A CJK font is required (Microsoft YaHei, Noto Sans CJK, or PingFang).")
pdfmetrics.registerFont(TTFont("YaHei", font_pair[0], subfontIndex=0))
pdfmetrics.registerFont(TTFont("YaHeiBold", font_pair[1], subfontIndex=0))
pdfmetrics.registerFontFamily("YaHei", normal="YaHei", bold="YaHeiBold")

INK = colors.HexColor("#17233A")
BLUE = colors.HexColor("#195CB6")
LIGHT = colors.HexColor("#EAF1FA")
MUTED = colors.HexColor("#526174")
LINE = colors.HexColor("#DCE4EE")

styles = {
    "title": ParagraphStyle("title", fontName="YaHeiBold", fontSize=26, leading=38,
                             textColor=INK, alignment=TA_LEFT, spaceAfter=8*mm),
    "subtitle": ParagraphStyle("subtitle", fontName="YaHei", fontSize=12, leading=19,
                                textColor=MUTED, spaceAfter=6*mm),
    "h1": ParagraphStyle("h1", fontName="YaHeiBold", fontSize=16, leading=23,
                          textColor=INK, spaceBefore=7*mm, spaceAfter=4*mm,
                          keepWithNext=True),
    "h2": ParagraphStyle("h2", fontName="YaHeiBold", fontSize=11.5, leading=17,
                          textColor=BLUE, spaceBefore=4*mm, spaceAfter=2*mm,
                          keepWithNext=True),
    "body": ParagraphStyle("body", fontName="YaHei", fontSize=8.6, leading=15,
                            textColor=INK, spaceAfter=2*mm),
    "small": ParagraphStyle("small", fontName="YaHei", fontSize=7.7, leading=12.5,
                             textColor=INK),
    "cell": ParagraphStyle("cell", fontName="YaHei", fontSize=7.8, leading=12.2,
                            textColor=INK),
    "cellhead": ParagraphStyle("cellhead", fontName="YaHeiBold", fontSize=8.2, leading=12.6,
                                textColor=colors.white),
    "code": ParagraphStyle("code", fontName="YaHei", fontSize=7.2, leading=11,
                            textColor=INK, wordWrap="CJK"),
}


def P(text: str, style="body") -> Paragraph:
    return Paragraph(text, styles[style])


def E(text: str) -> str:
    return escape(str(text)).replace("\n", "<br/>")


def footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(LINE)
    canvas.line(18*mm, 17*mm, w-18*mm, 17*mm)
    canvas.setFont("YaHei", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18*mm, 12*mm, "聚宽 API 接口大全  |  非官方整理 · 以聚宽原文档为准")
    canvas.drawRightString(w-18*mm, 12*mm, str(doc.page))
    canvas.restoreState()


class Handbook(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=18*mm,
                         rightMargin=18*mm, topMargin=17*mm,
                         bottomMargin=22*mm, title="聚宽 API 接口大全",
                         author="Community reference")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      id="normal", leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=footer))
        self._bookmarks = 0

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            self._bookmarks += 1
            key = f"section-{self._bookmarks}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(), key, 0)


def table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, -1), (-1, -1), .4, LINE),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), INK),
                     ("LINEBELOW", (0, 0), (-1, 0), .7, INK)]
    t.setStyle(TableStyle(commands))
    return t


entries = DATA["entries"]
topics = DATA["topics"]
call_rows = sum(e["kind"] == "function" for e in entries)
page_names = {"api": "策略平台", "Stock": "股票", "Future": "期货", "fund": "基金",
              "index": "指数", "JQData": "JQData", "optimizer": "组合优化",
              "faq": "常见问题", "plateData": "行业与概念", "Option": "期权"}

story = []
build_date = datetime.fromisoformat(DATA["generated_at"]).strftime("%Y-%m-%d")
story += [Spacer(1, 31*mm), P("聚宽 API 接口大全", "title"),
          P("策略平台与 JQData · 官方关联页面索引", "subtitle"),
          Spacer(1, 7*mm),
          P(f"10 个官方页面  /  {len(entries)} 条文档条目  /  "
            f"{call_rows} 条附调用形式", "subtitle"),
          P(f"编纂日期：{build_date}", "body"),
          Spacer(1, 17*mm),
          P("本手册按官方页面组织接口名称、简要用途和可识别的调用形式，并列出子页主题。"
            "它是便于检索的原创索引；参数细则、返回字段、权限和版本变化请打开各条目的官方来源核对。", "body"),
          P("官方入口：<link href='https://www.joinquant.com/help/api/help#name:api' color='#195CB6'>"
            "www.joinquant.com/help/api/help#name:api</link>", "body"),
          PageBreak()]

story += [P("阅读指南", "h1"),
          P("页面分成两类：策略平台 API 主要用于回测与模拟交易；JQData 提供研究和本地 Python 数据接口。"
            "名称相同的函数可能因运行环境、权限或版本而有不同参数。", "body"),
          P("<b>条目说明</b>：'调用形式' 是从官方示例中识别的签名摘录；省略号或空白表示该段资料不是明确函数签名。"
            "'主题导航' 收录各子页的章节和数据表标题，便于追溯没有独立签名的内容。", "body"),
          P("<b>使用提醒</b>：证券代码、交易日、复权、停牌填充、历史时点、数据权限和查询上限会影响结果。"
            "下单与回测配置还受引擎撮合、费用、滑点和运行时点影响。运行策略前请核对相应官方章节。", "body"),
          P("来源范围", "h1")]

source_rows = [[P("官方页面", "cellhead"), P("条目", "cellhead"), P("文档入口", "cellhead")]]
for page in DATA["pages"]:
    label = page_names.get(page["name"], page["name"])
    source_rows.append([P(E(label), "cell"), P(str(page["entry_count"]), "cell"),
                        P(f"<link href='{escape(page['url'])}' color='#195CB6'>"
                          f"{E(page['name'])}</link>", "cell")])
story += [table(source_rows, [48*mm, 20*mm, 105*mm]),
          Spacer(1, 3*mm),
          P(f"统计基于 {build_date} 可取得的页面内容。相同调用可能在不同资产类别或页面中出现多次；"
            "本表按文档条目计数。", "small"), PageBreak()]

story += [P("接口与数据条目", "h1"),
          P("按原始官方页面排列。每页标题中的链接可打开原文；条目文本经过压缩整理。", "body")]
for page in DATA["pages"]:
    name = page["name"]
    items = [e for e in entries if e["page"] == name]
    if not items:
        continue
    story += [P(f"{E(page_names.get(name, name))}  ·  {len(items)} 条", "h1"),
              P(f"<link href='{escape(page['url'])}' color='#195CB6'>打开官方 {E(name)} 页面</link>", "small")]
    rows = [[P("名称 / 用途", "cellhead"), P("调用形式或说明", "cellhead")]]
    for item in items:
        left = f"<b>{E(item['name'])}</b>"
        if item["purpose"] and item["purpose"] != item["name"]:
            left += f"<br/><font color='#526174'>{E(item['purpose'])}</font>"
        right = E(item["signature"]) if item["signature"] else "<font color='#526174'>文档主题 / 数据表</font>"
        rows.append([P(left, "cell"), P(right, "code")])
    story += [Spacer(1, 2*mm), table(rows, [59*mm, 114*mm]), Spacer(1, 4*mm)]

story += [PageBreak(), P("官方子页主题导航", "h1"),
          P("以下为官方关联页面的章节标题。表中保留中文标题以便与原站搜索对应。", "body")]
for page in DATA["pages"]:
    page_topics = [t for t in topics if t["page"] == page["name"]]
    if not page_topics:
        continue
    story += [P(E(page_names.get(page["name"], page["name"])), "h1")]
    topic_rows = [[P("级别", "cellhead"), P("主题", "cellhead")]]
    for item in page_topics:
        topic_rows.append([P(E(item["level"].upper()), "cell"), P(E(item["title"]), "cell")])
    story += [table(topic_rows, [22*mm, 151*mm]), Spacer(1, 4*mm)]

story += [P("来源与维护", "h1"),
          P("资料来自聚宽帮助中心的 API 页面及从中链接到的官方子页。"
            "接口可能调整；本手册不替代最新官方文档。项目内的 catalog.json 可用于搜索和后续更新。", "body"),
          P("官方入口：<link href='https://www.joinquant.com/help/api/help#name:api' color='#195CB6'>"
            "聚宽 API 文档</link>；本地数据包：<link href='https://github.com/JoinQuant/jqdatasdk' color='#195CB6'>"
            "JoinQuant/jqdatasdk</link>。", "body")]

Handbook(OUTPUT).build(story)
print(OUTPUT)
