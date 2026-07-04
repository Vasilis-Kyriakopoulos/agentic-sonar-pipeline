from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def text_of(el: etree._Element) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def style_of(p: etree._Element) -> str:
    style = p.find("./w:pPr/w:pStyle", NS)
    return style.get(f"{{{NS['w']}}}val") if style is not None else ""


def has_drawing(p: etree._Element) -> bool:
    return bool(p.xpath(".//w:drawing|.//w:pict", namespaces=NS))


def rels_by_id(zf: zipfile.ZipFile) -> dict[str, str]:
    try:
        rel_xml = zf.read("word/_rels/document.xml.rels")
    except KeyError:
        return {}
    root = etree.fromstring(rel_xml)
    rel_ns = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
    return {
        rel.get("Id"): rel.get("Target", "")
        for rel in root.xpath("//pr:Relationship", namespaces=rel_ns)
    }


def image_targets(p: etree._Element, rels: dict[str, str]) -> list[str]:
    ids = p.xpath(".//@r:embed", namespaces=NS)
    return [rels.get(rid, rid) for rid in ids]


def main(path: str, start: int | None = None, end: int | None = None) -> int:
    docx = Path(path)
    with zipfile.ZipFile(docx) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
        rels = rels_by_id(zf)

    body = root.find("w:body", NS)
    for idx, child in enumerate(body):
        if start is not None and idx < start:
            continue
        if end is not None and idx > end:
            continue
        local = etree.QName(child).localname
        if local == "p":
            style = style_of(child)
            text = text_of(child)
            image = has_drawing(child)
            if style.startswith("Heading") or style == "Caption" or image or text:
                bits = [f"{idx:04d}", "P", style or "-"]
                if image:
                    bits.append("IMG=" + ",".join(image_targets(child, rels)))
                bits.append(text[:180].replace("\n", " "))
                print(" | ".join(bits))
        elif local == "tbl":
            first = text_of(child)[:180].replace("\n", " ")
            print(f"{idx:04d} | TBL | - | {first}")
    return 0


if __name__ == "__main__":
    start_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    end_arg = int(sys.argv[3]) if len(sys.argv) > 3 else None
    raise SystemExit(main(sys.argv[1], start_arg, end_arg))
