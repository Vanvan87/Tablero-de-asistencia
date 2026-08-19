"""Lectura del registro diario y normalizacion a un esquema interno estable.

El resto del proyecto solo conoce los nombres canonicos:
    periodo, orden_periodo, fecha, semana, dia_semana, codigo, codigo_nombre,
    profesor, escuela, departamento, vicerrectoria, crn,
    hora_programada, check_entrada, check_salida, minutos_retraso
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import IO

import pandas as pd

from .config import Ajustes

# Nombres alternativos que se aceptan para cada campo canonico.
ALIAS: dict[str, list[str]] = {
    "periodo": ["periodo", "period", "ciclo", "periodoacademico", "term"],
    "fecha": ["fechas", "fecha", "date", "fechasesion", "fechaclase"],
    "codigo": ["califfinal", "registro", "codigo", "code", "codigoregistro", "clave"],
    "profesor": ["nombre", "profesor", "docente", "maestro", "nombreprofesor"],
    "escuela": ["escuela", "school", "escueladireccion", "facultad"],
    "departamento": ["descdepto", "departamento", "depto", "dept"],
    "vicerrectoria": ["vicerrectoria", "vice", "vr"],
    "crn": ["crn", "nrc"],
    "materia": ["materia", "asignatura", "curso"],
    "tipo_curso": ["tipodecurso", "tipocurso", "modalidad"],
    "edificio": ["edificio", "campusedificio"],
    "salon": ["salon", "aula"],
    "dia_semana": ["dia", "diasemana"],
    "semana": ["semana", "semanaperiodo"],
    "hora_programada": ["hini", "horaprogramada", "horainicio", "horaclase"],
    "hora_fin": ["hfin", "horafin"],
    "check_entrada": ["checkentrada", "checkin"],
    "check_salida": ["checksalida", "checkout"],
}

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _resolver_columnas(df: pd.DataFrame, ajustes: Ajustes) -> tuple[dict[str, str], list[str]]:
    """Devuelve {campo_canonico: columna_real} y la lista de avisos."""
    disponibles = {_slug(c): c for c in df.columns}
    mapeo: dict[str, str] = {}
    avisos: list[str] = []

    for campo, alias in ALIAS.items():
        # 1) lo que diga config.yaml manda
        declarado = (ajustes.columnas or {}).get(campo)
        if declarado and _slug(declarado) in disponibles:
            mapeo[campo] = disponibles[_slug(declarado)]
            continue
        if declarado:
            avisos.append(f"En config.yaml pediste '{declarado}' para «{campo}» y no está en el archivo.")
        # 2) deteccion automatica
        for a in alias:
            if a in disponibles:
                mapeo[campo] = disponibles[a]
                break
        else:
            # 3) coincidencia parcial
            for slug, real in disponibles.items():
                if any(slug.startswith(a) or a in slug for a in alias):
                    mapeo[campo] = real
                    break

    for obligatorio in ("codigo",):
        if obligatorio not in mapeo:
            raise ValueError(
                f"No encuentro la columna de «{obligatorio}». Declárala en config.yaml "
                f"dentro de 'columnas'. Columnas del archivo: {list(df.columns)}"
            )
    return mapeo, avisos


def etiqueta_y_orden(valor) -> tuple[str, int]:
    """Normaliza el periodo a la etiqueta PR-AA / OT-AA y a un orden cronológico.

    Acepta dos formatos:
      * Institucional numérico AAAATT (202311): el año es el CICLO académico y
        TT el término. 202311 = Otoño 2022 (OT-22), 202621 = Primavera 2026
        (PR-26). El otoño arranca el ciclo, por eso OT lleva el año anterior.
      * Textual PR-26 / OT-25.
    El orden es un entero comparable entre ambos formatos.
    """
    s = str(valor).strip().upper()
    m = re.fullmatch(r"(\d{4})([123])\d", s)
    if m:
        ciclo, term = int(m.group(1)), int(m.group(2))
        if term == 1:                       # otoño del año anterior al ciclo
            return f"OT-{(ciclo - 1) % 100:02d}", (ciclo - 1) * 10 + 2
        if term == 2:                       # primavera del año del ciclo
            return f"PR-{ciclo % 100:02d}", ciclo * 10 + 1
        return f"VE-{ciclo % 100:02d}", (ciclo - 1) * 10 + 3   # verano
    m = re.search(r"(PR|OT|VE)\D*(\d{2,4})", s)
    if m:
        tipo, anio = m.group(1), int(m.group(2)) % 100
        return f"{tipo}-{anio:02d}", anio * 10 + {"PR": 1, "OT": 2, "VE": 3}[tipo]
    return s, 0


def _a_minutos(serie: pd.Series) -> pd.Series:
    """Convierte hora a minutos desde medianoche. Acepta datetime, texto
    ("07:30") o el entero institucional HMM/HHMM (700 = 7:00, 1430 = 14:30)."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie.dt.hour * 60 + serie.dt.minute
    num = pd.to_numeric(serie, errors="coerce")
    if num.notna().mean() > 0.8:
        return (num // 100) * 60 + (num % 100)
    conv = pd.to_datetime(serie.astype(str).str.strip(), errors="coerce", format="mixed")
    return conv.dt.hour * 60 + conv.dt.minute


def leer(origen: str | Path | IO[bytes], ajustes: Ajustes) -> tuple[pd.DataFrame, list[str]]:
    """Lee el archivo y devuelve (df normalizado, avisos de calidad)."""
    nombre = getattr(origen, "name", str(origen))
    if str(nombre).lower().endswith((".xlsx", ".xlsm", ".xls")):
        df = pd.read_excel(origen, sheet_name=ajustes.hoja or 0)
    else:
        df = pd.read_csv(origen)

    mapeo, avisos = _resolver_columnas(df, ajustes)
    out = pd.DataFrame(index=df.index)
    for campo, real in mapeo.items():
        out[campo] = df[real]

    # --- codigo -------------------------------------------------------------
    out["codigo"] = pd.to_numeric(out["codigo"], errors="coerce")
    if out["codigo"].isna().all():
        raise ValueError(
            f"La columna elegida para el código ('{mapeo['codigo']}') está vacía. "
            "Revisa 'columnas: codigo:' en config.yaml; en el registro de UDEM el "
            "código suele venir en 'CALIF FINAL'."
        )
    sin_codigo = int(out["codigo"].isna().sum())
    if sin_codigo:
        avisos.append(f"{sin_codigo:,} filas sin código legible: se descartan.")
        out = out[out["codigo"].notna()]
    out["codigo"] = out["codigo"].astype(int)

    desconocidos = sorted(set(out["codigo"]) - set(ajustes.codigos) - set(ajustes.excluir))
    if desconocidos:
        avisos.append(f"Códigos presentes en los datos y ausentes del catálogo: {desconocidos}.")

    excluidas = int(out["codigo"].isin(ajustes.excluir).sum())
    if excluidas:
        avisos.append(f"{excluidas:,} sesiones excluidas por código {ajustes.excluir}.")
        out = out[~out["codigo"].isin(ajustes.excluir)]
    out["codigo_nombre"] = out["codigo"].map(ajustes.codigos).fillna(
        out["codigo"].map(lambda c: f"Código {c}")
    )

    # --- fecha, día y semana -------------------------------------------------
    if "fecha" in out:
        out["fecha"] = pd.to_datetime(out["fecha"], errors="coerce")
    if "dia_semana" in out:
        # el archivo trae LUNES / MIÉRCOLES: normalizar a Lunes / Miércoles
        mapa = {_slug(d): d for d in DIAS}
        out["dia_semana"] = out["dia_semana"].map(lambda v: mapa.get(_slug(v), pd.NA))
    elif "fecha" in out:
        out["dia_semana"] = out["fecha"].dt.weekday.map(dict(enumerate(DIAS)))
    if "semana" in out:
        out["semana"] = pd.to_numeric(out["semana"], errors="coerce")
    elif "fecha" in out:
        out["semana"] = out.groupby(out.get("periodo", "todo"), dropna=False)["fecha"].transform(
            lambda s: ((s - s.min()).dt.days // 7 + 1) if s.notna().any() else pd.NA
        )
    # franja horaria para el análisis de horarios
    if "hora_programada" in out:
        mins = _a_minutos(out["hora_programada"])
        out["hora_num"] = (mins // 60).astype("Int64")
        out["franja"] = out["hora_num"].map(lambda h: f"{h:02d}:00" if pd.notna(h) else pd.NA)

    # --- periodo ------------------------------------------------------------
    if "periodo" in out:
        pares = {v: etiqueta_y_orden(v) for v in out["periodo"].dropna().unique()}
        out["orden_periodo"] = out["periodo"].map(lambda v: pares.get(v, ("", 0))[1])
        out["periodo"] = out["periodo"].map(lambda v: pares.get(v, (str(v), 0))[0])
        if (out["orden_periodo"] == 0).any():
            raros = sorted(set(out.loc[out["orden_periodo"] == 0, "periodo"]))[:5]
            avisos.append(f"Periodos con formato no reconocido (ni AAAATT ni PR-AA/OT-AA): {raros}.")
    else:
        out["periodo"] = "Todo el histórico"
        out["orden_periodo"] = 1
        avisos.append("No hay columna de periodo: el reporte se muestra como un solo bloque.")

    # --- minutos de retraso (opcional) --------------------------------------
    if {"hora_programada", "check_entrada"} <= set(out.columns):
        prog, real = _a_minutos(out["hora_programada"]), _a_minutos(out["check_entrada"])
        out["minutos_retraso"] = (real - prog).clip(lower=0)
        out.loc[out["minutos_retraso"] > 180, "minutos_retraso"] = pd.NA

    for texto in ("profesor", "escuela", "departamento", "vicerrectoria",
                  "materia", "tipo_curso", "edificio", "salon"):
        if texto in out:
            out[texto] = out[texto].astype(str).str.strip().replace({"nan": pd.NA, "": pd.NA})

    return out.reset_index(drop=True), avisos
