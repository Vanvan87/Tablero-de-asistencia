"""Genera data/registro_demo.csv: datos sinteticos con la misma forma que el
registro real, para que el tablero corra antes de conectar el archivo de verdad.

    python scripts/generar_demo.py

NO son datos de la universidad. Sirven solo para validar que todo funciona.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

RNG = np.random.default_rng(26)

PERIODOS = ["PR-22", "OT-22", "PR-23", "OT-23", "PR-24", "OT-24", "PR-25", "OT-25", "PR-26"]
INICIOS = {"PR": "01-12", "OT": "08-10"}

ESTRUCTURA = {
    "VIAC": {
        "Escuela de Negocios": ["Administración", "Economía", "Mercadotecnia"],
        "Escuela de Ingeniería y Tecnologías": ["Ciencias Básicas", "Computación"],
        "Escuela de Arquitectura": ["Arquitectura", "Diseño Urbano"],
        "Facultad de Derecho y Ciencias Sociales": ["Derecho", "Ciencias Sociales"],
        "Escuela de Medicina": ["Ciencias Clínicas", "Crecimiento y Desarrollo"],
        "Escuela de Psicología": ["Psicología"],
        "Escuela de Odontología": ["Odontología"],
        "Escuela de Ciencias Aliadas de la Salud": ["Nutrición", "Fisioterapia"],
        "Facultad de Educación y Humanidades": ["Educación", "Letras"],
        "Escuela de Arte y Diseño": ["Arte", "Diseño"],
    },
    "VICSA": {
        "Dirección de Bienestar y Atención Estudiantil": ["Bienestar"],
        "Centro de Asesoría, Tutoría y Consejería Estudiantil": ["Asesoría y Tutoría"],
        "Centro de Equidad de Género e Inclusión": ["Centro de Equidad de Género"],
        "Dirección de Formación Deportiva y Liderazgo": ["Deportes", "Liderazgo"],
    },
    "VIFI": {
        "Dirección de Identidad y Principios Institucionales": ["Identidad"],
        "Dirección de Programas Internacionales": ["Internacional"],
    },
}

# Sesgo base por departamento (puntos porcentuales sobre la media)
SESGO = {"Ciencias Clínicas": -4.6, "Crecimiento y Desarrollo": -2.8, "Asesoría y Tutoría": -2.9,
         "Derecho": -1.6, "Arquitectura": -1.0, "Ciencias Básicas": -0.6, "Administración": -0.3,
         "Economía": -0.3, "Identidad": 2.2, "Nutrición": 1.9, "Deportes": 1.7}

CODIGOS = [0, 1, 2, 4, 5, 6, 8, 9, 10]


def calendario(periodo: str) -> list[pd.Timestamp]:
    ciclo, anio = periodo.split("-")
    inicio = pd.Timestamp(f"20{anio}-{INICIOS[ciclo]}")
    inicio -= pd.Timedelta(days=int(inicio.weekday()))  # cae en lunes
    dias = []
    for semana in range(16):
        for d in range(6):  # lunes a sabado
            dias.append(inicio + pd.Timedelta(days=semana * 7 + d))
    return dias


def main() -> None:
    filas = []
    profesores = [f"Profesor {i:03d}" for i in range(1, 421)]
    # unos pocos docentes concentran incidencias, como suele pasar en la realidad
    propension = RNG.beta(1.6, 9, len(profesores))
    prof_dep = {p: None for p in profesores}
    pares = [(v, e, d) for v, esc in ESTRUCTURA.items() for e, deps in esc.items() for d in deps]
    for i, p in enumerate(profesores):
        prof_dep[p] = pares[i % len(pares)]

    for pi, periodo in enumerate(PERIODOS):
        dias = calendario(periodo)
        mejora = pi * 0.12  # tendencia lenta de mejora entre periodos
        for p in profesores:
            vic, esc, dep = prof_dep[p]
            n = int(RNG.integers(14, 34))
            for _ in range(n):
                fecha = dias[int(RNG.integers(0, len(dias)))]
                sabado = fecha.weekday() == 5
                semana = (fecha - dias[0]).days // 7 + 1
                base = 1.1 + SESGO.get(dep, 0) * -0.75 + propension[profesores.index(p)] * 13
                base += 3.1 if sabado else 0
                base += 1.9 if semana >= 15 else 0
                base -= mejora * 0.9
                pr_inc = np.clip(base, 0.5, 45) / 100
                r = RNG.random()
                if r < pr_inc * 0.47:
                    cod = 1
                elif r < pr_inc * 0.94:
                    cod = 2
                elif r < pr_inc * 1.20:
                    cod = 4
                elif r < pr_inc * 1.40:
                    cod = 5
                elif r < pr_inc * 1.57:
                    cod = 6
                elif r < pr_inc * 1.70:
                    cod = 9
                elif r < pr_inc * 1.75:
                    cod = 8
                elif r < pr_inc * 1.78:
                    cod = 10
                else:
                    cod = 0
                hora = int(RNG.choice([7, 8, 9, 10, 11, 13, 15, 17, 19]))
                retraso = 0 if cod not in (1,) else int(RNG.integers(5, 26))
                filas.append(
                    {
                        "Periodo": periodo,
                        "Fecha": fecha.date().isoformat(),
                        "CRN": f"{RNG.integers(10000, 99999)}",
                        "Profesor": p,
                        "Vicerrectoria": vic,
                        "Escuela": esc,
                        "Departamento": dep,
                        "Codigo": cod,
                        "HoraProgramada": f"{hora:02d}:00",
                        "CheckEntrada": f"{hora:02d}:{retraso:02d}",
                        "CheckSalida": f"{hora + 1:02d}:{0 if cod != 2 else RNG.integers(35, 55):02d}",
                    }
                )

    df = pd.DataFrame(filas)
    salida = RAIZ / "data" / "registro_demo.csv"
    salida.parent.mkdir(exist_ok=True)
    df.to_csv(salida, index=False)

    sin10 = df[df["Codigo"] != 10]
    asist = len(sin10) - (sin10["Codigo"] == 4).sum()
    punt = (asist - sin10["Codigo"].isin([1, 2]).sum()) / asist
    print(f"{len(df):,} filas -> {salida}")
    print(f"Periodos: {df['Periodo'].nunique()} · Profesores: {df['Profesor'].nunique()}")
    print(f"% Puntualidad del demo: {punt:.2%}")


if __name__ == "__main__":
    main()
