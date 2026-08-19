"""Metricas de negocio.

Definiciones (alineadas a las medidas DAX del modelo original):
    Asistencia Global = sesiones - faltas
    % Puntualidad     = (Asistencia Global - retraso inicial - salida previa) / Asistencia Global
    Incidencia        = cualquier sesion con codigo distinto de 0
    Incidencia de puntualidad = codigos 1 y 2 (los accionables)
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import Ajustes


@dataclass
class Kpis:
    sesiones: int
    asistencia_global: int
    faltas: int
    retraso: int
    salida: int
    aviso_autorizacion: int
    incidencias: int
    incidencias_puntualidad: int
    puntualidad: float
    pct_faltas: float
    pct_retraso: float
    pct_salida: float
    minutos_perdidos: float | None
    unidades: int
    unidades_bajo_meta: int
    dispersion_pp: float

    @property
    def brecha_pp(self) -> float:
        return self.puntualidad * 100 - 95.0


def _p(num: int, den: int) -> float:
    return num / den if den else 0.0


def kpis(df: pd.DataFrame, aj: Ajustes, dim_unidad: str = "escuela") -> Kpis:
    total = len(df)
    faltas = int((df["codigo"] == aj.codigo_falta).sum())
    asist = total - faltas
    retraso = int((df["codigo"] == aj.codigos_puntualidad[0]).sum())
    salida = int((df["codigo"] == aj.codigos_puntualidad[1]).sum())
    inc_punt = retraso + salida
    incidencias = int((df["codigo"] != 0).sum())
    justificadas = int(df["codigo"].isin([5, 9]).sum())

    minutos = None
    if "minutos_retraso" in df.columns and df["minutos_retraso"].notna().any():
        minutos = float(df["minutos_retraso"].sum(skipna=True))

    unidades = bajo = 0
    dispersion = 0.0
    if dim_unidad in df.columns and df[dim_unidad].notna().any():
        tabla = por_dimension(df, dim_unidad, aj)
        unidades = len(tabla)
        bajo = int((tabla["puntualidad"] < aj.meta_puntualidad).sum())
        if unidades > 1:
            dispersion = float((tabla["puntualidad"].max() - tabla["puntualidad"].min()) * 100)

    return Kpis(
        sesiones=total,
        asistencia_global=asist,
        faltas=faltas,
        retraso=retraso,
        salida=salida,
        aviso_autorizacion=justificadas,
        incidencias=incidencias,
        incidencias_puntualidad=inc_punt,
        puntualidad=_p(asist - inc_punt, asist),
        pct_faltas=_p(faltas, total),
        pct_retraso=_p(retraso, asist),
        pct_salida=_p(salida, asist),
        minutos_perdidos=minutos,
        unidades=unidades,
        unidades_bajo_meta=bajo,
        dispersion_pp=dispersion,
    )


def por_dimension(df: pd.DataFrame, columna: str, aj: Ajustes, minimo: int = 0) -> pd.DataFrame:
    """Agrega por escuela, departamento, profesor, periodo, dia... con las
    mismas definiciones. 'incidencias_puntualidad' es el volumen accionable."""
    if columna not in df.columns:
        return pd.DataFrame()
    g = df.dropna(subset=[columna]).groupby(columna, dropna=True)
    t = pd.DataFrame(
        {
            "sesiones": g.size(),
            "faltas": g["codigo"].apply(lambda s: (s == aj.codigo_falta).sum()),
            "retraso": g["codigo"].apply(lambda s: (s == aj.codigos_puntualidad[0]).sum()),
            "salida": g["codigo"].apply(lambda s: (s == aj.codigos_puntualidad[1]).sum()),
        }
    )
    t["asistencia_global"] = t["sesiones"] - t["faltas"]
    t["incidencias_puntualidad"] = t["retraso"] + t["salida"]
    t["puntualidad"] = (t["asistencia_global"] - t["incidencias_puntualidad"]).div(
        t["asistencia_global"].replace(0, pd.NA)
    )
    t["pct_faltas"] = t["faltas"] / t["sesiones"]
    if "minutos_retraso" in df.columns:
        t["minutos_perdidos"] = g["minutos_retraso"].sum(min_count=1)
    t = t[t["sesiones"] >= minimo]
    return t.reset_index().rename(columns={columna: "categoria"})


def tendencia_periodo(df: pd.DataFrame, aj: Ajustes) -> pd.DataFrame:
    t = por_dimension(df, "periodo", aj)
    if t.empty or "orden_periodo" not in df.columns:
        return t
    orden = df.groupby("periodo")["orden_periodo"].min()
    t["orden"] = t["categoria"].map(orden)
    return t.sort_values("orden").reset_index(drop=True)


def composicion_codigos(df: pd.DataFrame, aj: Ajustes) -> pd.DataFrame:
    inc = df[df["codigo"] != 0]
    if inc.empty:
        return pd.DataFrame(columns=["codigo", "codigo_nombre", "sesiones", "pct_incidencias"])
    t = (
        inc.groupby(["codigo", "codigo_nombre"])
        .size()
        .reset_index(name="sesiones")
        .sort_values("sesiones", ascending=False)
    )
    t["pct_incidencias"] = t["sesiones"] / len(inc)
    t["pct_total"] = t["sesiones"] / len(df)
    return t.reset_index(drop=True)


def prioridad(df: pd.DataFrame, aj: Ajustes, columna: str = "departamento") -> pd.DataFrame:
    """Tabla de decisión: volumen de incidencia contra desempeño."""
    t = por_dimension(df, columna, aj, minimo=aj.min_sesiones_departamento)
    if t.empty:
        return t
    total_inc = t["incidencias_puntualidad"].sum()
    t["pct_del_total_incidencias"] = t["incidencias_puntualidad"] / total_inc if total_inc else 0
    t["bajo_meta"] = t["puntualidad"] < aj.meta_puntualidad
    return t.sort_values("incidencias_puntualidad", ascending=False).reset_index(drop=True)


ORDEN_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def mapa_dia_hora(df: pd.DataFrame, aj: Ajustes, min_sesiones: int = 30) -> pd.DataFrame:
    """Matriz día × franja horaria con % puntualidad. Celdas con pocas sesiones
    van vacías para no leer ruido como patrón."""
    if not {"dia_semana", "franja"} <= set(df.columns):
        return pd.DataFrame()
    base = df.dropna(subset=["dia_semana", "franja"])
    if base.empty:
        return pd.DataFrame()
    g = base.groupby(["dia_semana", "franja"])
    t = pd.DataFrame({
        "sesiones": g.size(),
        "faltas": g["codigo"].apply(lambda s: (s == aj.codigo_falta).sum()),
        "inc": g["codigo"].apply(lambda s: s.isin(aj.codigos_puntualidad).sum()),
    }).reset_index()
    t["asist"] = t["sesiones"] - t["faltas"]
    t["puntualidad"] = (t["asist"] - t["inc"]).div(t["asist"].replace(0, pd.NA))
    t.loc[t["sesiones"] < min_sesiones, "puntualidad"] = pd.NA
    t["dia_semana"] = pd.Categorical(t["dia_semana"], categories=ORDEN_DIAS, ordered=True)
    return t.sort_values(["dia_semana", "franja"]).reset_index(drop=True)


def tendencia_semana(df: pd.DataFrame, aj: Ajustes) -> pd.DataFrame:
    t = por_dimension(df, "semana", aj)
    if t.empty:
        return t
    t["orden"] = pd.to_numeric(t["categoria"], errors="coerce")
    t = t.dropna(subset=["orden"]).sort_values("orden").reset_index(drop=True)
    t["categoria"] = t["orden"].astype(int).astype(str)
    return t


def concentracion_docente(df: pd.DataFrame, aj: Ajustes) -> dict | None:
    """Qué tan concentrado está el problema: si pocos docentes explican mucho,
    la intervencion es dirigida; si esta repartido, es de proceso."""
    if "profesor" not in df.columns or df["profesor"].isna().all():
        return None
    t = por_dimension(df, "profesor", aj)
    if t.empty:
        return None
    t = t.sort_values("incidencias_puntualidad", ascending=False)
    total = t["incidencias_puntualidad"].sum()
    if not total:
        return None
    n = len(t)
    top10 = max(1, round(n * 0.10))
    con_incidencia = int((t["incidencias_puntualidad"] > 0).sum())
    return {
        "docentes": n,
        "con_incidencia": con_incidencia,
        "pct_con_incidencia": con_incidencia / n,
        "top10_pct_docentes": top10 / n,
        "top10_pct_incidencias": t.head(top10)["incidencias_puntualidad"].sum() / total,
        "reincidentes_3mas": int((t["incidencias_puntualidad"] >= 3).sum()),
    }


def ranking_docente(df: pd.DataFrame, aj: Ajustes, n: int = 15) -> pd.DataFrame:
    t = por_dimension(df, "profesor", aj, minimo=aj.min_sesiones_profesor)
    if t.empty:
        return t
    return t.sort_values(["puntualidad", "sesiones"], ascending=[True, False]).head(n).reset_index(drop=True)


def lectura_ejecutiva(df: pd.DataFrame, aj: Ajustes, k: Kpis) -> list[tuple[str, str, str]]:
    """Hallazgos redactados a partir de los datos, no fijos. (titulo, hallazgo, accion)"""
    out: list[tuple[str, str, str]] = []
    meta = aj.meta_puntualidad * 100

    # 1. Concentracion del volumen
    pr = prioridad(df, aj)
    if len(pr) >= 3:
        top3 = pr.head(3)
        share = top3["pct_del_total_incidencias"].sum()
        cumplen = top3[~top3["bajo_meta"]]["categoria"].tolist()
        detalle = ", ".join(f"{r.categoria} ({r.incidencias_puntualidad:,})" for r in top3.itertuples())
        nota = (
            f" {' y '.join(cumplen)} incluso cumplen la meta y aun así encabezan el volumen."
            if len(cumplen) else ""
        )
        out.append((
            "El volumen no vive donde vive el porcentaje",
            f"{detalle} concentran {share:.0%} de las incidencias de puntualidad.{nota}",
            "Priorizar por volumen: una mejora de un punto aquí vale más que corregir un área pequeña.",
        ))

    # 2. Peor dia
    if "dia_semana" in df.columns:
        d = por_dimension(df, "dia_semana", aj, minimo=50).dropna(subset=["puntualidad"])
        if len(d) >= 2:
            peor = d.loc[d["puntualidad"].idxmin()]
            resto = d[d["categoria"] != peor["categoria"]]["puntualidad"].mean()
            brecha = (resto - peor["puntualidad"]) * 100
            if brecha >= 1:
                out.append((
                    f"{peor['categoria']} es el punto ciego",
                    f"{peor['puntualidad']:.2%} contra {resto:.2%} del resto de la semana: "
                    f"{brecha:.1f} puntos de brecha sobre {peor['sesiones']:,} sesiones.",
                    "Revisar logística del día: apertura de aulas, acceso y horario de registro.",
                ))

    # 3. Composicion de la incidencia
    comp = composicion_codigos(df, aj)
    if not comp.empty:
        punt = comp[comp["codigo"].isin(aj.codigos_puntualidad)]["pct_incidencias"].sum()
        falta = comp[comp["codigo"] == aj.codigo_falta]["pct_incidencias"].sum()
        if punt > falta:
            out.append((
                "El incumplimiento está en los bordes de la clase",
                f"Retraso inicial y salida previa son {punt:.0%} de las incidencias; "
                f"la falta completa es {falta:.0%}.",
                "No es ausentismo: es arranque y cierre. Atacarlo con el proceso de check, no con política de faltas.",
            ))

    # 4. Tendencia entre periodos
    tp = tendencia_periodo(df, aj)
    if len(tp) >= 2:
        ult, prev = tp.iloc[-1], tp.iloc[-2]
        delta = (ult["puntualidad"] - prev["puntualidad"]) * 100
        direccion = "mejora" if delta > 0 else "cae"
        out.append((
            f"{ult['categoria']} {direccion} {abs(delta):.2f} pp contra {prev['categoria']}",
            f"{prev['puntualidad']:.2%} a {ult['puntualidad']:.2%} sobre {ult['sesiones']:,} sesiones. "
            f"Promedio histórico de la serie: {tp['puntualidad'].mean():.2%}.",
            "Sostener la comparación periodo contra periodo como indicador de tablero, no la foto del semestre.",
        ))

    # 5. Concentracion docente
    c = concentracion_docente(df, aj)
    if c and c["top10_pct_incidencias"] > 0.3:
        out.append((
            "El problema está concentrado en pocos docentes",
            f"El 10% de los profesores acumula {c['top10_pct_incidencias']:.0%} de las incidencias. "
            f"{c['reincidentes_3mas']:,} docentes tienen 3 o mas en el periodo.",
            "Intervención dirigida con esos casos antes que una campaña general.",
        ))

    # 5b. Faltas por encima de lo tolerable
    if k.pct_faltas >= 0.02:
        out.append((
            f"Las faltas son {k.pct_faltas:.2%} del total",
            f"{k.faltas:,} sesiones sin impartir y sin reponer. A ~1.5 horas por sesión "
            f"equivalen a unas {k.faltas * 1.5:,.0f} horas de clase no dadas.",
            "Separar del tema de puntualidad: la falta requiere protocolo de reposición, no recordatorio de check.",
        ))

    # 5c. Franja horaria crítica
    mapa = mapa_dia_hora(df, aj)
    if not mapa.empty and mapa["puntualidad"].notna().any():
        peor_f = mapa.loc[mapa["puntualidad"].idxmin()]
        prom = mapa["puntualidad"].mean()
        brecha_f = (prom - peor_f["puntualidad"]) * 100
        if brecha_f >= 1.5:
            out.append((
                f"La franja crítica es {peor_f['dia_semana']} {peor_f['franja']}",
                f"{peor_f['puntualidad']:.2%} contra {prom:.2%} promedio de la parrilla, "
                f"sobre {peor_f['sesiones']:,.0f} sesiones programadas en ese bloque.",
                "Antes de mover horarios, verificar traslados entre edificios y empalmes de la plantilla en ese bloque.",
            ))

    # 6. Unidades bajo meta
    if k.unidades_bajo_meta:
        out.append((
            f"{k.unidades_bajo_meta} de {k.unidades} unidades cierran bajo meta",
            f"Dispersión de {k.dispersion_pp:.2f} pp entre la mejor y la peor unidad, "
            f"con la meta institucional en {meta:.0f}%.",
            "Acordar plan por unidad con el director correspondiente y fecha de revisión.",
        ))
    return out
