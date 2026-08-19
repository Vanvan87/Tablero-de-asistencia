"""Exporta el one-pager a PDF (A4 horizontal) con los mismos números y
gráficos que muestra el tablero. Los gráficos Plotly se rasterizan con kaleido.
"""
from __future__ import annotations

import unicodedata
from datetime import date

import plotly.graph_objects as go
from fpdf import FPDF

from .config import PALETA, Ajustes

# Geometría A4 horizontal en mm
W, H, M = 297, 210, 8

_NAVY = (11, 31, 58)
_MUTED = (107, 126, 147)
_LINEA = (226, 232, 240)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _t(s: str) -> str:
    """Las fuentes base de FPDF son latin-1: sustituir lo que no cabe."""
    s = (
        s.replace("\u2014", "-").replace("\u2013", "-").replace("\u2011", "-")
        .replace("\u2192", "->").replace("\u00b7", " | ").replace("\u2265", ">=")
        .replace("\u2264", "<=").replace("\u2212", "-").replace("\u201c", '"')
        .replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u00d7", "x")
    )
    return "".join(ch if ord(ch) < 256 else unicodedata.normalize("NFKD", ch)[0] for ch in s)


def _png(fig: go.Figure, ancho_px: int, alto_px: int) -> bytes:
    fig = go.Figure(fig)
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")
    return fig.to_image(format="png", width=ancho_px, height=alto_px, scale=2)


class _Doc(FPDF):
    def caja(self, x, y, w, h, radio=2.0, borde=_LINEA, relleno=(255, 255, 255)):
        self.set_draw_color(*borde)
        self.set_fill_color(*relleno)
        self.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=radio)

    def texto(self, x, y, s, tam=9, estilo="", color=_NAVY, ancho=None, alinear="L"):
        self.set_font("helvetica", estilo, tam)
        self.set_text_color(*color)
        self.set_xy(x, y)
        self.cell(ancho or self.get_string_width(_t(s)) + 1, tam * 0.42, _t(s), align=alinear)


def generar_pdf(aj: Ajustes, k, alcance: str, figuras: dict[str, go.Figure],
                hallazgos: list[tuple[str, str, str]], avisos: list[str]) -> bytes:
    pdf = _Doc(orientation="L", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_fill_color(238, 242, 246)
    pdf.rect(0, 0, W, H, style="F")

    # ---------------- encabezado ----------------
    hy, hh = M, 22
    pdf.set_fill_color(*_NAVY)
    pdf.rect(M, hy, W - 2 * M, hh, style="F", round_corners=True, corner_radius=2.5)
    pdf.texto(M + 6, hy + 4, f"{aj.institucion.upper()}  |  {aj.area.upper()}", 6.5, "B",
              _hex(PALETA["accent"]))
    pdf.texto(M + 6, hy + 9, aj.titulo, 14, "B", (255, 255, 255))
    pdf.texto(M + 6, hy + 16, alcance, 8, "", (201, 214, 232))
    ok = k.puntualidad >= aj.meta_puntualidad
    pdf.texto(W - M - 62, hy + 5, f"{k.puntualidad:.2%}", 21, "B",
              (127, 209, 168) if ok else (242, 162, 156), ancho=56, alinear="R")
    pdf.texto(W - M - 62, hy + 16,
              f"{k.brecha_pp:+.2f} pp vs meta {aj.meta_puntualidad:.0%}  |  "
              f"{k.unidades - k.unidades_bajo_meta} de {k.unidades} unidades cumplen",
              6.5, "", (201, 214, 232), ancho=56, alinear="R")

    # ---------------- KPIs ----------------
    ky, kh = hy + hh + 3, 16
    datos = [
        (f"{k.sesiones:,}", "Sesiones registradas", f"Excluye codigos {aj.excluir}", _NAVY),
        (f"{k.puntualidad:.2%}", "% Puntualidad", f"Meta {aj.meta_puntualidad:.0%}",
         _hex(aj.color(k.puntualidad))),
        (f"{k.incidencias:,}", "Con incidencia", f"{k.incidencias / k.sesiones:.2%} del total", _NAVY),
        (f"{k.incidencias_puntualidad:,}", "Retraso o salida previa",
         f"{k.incidencias_puntualidad / max(k.incidencias, 1):.1%} de las incidencias",
         _hex(PALETA["ambar"])),
        (f"{k.faltas:,}", "Faltas sin reponer", f"{k.pct_faltas:.2%} del total", _hex(PALETA["rojo"])),
        (f"{k.unidades_bajo_meta} de {k.unidades}", "Unidades bajo meta",
         f"Dispersion {k.dispersion_pp:.2f} pp",
         _hex(PALETA["rojo"]) if k.unidades_bajo_meta else _hex(PALETA["verde"])),
    ]
    kw = (W - 2 * M - 5 * 3) / 6
    for i, (v, lbl, sub, col) in enumerate(datos):
        x = M + i * (kw + 3)
        pdf.caja(x, ky, kw, kh)
        pdf.texto(x + 3, ky + 2.5, v, 12, "B", col)
        pdf.texto(x + 3, ky + 8.5, lbl, 6.6, "B")
        pdf.texto(x + 3, ky + 12, sub, 5.6, "", _MUTED)

    # ---------------- fila de gráficos 1 ----------------
    gy = ky + kh + 3
    g1h = 58
    ancho_izq = (W - 2 * M) * 0.485
    ancho_der = (W - 2 * M) - ancho_izq - 3

    pdf.caja(M, gy, ancho_izq, g1h)
    pdf.texto(M + 4, gy + 2.5, "Tendencia de % puntualidad", 8.5, "B")
    pdf.texto(M + 4, gy + 6.5, figuras.get("_sub_tendencia", ""), 6, "", _MUTED)
    if "tendencia" in figuras:
        img = _png(figuras["tendencia"], 900, 330)
        pdf.image(img, x=M + 2, y=gy + 9, w=ancho_izq - 4)

    pdf.caja(M + ancho_izq + 3, gy, ancho_der, g1h)
    pdf.texto(M + ancho_izq + 7, gy + 2.5, "Parrilla de horarios: puntualidad por dia y hora", 8.5, "B")
    pdf.texto(M + ancho_izq + 7, gy + 6.5,
              "Celdas vacias: menos de 30 sesiones. El color ancla en la meta.", 6, "", _MUTED)
    if "heatmap" in figuras:
        img = _png(figuras["heatmap"], 940, 330)
        pdf.image(img, x=M + ancho_izq + 5, y=gy + 9, w=ancho_der - 4)

    # ---------------- fila de gráficos 2 ----------------
    g2y = gy + g1h + 3
    g2h = 50
    tercio = (W - 2 * M - 6) / 3
    paneles = [
        ("unidades", "Puntualidad por unidad", "Rojo bajo meta; orden de peor a mejor"),
        ("prioridad", "Prioridad de atencion", "Volumen vs desempeno; tamano = sesiones"),
        ("codigos", "Donde estan las incidencias", "Sobre las sesiones con codigo"),
    ]
    for i, (clave, titulo, sub) in enumerate(paneles):
        x = M + i * (tercio + 3)
        pdf.caja(x, g2y, tercio, g2h)
        pdf.texto(x + 4, g2y + 2.5, titulo, 8.5, "B")
        pdf.texto(x + 4, g2y + 6.5, sub, 6, "", _MUTED)
        if clave in figuras:
            img = _png(figuras[clave], 620, 340)
            pdf.image(img, x=x + 2, y=g2y + 9, w=tercio - 4)

    # ---------------- lectura ejecutiva ----------------
    ly = g2y + g2h + 3
    lh = H - ly - M - 6
    pdf.caja(M, ly, W - 2 * M, lh)
    pdf.texto(M + 4, ly + 2.5, "Lectura ejecutiva y acciones", 8.5, "B")
    col_w = (W - 2 * M - 8 - 8) / 3
    acc = _hex(PALETA["accent"])

    def _corta(s: str, n: int) -> str:
        s = _t(s)
        return s if len(s) <= n else s[: n - 3].rstrip() + "..."

    for i, (titulo, detalle, accion) in enumerate(hallazgos[:3]):
        cx = M + 4 + i * (col_w + 4)
        cy = ly + 8
        pdf.set_draw_color(*acc)
        pdf.set_line_width(0.8)
        pdf.line(cx, cy + 0.3, cx, ly + lh - 3)
        pdf.set_font("helvetica", "B", 7.2)
        pdf.set_text_color(*_NAVY)
        pdf.set_xy(cx + 2.5, cy)
        pdf.cell(col_w - 5, 3.2, _corta(titulo, 58))
        pdf.set_font("helvetica", "", 6.4)
        pdf.set_text_color(65, 85, 110)
        pdf.set_xy(cx + 2.5, cy + 4.2)
        pdf.multi_cell(col_w - 5, 2.9, _corta(detalle, 175), max_line_height=2.9)
        pdf.set_font("helvetica", "B", 6.4)
        pdf.set_text_color(*_NAVY)
        pdf.set_xy(cx + 2.5, cy + 4.2 + 9.4)
        pdf.multi_cell(col_w - 5, 2.9, _corta("-> " + accion, 120), max_line_height=2.9)

    # ---------------- pie ----------------
    nota_avisos = ("  |  " + "; ".join(avisos[:2])) if avisos else ""
    pdf.texto(
        M, H - M - 2.5,
        f"Generado el {date.today():%Y-%m-%d} | % Puntualidad sobre Asistencia Global | "
        f"el indicador mide registro de check, no docencia impartida{nota_avisos}",
        5.6, "", _MUTED, ancho=W - 2 * M, alinear="C",
    )
    return bytes(pdf.output())
