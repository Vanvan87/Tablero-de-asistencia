"""Carga y validacion de config.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent

PALETA = {
    "navy": "#0B1F3A",
    "navy2": "#12294D",
    "steel": "#3B5A80",
    "accent": "#E8A33D",
    "teal": "#2FA79A",
    "rojo": "#D4534B",
    "verde": "#4C9A6E",
    "ambar": "#E0A62E",
    "ocre": "#B5651D",
    "muted": "#6B7E93",
    "linea": "#E2E8F0",
    "fondo": "#EEF2F6",
}

COLOR_CODIGO = {
    0: PALETA["verde"],
    1: PALETA["ambar"],
    2: PALETA["ocre"],
    4: PALETA["rojo"],
    5: PALETA["accent"],
    6: PALETA["teal"],
    8: PALETA["muted"],
    9: PALETA["steel"],
}


@dataclass
class Ajustes:
    fuente: str
    hoja: str | None
    columnas: dict[str, str | None]
    codigos: dict[int, str]
    excluir: list[int]
    codigos_puntualidad: list[int]
    codigo_falta: int
    meta_puntualidad: float
    umbral_verde: float
    min_sesiones_profesor: int
    min_sesiones_departamento: int
    institucion: str
    area: str
    titulo: str
    crudo: dict[str, Any] = field(default_factory=dict)

    @property
    def ruta_fuente(self) -> Path:
        p = Path(self.fuente)
        return p if p.is_absolute() else RAIZ / p

    def color(self, valor: float | None) -> str:
        """Semaforo estandar para un porcentaje de puntualidad (0-1)."""
        if valor is None:
            return PALETA["muted"]
        if valor < self.meta_puntualidad:
            return PALETA["rojo"]
        if valor < self.umbral_verde:
            return PALETA["ambar"]
        return PALETA["verde"]


def cargar_ajustes(ruta: Path | str | None = None) -> Ajustes:
    ruta = Path(ruta) if ruta else RAIZ / "config.yaml"
    with open(ruta, encoding="utf-8") as fh:
        d = yaml.safe_load(fh)
    return Ajustes(
        fuente=d.get("fuente", "data/registro_demo.csv"),
        hoja=d.get("hoja"),
        columnas=d.get("columnas", {}),
        codigos={int(k): v for k, v in (d.get("codigos") or {}).items()},
        excluir=[int(x) for x in (d.get("excluir") or [])],
        codigos_puntualidad=[int(x) for x in (d.get("codigos_puntualidad") or [1, 2])],
        codigo_falta=int(d.get("codigo_falta", 4)),
        meta_puntualidad=float(d.get("meta_puntualidad", 0.95)),
        umbral_verde=float(d.get("umbral_verde", 0.98)),
        min_sesiones_profesor=int(d.get("min_sesiones_profesor", 30)),
        min_sesiones_departamento=int(d.get("min_sesiones_departamento", 100)),
        institucion=d.get("institucion", "UDEM"),
        area=d.get("area", "Escolar y Registro Academico"),
        titulo=d.get("titulo", "Puntualidad y Asistencia Docente"),
        crudo=d,
    )
