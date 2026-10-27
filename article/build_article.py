"""Build the 1.5-page Café Poliçe article (Turkish) as .docx and .md from outputs/metrics.json and priority_table.csv."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
M = json.loads((ROOT / "outputs" / "metrics.json").read_text(encoding="utf-8"))
T = pd.read_csv(ROOT / "outputs" / "priority_table.csv")
GITHUB = "https://github.com/000MAK/cafepolice-reinsurance-priority"
HF = "https://huggingface.co/makactuary/danish-fire-xl-priority"
NAVY, ORANGE = RGBColor(0x14, 0x21, 0x3D), RGBColor(0xB4, 0x56, 0x1C)


def tr(x: float, d: int = 0) -> str:
    """Turkish number format: thousands '.', decimals ','."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


g, o, b, h, th = M["gpd"], M["optimum"], M["bootstrap"], M["holdout"], M["threshold_sensitivity"]
h10, h30 = h["by_priority"]["10.0"], h["by_priority"]["30.0"]
xi_range = [min(v["xi"] for v in th.values()), max(v["xi"] for v in th.values())]
sens = sorted(set(M["sensitivity"].values()))
row = {p: T[T["priority"] == p].iloc[0] for p in (10.0, 30.0, o["priority"])}

TITLE = "Reasürans Dilimini Nereye Koymalı?"
SUBTITLE = "Danimarka yangın hasarlarıyla hasar fazlası (XL) muafiyetinin uç değer analizi"
BYLINE = "Mehmet Ali Kaya · Veri Yönetimi Uzmanı, Yönetim Bilişim Sistemleri Doktora Adayı, İstatistik Yüksek Lisans"
SPOT = (f"On bir yılın {tr(M['claims'])} yangın hasarıyla hasar fazlası korumasının muafiyetini hesapladım. "
        f"Doğru muafiyet tek bir sayı değil, {tr(o['within_5pct_range'][0], 1).rstrip('0').rstrip(',')}–{tr(o['within_5pct_range'][1])} milyon DKK arasında geniş ve düz bir vadi; "
        "asıl risk, vadinin yerini geçmiş veriden okurken trendi unutmak.")

SECTIONS = [
    ("Veri ve problem", [
        f"Veri, uç değer literatürünün klasiği danishuni: Copenhagen Re'ye 1980–1990 arasında bildirilen, 1 milyon DKK'yı aşan {tr(M['claims'])} ticari yangın hasarı, "
        f"1985 fiyatlarına enflasyonla düzeltilmiş (CASdatasets, GPL). Medyan hasar {tr(M['median'], 2)}, ortalama {tr(M['mean'], 2)}, en büyüğü {tr(M['max'])} milyon DKK. "
        "Soru, her aktüerin reasürans yenilemesinde sorduğu soru: Risk başına hasar fazlası (XL) korumasının muafiyetini nereye koymalı? "
        "Muafiyet düşerse reasürans pahalanır; yükselirse şirket büyük hasarı kendi sermayesiyle taşır.",
    ]),
    ("Model ve bulgular", [
        f"10 milyon DKK eşiğini aşan {g['n']} hasara Genelleştirilmiş Pareto dağılımı uydurdum: kuyruk parametresi ξ = {tr(g['xi'], 2)} "
        f"(bootstrap güven aralığı {tr(b['xi_ci95'][0], 2)}–{tr(b['xi_ci95'][1], 2)}; Hill tahmini {tr(M['hill_xi_k_eq_n_u'], 2)}; eşiğe göre {tr(xi_range[0], 2)}–{tr(xi_range[1], 2)}). "
        f"Model, geçmiş yılların gerçekleşen devrini (burning cost) yakından izliyor; 10 milyon muafiyette yıllık beklenen devir {tr(row[10.0]['ceded_model'], 1)}, gerçekleşen {tr(row[10.0]['burning_cost'], 1)} milyon DKK.",
        f"Muafiyeti seçmek için iki maliyeti topladım: reasürörün beklenen devir üzerindeki yüzde 30 marjı ve şirketin elde kalan yıllık hasarı için tuttuğu sermayenin yüzde 10'luk maliyeti "
        f"(sermaye: 50.000 simüle yılda yüzde 99,5 VaR eksi ortalama). Toplam maliyet {tr(o['priority'])} milyon DKK muafiyette en düşük: yılda {tr(o['total_cost'], 1)} milyon DKK; "
        f"reasüranssız {tr(o['total_cost_no_reinsurance'], 1)} milyonun yüzde {tr(o['saving_vs_no_reinsurance']*100)} altında. Ama eğri düz: Marj yüzde 20–50, sermaye maliyeti yüzde 6–10 arasında "
        f"değiştiğinde en iyi muafiyet {tr(sens[0])} ile {tr(sens[-1])} milyon arasında geziyor. Üstelik {tr(o['priority'])} milyon muafiyetteki beklenen devrin güven aralığı "
        f"{tr(b['ceded_at_optimum_ci95'][0], 1)}–{tr(b['ceded_at_optimum_ci95'][1])} milyon DKK; kuyruğun ucu belirsiz.",
        f"Son olarak modeli zamana karşı sınadım: 1980–1987 verisiyle kurup 1988–1990'ı tahmin ettirdim. 10 milyon muafiyette beklenen yıllık devir {tr(h10['expected'])}, gerçekleşen {tr(h10['observed'])} milyon; "
        f"simülasyonların yalnızca yüzde {tr(h10['share_of_sims_at_or_above_observed']*100, 1)}'i bu kadar kötü. Sebep frekans: Yıllık hasar sayısı {tr(h['train_claims_per_year'])}'den {tr(h['test_claims_per_year'])}'e çıktı. "
        f"30 milyon muafiyette ise sonuç tahmin aralığının içinde kaldı (simülasyonların yüzde {tr(h30['share_of_sims_at_or_above_observed']*100, 1)}'i).",
    ]),
]


def bottom_border(paragraph, color="E07A2E") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "8"), ("w:space", "4"), ("w:color", color)):
        bottom.set(qn(k), v)
    borders.append(bottom)
    p_pr.append(borders)


LESSON = ("Muafiyet seçimi bir noktayı değil bir aralığı hedeflemeli; aralığın içindeki son karar sermaye iştahına ve reasürans fiyatına bağlı. "
          "Asıl tehlike alt dilimlerde: Frekans trendi modele girmezse, en çok prim ödenen alt dilimlerin maliyeti sistematik olarak düşük görünür. "
          "Grafikteki en büyük üç hasarın Pareto çizgisinin üstünde durması da en üst dilimin modelden bile ağır olabileceğini hatırlatıyor.")

TABLE = [("Muafiyet (milyon DKK)", "Beklenen devir (model)", "Burning cost", "Elde kalan sermaye", "Toplam maliyet")] + [
    (f"{tr(p, 1).rstrip('0').rstrip(',')}" if p == p else "Reasüranssız",
     tr(r["ceded_model"], 1), tr(r["burning_cost"], 1), tr(r["scr_retained"]), tr(r["total_cost"], 1))
    for p, r in ((p, T[T["priority"] == p].iloc[0]) for p in (5.0, 10.0, 30.0, o["priority"], 100.0))
] + [("Reasüranssız", "0", "0", tr(T[T["priority"].isna()].iloc[0]["scr_retained"]), tr(o["total_cost_no_reinsurance"], 1))]


def build_docx(path: Path) -> None:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.3)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    hs = doc.styles["Heading 1"]
    hs.font.name, hs.font.size, hs.font.color.rgb, hs.font.bold = "Calibri", Pt(13), NAVY, True
    hs.paragraph_format.space_before, hs.paragraph_format.space_after = Pt(10), Pt(4)

    for text, size, color, bold, italic in ((TITLE, 24, NAVY, True, False), (SUBTITLE, 12.5, ORANGE, False, False),
                                            (BYLINE, 9.5, None, False, True), (SPOT, 11.5, None, True, False)):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold, r.italic, r.font.size = bold, italic, Pt(size)
        if color:
            r.font.color.rgb = color
        if text == BYLINE:
            bottom_border(p)

    for heading, paras in SECTIONS:
        doc.add_heading(heading, level=1)
        for text in paras:
            doc.add_paragraph(text)
    table = doc.add_table(rows=len(TABLE), cols=5)
    table.style = "Light Grid Accent 1"
    for i, vals in enumerate(TABLE):
        for j, val in enumerate(vals):
            cell = table.cell(i, j)
            cell.text = val
            run = cell.paragraphs[0].runs[0]
            run.font.size, run.bold = Pt(9), i == 0 or (j == 0 and val == tr(o["priority"]))
            if j:
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    cp = doc.add_paragraph()
    r = cp.add_run("Tablo 1. Yıllık değerler, milyon DKK. Sermaye: yüzde 99,5 VaR eksi ortalama; toplam maliyet: yüzde 30 reasürans marjı + yüzde 10 sermaye maliyeti.")
    r.italic, r.font.size = True, Pt(8.5)

    doc.add_picture(str(ROOT / "outputs" / "charts" / "01_kuyruk_ve_muafiyet.png"), width=Cm(16.4))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cp.add_run("Grafik 1. Solda büyük hasar kuyruğu ve Pareto uyumu; sağda muafiyete göre reasürans marjı, sermaye maliyeti ve toplamı.")
    r.italic, r.font.size = True, Pt(9)

    doc.add_heading("Sektör için tek ders", level=1)
    doc.add_paragraph(LESSON)
    p = doc.add_paragraph()
    r = p.add_run(f"Kod: {GITHUB}  ·  Sonuçlar: {HF}\nKaynak: Dutang, C. ve Charpentier, A., CASdatasets (danishuni); McNeil, A. (1996), ASTIN Bulletin 27(1). "
                  "Sonuçlar bir yöntem gösterimidir; reasürans fiyatı, marj ve sermaye maliyeti varsayımdır.")
    r.italic, r.font.size = True, Pt(8.5)
    doc.save(path)


def build_md(path: Path) -> None:
    lines = [f"# {TITLE}", f"*{SUBTITLE}*", "", f"*{BYLINE}*", "", f"**{SPOT}**", ""]
    for heading, paras in SECTIONS:
        lines += [f"## {heading}", ""] + [p + "\n" for p in paras]
    lines += ["| " + " | ".join(TABLE[0]) + " |", "|" + "---|" * 5] + ["| " + " | ".join(r) + " |" for r in TABLE[1:]] + [""]
    lines += ["![Grafik 1](../outputs/charts/01_kuyruk_ve_muafiyet.png)", "", "## Sektör için tek ders", "", LESSON, "",
              f"- Kod: {GITHUB}", f"- Sonuçlar: {HF}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    out = ROOT / "article"
    build_docx(out / "CafePolice_Reasurans_Muafiyet_MehmetAliKaya.docx")
    build_md(out / "CafePolice_Reasurans_Muafiyet_MehmetAliKaya.md")
    print("written")
