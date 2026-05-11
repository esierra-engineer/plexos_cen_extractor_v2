# cen plexos daily extraction tool

Herramienta en Python para extraer insumos y resultados diarios de PLEXOS (CEN) y consolidarlos en Excel.

## Requisitos

- Python 3.11+
- Dependencias:
  - pandas
  - numpy
  - lxml
  - openpyxl

Instalación:

```bash
python -m pip install -r requirements.txt
```

## Estructura

```text
.
├── main.py
├── requirements.txt
├── src/
│   ├── config.py
│   ├── extract_inputs.py
│   ├── extract_outputs.py
│   └── excel_writer.py
├── reports/
│   └── cen_revision_diaria.xlsx
└── data/
    ├── DATOS20260509/
    └── Model PRGdia_Full_Definitivo Solution/
```

## Entrada esperada

- `data/DATOS20260509/Gen_UnitsOut.csv`
- `data/DATOS20260509/Hydro_WaterFlows.csv`
- `data/DATOS20260509/DBSEN_PRGDIARIO.xml`
- `data/Model PRGdia_Full_Definitivo Solution/Model PRGdia_Full_Definitivo Solution.xml`
- `data/Model PRGdia_Full_Definitivo Solution/t_data_0.BIN`

## Ejecución

```bash
python main.py
```

Salida:

- `reports/cen_revision_diaria.xlsx` con hojas:
  - `generacion_centrales`
  - `cmg_y_demanda_barras`
  - `flujo_lineas`
  - `inputs_mantenimiento_hidro`

## Compatibilidad

- Linux y Windows (sin dependencias de Access/ODBC).
