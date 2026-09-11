# -*- coding: utf-8 -*-
"""docx 后处理：页脚 PAGE 域补格式开关（WPS 兼容）+ 清理封面节空 pgNumType"""
import sys, zipfile, shutil, re, os

path = sys.argv[1]
tmp = path + ".tmp"
zin = zipfile.ZipFile(path, "r")

# 找出各节引用的 footer：解析 document.xml 中 sectPr 的 footerReference 顺序
doc_xml = zin.read("word/document.xml").decode("utf-8")

# 按节顺序收集 footer rId
sect_footers = []
for sect in re.finditer(r"<w:sectPr[ >].*?</w:sectPr>", doc_xml, re.S):
    m = re.search(r'<w:footerReference w:type="default" r:id="(rId\d+)"', sect.group(0))
    fmt = re.search(r'<w:pgNumType[^/]*w:fmt="([^"]+)"', sect.group(0))
    sect_footers.append((m.group(1) if m else None, fmt.group(1) if fmt else None))

# rId -> footer 文件名
rels = zin.read("word/_rels/document.xml.rels").decode("utf-8")
rid_map = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="(footer\d+\.xml)"', rels))

# 节序：0=封面（无页码）1=目录（upperRoman）2=正文（decimal）
# 对每个 footer 文件，按其所属节的 fmt 决定 instrText 开关
footer_fmt = {}
for i, (rid, fmt) in enumerate(sect_footers):
    if rid and rid in rid_map:
        f = rid_map[rid]
        if fmt == "upperRoman":
            footer_fmt[f] = "ROMAN"
        else:
            footer_fmt[f] = "arabic"

# 清理空 pgNumType（封面节 docx-js 可能输出 <w:pgNumType/>）
doc_xml_new = doc_xml.replace("<w:pgNumType/>", "")

zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == "word/document.xml":
        data = doc_xml_new.encode("utf-8")
    else:
        base = os.path.basename(item.filename)
        if base in footer_fmt and item.filename.startswith("word/footer"):
            xml = data.decode("utf-8")
            sw = footer_fmt[base]
            xml = re.sub(
                r'(<w:instrText[^>]*>)\s*PAGE\s*(</w:instrText>)',
                r'\1 PAGE \\* ' + sw + r' \\* MERGEFORMAT \2',
                xml)
            data = xml.encode("utf-8")
    zout.writestr(item, data)
zout.close()
zin.close()
shutil.move(tmp, path)
print("postprocess done:", path)
for f, sw in footer_fmt.items():
    print("  footer", f, "->", sw)
