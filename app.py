"""Tablero ejecutivo de Puntualidad y Asistencia Docente.

Ejecutar en local:   streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, metrics
from src.config import PALETA, cargar_ajustes
from src.data import leer

AJ = cargar_ajustes()

st.set_page_config(page_title=f"{AJ.titulo} · {AJ.institucion}", page_icon="📋", layout="wide")

st.markdown(
    f"""
    <style>
      .block-container {{padding-top:1.4rem;padding-bottom:2rem;max-width:1400px}}
      #MainMenu, footer {{visibility:hidden}}
      .hdr {{background:linear-gradient(115deg,{PALETA['navy']},{PALETA['navy2']} 60%,#1B3A63);
            color:#fff;border-radius:12px;padding:18px 24px;display:flex;
            justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap}}
      .eb {{font-size:10px;letter-spacing:2.2px;text-transform:uppercase;
           color:{PALETA['accent']};font-weight:700}}
      .hdr h1 {{margin:4px 0 2px;font-size:22px;font-weight:700}}
      .hdr p {{margin:0;font-size:12.5px;color:#C9D6E8}}
      .score b {{display:block;font-size:36px;font-weight:800;line-height:1}}
      .score span {{font-size:11px;color:#C9D6E8}}
      .card {{background:#fff;border:1px solid {PALETA['linea']};border-radius:10px;
             padding:14px 16px;height:100%}}
      .card h3 {{font-size:13.5px;margin:0 0 2px;color:{PALETA['navy']}}}
      .card .sub {{font-size:11px;color:{PALETA['muted']};margin-bottom:4px;line-height:1.35}}
      .hall {{border-left:3px solid {PALETA['accent']};padding-left:11px;margin-bottom:12px}}
      .hall .t {{font-size:12.5px;font-weight:700}}
      .hall .d {{font-size:11.5px;color:#41556E;line-height:1.45;margin-top:2px}}
      .hall .a {{font-size:11.5px;font-weight:600;line-height:1.45;margin-top:3px}}
      .kgrid {{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:14px 0 4px}}
      .kpi {{background:#fff;border:1px solid {PALETA['linea']};border-radius:10px;padding:12px 14px}}
      .kv {{font-size:22px;font-weight:800;line-height:1.1}}
      .kl {{font-size:11.5px;font-weight:700;margin-top:2px}}
      .ks {{font-size:10px;color:{PALETA['muted']};margin-top:3px;line-height:1.3}}
      @media (max-width:1200px) {{.kgrid {{grid-template-columns:repeat(3,1fr)}}}}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- datos
@st.cache_data(show_spinner="Leyendo el registro diario…")
def _cargar(origen, nombre: str):
    return leer(origen, AJ)


with st.sidebar:
    st.markdown("### Fuente de datos")
    subido = st.file_uploader("Registro diario (.xlsx o .csv)", type=["xlsx", "xlsm", "csv"])
    if subido is None and AJ.ruta_fuente.exists():
        st.caption(f"Usando `{AJ.fuente}`. Sube un archivo para reemplazarlo.")

if subido is not None:
    df, avisos = _cargar(subido, subido.name)
elif AJ.ruta_fuente.exists():
    df, avisos = _cargar(AJ.ruta_fuente, str(AJ.ruta_fuente))
else:
    st.info(
        f"No encontré `{AJ.fuente}`. Sube el registro diario en la barra lateral, "
        "o genera datos de ejemplo con `python scripts/generar_demo.py`."
    )
    st.stop()

# --------------------------------------------------------------------------- filtros
with st.sidebar:
    st.markdown("### Alcance")
    periodos = (
        df.sort_values("orden_periodo")["periodo"].dropna().unique().tolist()
        if "orden_periodo" in df else sorted(df["periodo"].dropna().unique())
    )
    sel_per = st.multiselect("Periodo", periodos, default=periodos)
    vices = sorted(df["vicerrectoria"].dropna().unique()) if "vicerrectoria" in df else []
    sel_vic = st.multiselect("Vicerrectoría", vices, default=vices) if vices else []
    dim = st.radio("Comparar unidades por", ["escuela", "departamento"], horizontal=True,
                   format_func=str.capitalize)
    if avisos:
        with st.expander(f"Calidad del dato · {len(avisos)}"):
            for a in avisos:
                st.caption(f"• {a}")

f = df[df["periodo"].isin(sel_per)] if sel_per else df
if sel_vic:
    f = f[f["vicerrectoria"].isin(sel_vic)]
if f.empty:
    st.warning("La selección no deja sesiones. Amplía el alcance en la barra lateral.")
    st.stop()

k = metrics.kpis(f, AJ, dim_unidad=dim)
meta_txt = f"{AJ.meta_puntualidad:.0%}"
color_score = "#7FD1A8" if k.puntualidad >= AJ.meta_puntualidad else "#F2A29C"
if len(sel_per) == 1:
    alcance = sel_per[0]
elif len(sel_per) == len(periodos):
    alcance = f"{periodos[0]} a {periodos[-1]} · {len(periodos)} periodos"
else:
    alcance = f"{len(sel_per)} periodos seleccionados"

st.markdown(
    f"""
    <div class="hdr">
      <div>
        <div class="eb">{AJ.institucion} · {AJ.area}</div>
        <h1>{AJ.titulo}</h1>
        <p>{alcance} · {k.sesiones:,} sesiones · {k.unidades} unidades</p>
      </div>
      <div class="score" style="text-align:right">
        <b style="color:{color_score}">{k.puntualidad:.2%}</b>
        <span>{k.brecha_pp:+.2f} pp contra la meta de {meta_txt} ·
        {k.unidades - k.unidades_bajo_meta} de {k.unidades} unidades cumplen</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- KPIs
st.write("")


def tarjeta(valor: str, etiqueta: str, nota: str, color: str = PALETA["navy"]) -> str:
    return (f'<div class="kpi"><div class="kv" style="color:{color}">{valor}</div>'
            f'<div class="kl">{etiqueta}</div><div class="ks">{nota}</div></div>')


st.markdown(
    '<div class="kgrid">'
    + tarjeta(f"{k.sesiones:,}", "Sesiones registradas",
              f"Excluye códigos {AJ.excluir} · {k.asistencia_global:,} de Asistencia Global")
    + tarjeta(f"{k.puntualidad:.2%}", "% Puntualidad",
              f"Meta {meta_txt} · brecha {k.brecha_pp:+.2f} pp", AJ.color(k.puntualidad))
    + tarjeta(f"{k.incidencias:,}", "Sesiones con incidencia",
              f"{k.incidencias/k.sesiones:.2%} del total, cualquier código")
    + tarjeta(f"{k.incidencias_puntualidad:,}", "Retraso o salida previa",
              f"{k.incidencias_puntualidad/max(k.incidencias,1):.1%} de las incidencias · foco de acción",
              PALETA["ambar"])
    + tarjeta(f"{k.faltas:,}", "Faltas sin reponer",
              f"{k.pct_faltas:.2%} del total", PALETA["rojo"])
    + tarjeta(f"{k.unidades_bajo_meta} de {k.unidades}", "Unidades bajo meta",
              f"Dispersión de {k.dispersion_pp:.2f} pp entre la mejor y la peor",
              PALETA["rojo"] if k.unidades_bajo_meta else PALETA["verde"])
    + "</div>",
    unsafe_allow_html=True,
)

if k.minutos_perdidos:
    st.caption(
        f"⏱️ Tiempo lectivo comprometido en la selección: **{k.minutos_perdidos/60:,.0f} horas** "
        f"({k.minutos_perdidos:,.0f} minutos de arranque tardío)."
    )

# --------------------------------------------------------------------------- tendencia
tp = metrics.tendencia_periodo(f, AJ)
if len(tp) > 1:
    st.markdown("#### ¿Vamos mejorando?")
    st.caption("La única métrica que responde si el problema se corrige o se arrastra.")
    st.plotly_chart(charts.tendencia(tp, AJ, "Periodo académico"), use_container_width=True,
                    config={"displayModeBar": False})

# --------------------------------------------------------------------------- unidades + prioridad
izq, der = st.columns([1.25, 1])
with izq:
    st.markdown(f"#### Puntualidad por {dim}")
    st.caption(f"(Asistencia Global − retraso − salida previa) ÷ Asistencia Global · "
               f"rojo <{meta_txt}, ámbar hasta {AJ.umbral_verde:.0%}, verde arriba")
    st.plotly_chart(charts.barras_unidad(metrics.por_dimension(f, dim, AJ), AJ),
                    use_container_width=True, config={"displayModeBar": False})
with der:
    st.markdown("#### Prioridad de atención")
    st.caption("Volumen de incidencia contra desempeño. El tamaño es el número de sesiones: "
               "arriba a la izquierda se atiende primero.")
    pr = metrics.prioridad(f, AJ, "departamento" if "departamento" in f else dim)
    if not pr.empty:
        st.plotly_chart(charts.matriz_prioridad(pr.head(15), AJ), use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.info("Sin departamentos que superen el mínimo de sesiones configurado.")

# --------------------------------------------------------------------------- incidencias
st.markdown("#### Dónde están las incidencias")
sin_inc = int((f["codigo"] == 0).sum())
st.plotly_chart(charts.contexto_incidencias(sin_inc, k.incidencias), use_container_width=True,
                config={"displayModeBar": False})
a, b = st.columns([1, 1])
with a:
    st.caption(f"Desglose de las {k.incidencias:,} sesiones con código. "
               "Los porcentajes son sobre ese subconjunto, no sobre el total.")
    st.plotly_chart(charts.barras_codigos(metrics.composicion_codigos(f, AJ)),
                    use_container_width=True, config={"displayModeBar": False})
with b:
    if "dia_semana" in f:
        st.caption("Puntualidad por día de la semana: el patrón operativo suele explicar más que el docente.")
        st.plotly_chart(charts.barras_dia(metrics.por_dimension(f, "dia_semana", AJ, 50), AJ),
                        use_container_width=True, config={"displayModeBar": False})

# --------------------------------------------------------------------------- tablas
st.markdown("#### Detalle accionable")
t1, t2, t3 = st.tabs(["Por volumen de incidencia", "Ranking docente", "Datos"])
with t1:
    if not pr.empty:
        vista = pr.assign(
            **{
                "% Puntualidad": (pr["puntualidad"] * 100).round(2),
                "% de las incidencias": (pr["pct_del_total_incidencias"] * 100).round(1),
            }
        )[["categoria", "sesiones", "% Puntualidad", "incidencias_puntualidad", "% de las incidencias"]]
        vista.columns = ["Unidad", "Sesiones", "% Puntualidad", "Sesiones con incidencia", "% de las incidencias"]
        st.dataframe(
            vista, use_container_width=True, hide_index=True,
            column_config={
                "% Puntualidad": st.column_config.NumberColumn(format="%.2f%%"),
                "% de las incidencias": st.column_config.NumberColumn(format="%.1f%%"),
                "Sesiones": st.column_config.NumberColumn(format="%d"),
                "Sesiones con incidencia": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.caption(f"Ordenado por volumen, no por porcentaje. Los primeros tres concentran "
                   f"{pr.head(3)['pct_del_total_incidencias'].sum():.0%} de las incidencias de puntualidad.")
with t2:
    rk = metrics.ranking_docente(f, AJ)
    conc = metrics.concentracion_docente(f, AJ)
    if conc:
        st.caption(
            f"{conc['docentes']:,} docentes en la selección · {conc['pct_con_incidencia']:.0%} registra al menos "
            f"una incidencia · el 10% con más incidencias concentra {conc['top10_pct_incidencias']:.0%} del total "
            f"· {conc['reincidentes_3mas']:,} con tres o más."
        )
    if not rk.empty:
        vista = rk.assign(**{"% Puntualidad": (rk["puntualidad"] * 100).round(2)})[
            ["categoria", "sesiones", "% Puntualidad", "incidencias_puntualidad", "faltas"]]
        vista.columns = ["Profesor", "Sesiones", "% Puntualidad", "Retraso o salida previa", "Faltas"]
        st.dataframe(
            vista, use_container_width=True, hide_index=True,
            column_config={"% Puntualidad": st.column_config.NumberColumn(format="%.2f%%")},
        )
        st.caption(f"Mínimo {AJ.min_sesiones_profesor} sesiones. Insumo de seguimiento con el director "
                   "de la unidad, no de evaluación automática: el indicador mide registro de check, "
                   "no docencia impartida.")
    else:
        st.info("No hay columna de profesor, o ningún docente alcanza el mínimo de sesiones.")
with t3:
    st.dataframe(f.head(500), use_container_width=True, hide_index=True)
    st.download_button("Descargar la selección (CSV)", f.to_csv(index=False).encode("utf-8"),
                       "registro_filtrado.csv", "text/csv")

# --------------------------------------------------------------------------- lectura ejecutiva
st.markdown("#### Lectura ejecutiva")
st.caption("Generada a partir de los datos de la selección actual.")
hallazgos = metrics.lectura_ejecutiva(f, AJ, k)
cols = st.columns(2)
for i, (titulo, detalle, accion) in enumerate(hallazgos):
    with cols[i % 2]:
        st.markdown(
            f'<div class="hall"><div class="t">{titulo}</div><div class="d">{detalle}</div>'
            f'<div class="a">→ {accion}</div></div>',
            unsafe_allow_html=True,
        )

st.divider()
st.caption(
    f"Fuente: registro diario · códigos {AJ.excluir} excluidos por indicación del área funcional · "
    f"% Puntualidad calculada sobre Asistencia Global · el indicador mide registro de check, "
    f"no docencia impartida."
)
