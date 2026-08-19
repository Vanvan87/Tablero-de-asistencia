# Tablero ejecutivo — Puntualidad y Asistencia Docente

Aplicación en Streamlit para la Dirección de Escolar y Registro Académico. Lee el
registro diario de sesiones y responde tres preguntas: **si cumplimos la meta**,
**dónde está el volumen del problema** y **qué hacer al respecto**.

---

## Arrancar en local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/generar_demo.py   # datos sintéticos, opcional
streamlit run app.py
```

Abre `http://localhost:8501`.

## Publicar en Streamlit Cloud

1. Sube esta carpeta a un repositorio de GitHub.
2. En [share.streamlit.io](https://share.streamlit.io) → **New app**, elige el repo,
   la rama y `app.py` como *main file*.
3. Deploy. Streamlit Cloud instala `requirements.txt` automáticamente.

**Sobre los datos en la nube.** El repositorio no debe contener el registro real:
`.gitignore` ya bloquea los `.xlsx` y `.csv` de `data/` (salvo el demo). En
producción, la app arranca con el demo y quien la usa **sube el archivo real desde
la barra lateral**; ese archivo vive solo en la sesión y no se guarda en el
servidor. Si el tablero va a ser público, considera protegerlo con la opción de
acceso privado de Streamlit Cloud: el ranking docente contiene nombres.

---

## Conectar tu archivo

Todo se configura en `config.yaml`, sin tocar código:

```yaml
fuente: data/registro_diario.xlsx
columnas:
  periodo: Periodo
  fecha: Fecha
  codigo: Codigo
  profesor: Profesor
  escuela: Escuela
  departamento: DEPTO
```

La app además intenta detectar las columnas sola, ignorando acentos, mayúsculas y
espacios: si tu columna se llama `Depto.` o `DEPARTAMENTO`, la encuentra. La única
obligatoria es la del **código**; el resto degrada con elegancia (sin columna de
profesor, la pestaña de ranking simplemente avisa que falta).

### Formato del periodo

Se espera `PR-26`, `OT-25`, etc. El orden cronológico se calcula solo
(`PR-22` → 221, `OT-22` → 222), así que la tendencia no queda en orden alfabético,
que pondría OT antes que PR dentro del mismo año.

### Minutos perdidos (opcional)

Si existen `HoraProgramada` y `CheckEntrada`, la app calcula el tiempo lectivo
comprometido. Es la métrica que traduce "1.5% de retraso" a horas de clase, que es
el lenguaje en que se discute presupuesto. Se descartan diferencias mayores a 180
minutos por considerarse error de captura.

---

## Definiciones

| Métrica | Fórmula |
|---|---|
| Asistencia Global | sesiones − faltas |
| % Puntualidad | (Asistencia Global − retraso inicial − salida previa) ÷ Asistencia Global |
| Sesiones con incidencia | cualquier código distinto de 0 |
| Incidencia de puntualidad | códigos 1 y 2, los accionables |
| Volumen de incidencia | retraso + salida previa **en número absoluto** |

La última es la que cambia decisiones. Un departamento con 96.5% y 8,000 sesiones
genera más incidencias que uno con 92% y 400, aunque el ranking por porcentaje diga
lo contrario. Por eso la tabla principal y la matriz de prioridad ordenan por
volumen.

---

## Estructura

```
app.py                  interfaz y layout
config.yaml             columnas, catálogo de códigos, umbrales
src/config.py           carga de configuración y paleta
src/data.py             lectura, detección de columnas, normalización
src/metrics.py          KPIs, agregados y lectura ejecutiva automática
src/charts.py           gráficos Plotly
scripts/generar_demo.py datos sintéticos de prueba
```

Para cambiar la meta institucional, los umbrales del semáforo o el mínimo de
sesiones de un docente para aparecer en el ranking, edita `config.yaml`.

---

## Advertencias de interpretación

- El indicador mide **registro de check**, no docencia impartida. Una falla de
  sistema se ve igual que una impuntualidad; conviene decirlo en cualquier reporte
  que salga de aquí.
- El ranking docente es insumo de seguimiento con el director de la unidad, no de
  evaluación automática de personal.
- Los códigos excluidos se declaran en `config.yaml` (`excluir: [10]`) y la app
  reporta cuántas sesiones descartó en el panel de calidad del dato.
