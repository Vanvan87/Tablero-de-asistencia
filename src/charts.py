"""Graficos. Todos comparten escala 90-100% y linea de meta para que se puedan
comparar entre si de un vistazo."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .config import COLOR_CODIGO, PALETA, Ajustes

FUENTE = dict(family="Segoe UI, Helvetica, Arial, sans-serif", color=PALETA["navy"])


def _base(fig: go.Figure, alto: int, margen: dict | None = None) -> go.Figure:
    fig.update_layout(
        height=alto,
        margin=margen or dict(l=10, r=10, t=10, b=10),
        font=FUENTE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=PALETA["linea"])
    fig.update_yaxes(gridcolor="#F1F5F9", zeroline=False, linecolor=PALETA["linea"])
    return fig


def _rango_puntualidad(valores: pd.Series, aj: Ajustes) -> list[float]:
    lo = min(90.0, float(valores.min()) - 1) if len(valores) else 90.0
    return [max(0, lo), 100.5]


def barras_unidad(t: pd.DataFrame, aj: Ajustes, titulo_eje: str = "% Puntualidad") -> go.Figure:
    t = t.dropna(subset=["puntualidad"]).sort_values("puntualidad", ascending=False)
    v = t["puntualidad"] * 100
    fig = go.Figure(
        go.Bar(
            x=v,
            y=t["categoria"],
            orientation="h",
            marker_color=[aj.color(p) for p in t["puntualidad"]],
            text=[f"{x:.2f}%" for x in v],
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(color="white", size=11),
            customdata=t[["sesiones", "incidencias_puntualidad"]],
            hovertemplate="<b>%{y}</b><br>%{x:.2f}% puntualidad<br>"
            "%{customdata[0]:,} sesiones<br>%{customdata[1]:,} con retraso o salida previa<extra></extra>",
        )
    )
    fig.add_vline(x=aj.meta_puntualidad * 100, line=dict(color=PALETA["navy"], width=1.4, dash="dash"),
                  annotation_text=f"meta {aj.meta_puntualidad:.0%}", annotation_position="top",
                  annotation_font_size=10)
    fig.update_xaxes(range=_rango_puntualidad(v, aj), ticksuffix="%", showgrid=True, gridcolor="#F1F5F9")
    fig.update_yaxes(tickfont=dict(size=11))
    return _base(fig, max(260, 26 * len(t) + 40), dict(l=10, r=20, t=24, b=10))


def tendencia(t: pd.DataFrame, aj: Ajustes, etiqueta_x: str = "") -> go.Figure:
    v = t["puntualidad"] * 100
    fig = go.Figure(
        go.Scatter(
            x=t["categoria"], y=v, mode="lines+markers+text",
            line=dict(color=PALETA["teal"], width=2.6),
            marker=dict(size=8, color=[aj.color(p) for p in t["puntualidad"]],
                        line=dict(width=1.5, color="white")),
            text=[f"{x:.2f}%" for x in v], textposition="top center", textfont=dict(size=10),
            fill="tozeroy", fillcolor="rgba(47,167,154,0.10)",
            customdata=t[["sesiones", "incidencias_puntualidad"]],
            hovertemplate="<b>%{x}</b><br>%{y:.2f}% puntualidad<br>%{customdata[0]:,} sesiones"
            "<br>%{customdata[1]:,} incidencias<extra></extra>",
        )
    )
    fig.add_hline(y=aj.meta_puntualidad * 100, line=dict(color=PALETA["rojo"], width=1.2, dash="dash"),
                  annotation_text=f"meta {aj.meta_puntualidad:.0%}", annotation_position="bottom right",
                  annotation_font=dict(size=10, color=PALETA["rojo"]))
    fig.update_yaxes(range=_rango_puntualidad(v, aj), ticksuffix="%")
    fig.update_xaxes(title=etiqueta_x, title_font=dict(size=11, color=PALETA["muted"]))
    return _base(fig, 300, dict(l=10, r=20, t=30, b=30))


def matriz_prioridad(t: pd.DataFrame, aj: Ajustes) -> go.Figure:
    """Volumen de incidencia contra desempeno. Arriba a la izquierda = atender primero."""
    x = t["puntualidad"] * 100
    y = t["incidencias_puntualidad"]
    tam = (t["sesiones"] / t["sesiones"].max() * 45 + 12) if len(t) else 20
    fig = go.Figure(
        go.Scatter(
            x=x, y=y, mode="markers+text",
            marker=dict(size=tam, color=[aj.color(p) for p in t["puntualidad"]],
                        opacity=0.75, line=dict(width=1, color="white")),
            text=[c if i < 6 else "" for i, c in enumerate(t["categoria"])],
            textposition="middle right", textfont=dict(size=10),
            cliponaxis=False,
            customdata=t[["sesiones", "pct_del_total_incidencias"]],
            hovertemplate="<b>%{text}</b><br>%{x:.2f}% puntualidad<br>"
            "%{y:,} sesiones con retraso o salida previa<br>%{customdata[0]:,} sesiones totales"
            "<br>%{customdata[1]:.1%} de todas las incidencias<extra></extra>",
        )
    )
    fig.add_vrect(x0=x.min() - 1.5, x1=aj.meta_puntualidad * 100, fillcolor=PALETA["rojo"],
                  opacity=0.05, line_width=0)
    fig.add_vline(x=aj.meta_puntualidad * 100, line=dict(color=PALETA["rojo"], width=1.2, dash="dash"),
                  annotation_text="meta", annotation_position="top", annotation_font_size=10)
    fig.update_xaxes(title="% Puntualidad", ticksuffix="%",
                     title_font=dict(size=11, color=PALETA["muted"]),
                     range=[x.min() - 1.5, min(100.6, x.max() + 2.5)])
    fig.update_yaxes(title="Sesiones con retraso o salida previa",
                     title_font=dict(size=11, color=PALETA["muted"]),
                     range=[-y.max() * 0.08, y.max() * 1.18], showgrid=True)
    return _base(fig, 380, dict(l=60, r=30, t=24, b=44))


def contexto_incidencias(sin_incidencia: int, con_incidencia: int) -> go.Figure:
    """Barra apilada que conserva la proporcion real antes de hacer zoom."""
    total = sin_incidencia + con_incidencia
    fig = go.Figure()
    fig.add_bar(x=[sin_incidencia], y=[""], orientation="h", marker_color=PALETA["verde"],
                text=[f"{sin_incidencia:,} sin incidencia · {sin_incidencia/total:.2%}"],
                textposition="inside", insidetextanchor="middle",
                textfont=dict(color="white", size=12), hoverinfo="skip")
    fig.add_bar(x=[con_incidencia], y=[""], orientation="h", marker_color=PALETA["steel"],
                hovertemplate=f"{con_incidencia:,} con código<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.2)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _base(fig, 74, dict(l=0, r=0, t=6, b=6))


def barras_codigos(t: pd.DataFrame) -> go.Figure:
    t = t.sort_values("sesiones")
    fig = go.Figure(
        go.Bar(
            x=t["sesiones"], y=t["codigo_nombre"], orientation="h",
            marker_color=[COLOR_CODIGO.get(int(c), PALETA["muted"]) for c in t["codigo"]],
            text=[f"{n:,} · {p:.1%}" for n, p in zip(t["sesiones"], t["pct_incidencias"])],
            textposition="outside", textfont=dict(size=10),
            hovertemplate="<b>%{y}</b><br>%{x:,} sesiones<extra></extra>",
        )
    )
    fig.update_xaxes(visible=False, range=[0, t["sesiones"].max() * 1.35])
    fig.update_yaxes(tickfont=dict(size=11))
    return _base(fig, max(200, 30 * len(t) + 20), dict(l=10, r=10, t=6, b=6))


def barras_dia(t: pd.DataFrame, aj: Ajustes) -> go.Figure:
    orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    t = t[t["categoria"].isin(orden)].copy()
    t["orden"] = t["categoria"].map({d: i for i, d in enumerate(orden)})
    t = t.sort_values("orden")
    v = t["puntualidad"] * 100
    fig = go.Figure(
        go.Bar(x=t["categoria"], y=v, marker_color=[aj.color(p) for p in t["puntualidad"]],
               text=[f"{x:.2f}%" for x in v], textposition="outside", textfont=dict(size=11),
               customdata=t[["sesiones"]],
               hovertemplate="<b>%{x}</b><br>%{y:.2f}%<br>%{customdata[0]:,} sesiones<extra></extra>")
    )
    fig.add_hline(y=aj.meta_puntualidad * 100, line=dict(color=PALETA["rojo"], width=1.2, dash="dash"))
    fig.update_yaxes(range=_rango_puntualidad(v, aj), ticksuffix="%")
    return _base(fig, 280, dict(l=10, r=10, t=24, b=10))


def heatmap_dia_hora(t: pd.DataFrame, aj: Ajustes) -> go.Figure:
    """Parrilla de horarios: % puntualidad por día × hora de inicio."""
    piv = t.pivot(index="dia_semana", columns="franja", values="puntualidad")
    ses = t.pivot(index="dia_semana", columns="franja", values="sesiones")
    piv = piv.dropna(how="all").dropna(axis=1, how="all")
    ses = ses.reindex(index=piv.index, columns=piv.columns)
    z = piv.values * 100
    texto = [[f"{v:.1f}" if v == v else "" for v in fila] for fila in z]
    lo = aj.meta_puntualidad * 100
    zmin, zmax = min(88.0, float(pd.DataFrame(z).min().min() or 90) - 1), 100.0
    frac = max(0.0, min(1.0, (lo - zmin) / (zmax - zmin)))
    escala = [[0, PALETA["rojo"]], [frac, "#F3D8A8"], [1, PALETA["verde"]]]
    fig = go.Figure(go.Heatmap(
        z=z, x=piv.columns.tolist(), y=piv.index.tolist(),
        text=texto, texttemplate="%{text}", textfont=dict(size=10),
        colorscale=escala, zmin=zmin, zmax=zmax,
        customdata=ses.values,
        hovertemplate="<b>%{y} %{x}</b><br>%{z:.2f}% puntualidad<br>"
        "%{customdata:,.0f} sesiones<extra></extra>",
        colorbar=dict(ticksuffix="%", thickness=12, outlinewidth=0),
        hoverongaps=False,
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="bottom", tickfont=dict(size=10))
    return _base(fig, 300, dict(l=10, r=10, t=10, b=10))
