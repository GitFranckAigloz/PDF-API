import fitz  # PyMuPDF
import pandas as pd
import unicodedata
from collections import defaultdict


def normalize(s):
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s


def cell_to_str(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def run_processing(PDF_INPUT, EXCEL_PATH, PDF_OUTPUT, REPORT_PATH):

    COLOR_HIGHLIGHT = (1, 1, 0)
    HIGHLIGHT_OPACITY = 0.3
    PADDING_X = 2
    PADDING_Y = 2
    POPUP_SPACING = 5

    # === Lecture Excel ===
    df = pd.read_excel(EXCEL_PATH)
    df.columns = [c.strip().lower() for c in df.columns]

    if "mot" not in df.columns:
        raise Exception("La colonne 'mot' est obligatoire")

    df["tooltip"] = df.get("tooltip", "").apply(cell_to_str)
    df["url"] = df.get("url", "").apply(cell_to_str)
    df["mot"] = df["mot"].apply(cell_to_str)

    # === Mapping ===
    mapping = {
        normalize(mot): {"mot": mot, "tooltip": tip, "url": url}
        for mot, tip, url in zip(df["mot"], df["tooltip"], df["url"])
    }

    mapping_sorted = sorted(mapping.items(), key=lambda x: -len(x[0]))

    index = defaultdict(list)
    for mot_norm, info in mapping_sorted:
        first = mot_norm.split()[0]
        index[first].append((mot_norm, info))

    results = {
        mot_norm: {
            "mot": info["mot"],
            "tooltip": info["tooltip"],
            "url": info["url"],
            "occurrences": 0,
            "pages": set()
        }
        for mot_norm, info in mapping.items()
    }

    # === PDF ===
    doc = fitz.open(PDF_INPUT)

    total_pages = len(doc)
    pages_sans_texte = 0

    for page_num, page in enumerate(doc, start=1):
        words = page.get_text("words")
        if not words:
            pages_sans_texte += 1
            continue

        words_norm = [normalize(w[4]) for w in words]
        used_popup_zones = []

        def get_non_overlapping_rect(base_rect):
            y_shift = 0
            test_rect = fitz.Rect(base_rect)
            while any(test_rect.intersects(r) for r in used_popup_zones):
                y_shift -= (base_rect.height + POPUP_SPACING)
                test_rect = fitz.Rect(
                    base_rect.x0,
                    base_rect.y0 + y_shift,
                    base_rect.x1,
                    base_rect.y1 + y_shift
                )
            used_popup_zones.append(test_rect)
            return test_rect

        i = 0
        while i < len(words_norm):
            candidates = index.get(words_norm[i], [])
            matched = False

            for mot_norm, info in candidates:
                tokens = mot_norm.split()
                n = len(tokens)

                if words_norm[i:i+n] == tokens:
                    x0 = min(words[i+j][0] for j in range(n))
                    y0 = min(words[i+j][1] for j in range(n))
                    x1 = max(words[i+j][2] for j in range(n))
                    y1 = max(words[i+j][3] for j in range(n))
                    rect = fitz.Rect(x0, y0, x1, y1)

                    is_vertical = rect.height > rect.width * 2

                    if is_vertical:
                        highlight = page.add_rect_annot(rect)
                        highlight.set_colors(stroke=COLOR_HIGHLIGHT, fill=COLOR_HIGHLIGHT)
                    else:
                        highlight = page.add_highlight_annot(rect)
                        highlight.set_colors(stroke=COLOR_HIGHLIGHT)

                    highlight.set_opacity(HIGHLIGHT_OPACITY)
                    highlight.update()

                    # Tooltip
                    if info["tooltip"]:
                        popup_rect = fitz.Rect(
                            rect.x0,
                            rect.y0 - rect.height - PADDING_Y,
                            rect.x1 + PADDING_X,
                            rect.y1 + PADDING_Y
                        )
                        popup_rect = get_non_overlapping_rect(popup_rect)

                        highlight.set_popup(popup_rect)
                        highlight.set_info(content=info["tooltip"])
                        highlight.set_open(False)
                        highlight.update()

                    # Lien
                    if info["url"]:
                        page.insert_link({
                            "kind": fitz.LINK_URI,
                            "from": rect,
                            "uri": info["url"],
                            "new_window": True
                        })

                    results[mot_norm]["occurrences"] += 1
                    results[mot_norm]["pages"].add(page_num)

                    i += n
                    matched = True
                    break

            if not matched:
                i += 1

    # === Sauvegarde PDF ===
    doc.save(PDF_OUTPUT, deflate=True)
    doc.close()

    # === Reporting fichier texte ===
    report_lines = [
        f"PDF généré : {PDF_OUTPUT}\n",
        f"{'Mot':25} | {'Tooltip':40} | {'URL':40} | {'Nb':>5} | Pages",
        "-" * 120
    ]

    total_occ = 0

    for mot_norm, info in results.items():
        pages = sorted(info["pages"])
        pages_str = ", ".join(map(str, pages)) if pages else "—"

        report_lines.append(
            f"{info['mot']:25} | {info['tooltip'][:40]:40} | {info['url'][:40]:40} | {info['occurrences']:>5} | {pages_str}"
        )

        total_occ += info["occurrences"]

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # === Retour JSON pour API ===
    clean_results = []

    for mot_norm, info in results.items():
        clean_results.append({
            "mot": info["mot"],
            "tooltip": info["tooltip"],
            "url": info["url"],
            "occurrences": info["occurrences"],
            "pages": list(info["pages"])
        })

    return clean_results