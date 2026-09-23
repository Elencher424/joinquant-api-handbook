# 聚宽 API 接口大全 / JoinQuant API Handbook

一份便于搜索的**非官方**聚宽 API 索引。PDF 覆盖[聚宽 API 入口](https://www.joinquant.com/help/api/help#name:api)及页面内链接到的 10 个官方帮助页面，收录 366 条文档条目、368 个章节主题；其中 209 条附有可识别的调用形式。编纂日期：2026-09-23。

An **unofficial**, searchable index of JoinQuant APIs. The PDF covers the [official API entry page](https://www.joinquant.com/help/api/help#name:api) and 10 linked help pages: 366 documentation entries, 368 section topics, and 209 entries with recognizable call forms. Compiled on 2026-09-23.

## 文件 / Files

- [`JoinQuant_API_Handbook.pdf`](JoinQuant_API_Handbook.pdf) — 接口与数据主题索引 / searchable handbook.
- [`catalog.json`](catalog.json) — 可供检索或二次处理的结构化目录 / machine-readable catalog.
- `build_catalog.py`, `build_pdf.py` — 更新目录和 PDF 的脚本 / refresh scripts.

## 更新 / Refresh

```bash
pip install -r requirements.txt
python build_catalog.py
python build_pdf.py
```

聚宽页面可能限制非中国大陆网络访问。已生成的 PDF 和 JSON 可以直接使用。PDF 构建需要系统安装中文字体（微软雅黑、Noto Sans CJK 或苹方）。

JoinQuant may restrict access outside mainland China. The included PDF and JSON can be used without refreshing. PDF generation requires a CJK font (Microsoft YaHei, Noto Sans CJK, or PingFang).

## 范围与来源 / Scope and sources

目录包含策略平台、股票、期货、基金、指数、期权、行业概念、JQData、组合优化及常见问题页面。它是对名称、简要用途、调用形式和章节的整理，**不是官方文档的逐字副本**。参数细则、返回字段、权限和版本变化请以[聚宽帮助中心](https://www.joinquant.com/help/api/help#name:api)及[官方 JQData 项目](https://github.com/JoinQuant/jqdatasdk)为准。

The catalog spans strategy APIs, stocks, futures, funds, indices, options, sectors, JQData, portfolio optimization, and FAQs. It organizes names, short purposes, call forms, and topics; it is **not a verbatim copy** of the documentation. Check the [official help center](https://www.joinquant.com/help/api/help#name:api) and [official JQData SDK](https://github.com/JoinQuant/jqdatasdk) for complete parameters, return fields, access rights, and updates.
