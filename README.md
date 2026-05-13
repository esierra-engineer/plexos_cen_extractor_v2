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

## Guía detallada para comprender inputs/outputs y validar manualmente `main.py`

Esta guía permite revisar manualmente si el resultado de `python main.py` coincide con el escenario PLEXOS base.

### 1) Qué hace `main.py` en términos de negocio

`main.py` ejecuta 3 pasos:

1. **Lee insumos operativos** desde CSV/XML de `data/DATOS20260509`.
2. **Extrae resultados de simulación** desde XML/BIN de la solución en `data/Model PRGdia_Full_Definitivo Solution`.
3. **Escribe un Excel consolidado** en `reports/cen_revision_diaria.xlsx` para revisión diaria.

### 2) Entradas esperadas y su rol en la revisión

#### 2.1 Insumos (`extract_inputs`)

- `data/DATOS20260509/Gen_UnitsOut.csv`  
  Se etiqueta como `input_type = mantenimiento_fallas`.

- `data/DATOS20260509/Hydro_WaterFlows.csv`  
  Se etiqueta como `input_type = hidrologia`.

- `data/DATOS20260509/DBSEN_PRGDIARIO.xml`  
  Se recorren nodos `Object`/`Property` y se arma:
  - `object`
  - `property`
  - `value`
  - `input_type = restriccion_operativa`

Resultado intermedio: un DataFrame único con la unión de estas 3 fuentes, exportado luego a la hoja `inputs_mantenimiento_hidro`.

#### 2.2 Resultados de solución (`extract_outputs`)

- `data/Model PRGdia_Full_Definitivo Solution/Model PRGdia_Full_Definitivo Solution.xml`  
  Se parsean tablas `t_*` para reconstruir metadatos:
  - clases (`t_class`)
  - objetos (`t_object`)
  - propiedades (`t_property`)
  - membresías (`t_membership`)
  - claves (`t_key`)
  - índices de series (`t_key_index`)
  - secuencias de fase/período (`t_phase_*`, `t_period_*`)

- `data/Model PRGdia_Full_Definitivo Solution/t_data_0.BIN`  
  Se lee como arreglo `float64` y se cruza con `t_key_index` para expandir series temporales.

Solo se consideran propiedades objetivo:
- `generation`
- `price`
- `flow`
- `demand`

Se genera un DataFrame con columnas:
- `key_id`
- `period` (convertido a datetime)
- `class`
- `object`
- `property`
- `value`

### 3) Cómo se traducen los resultados al Excel final

En `export_report`, el DataFrame de outputs se divide por clase:

- `class == Generator` → hoja `generacion_centrales`
- `class == Node` → hoja `cmg_y_demanda_barras`
- `class == Line` → hoja `flujo_lineas`

Y los insumos concatenados van a:

- hoja `inputs_mantenimiento_hidro`

Si una clase no coincide con `Generator`, `Node` o `Line`, no se publica en esas 3 hojas.

### 4) Procedimiento de chequeo manual recomendado

#### Paso A: Verificar que las rutas base existen

Confirma existencia de:
- `data/DATOS20260509/Gen_UnitsOut.csv`
- `data/DATOS20260509/Hydro_WaterFlows.csv`
- `data/DATOS20260509/DBSEN_PRGDIARIO.xml`
- `data/Model PRGdia_Full_Definitivo Solution/Model PRGdia_Full_Definitivo Solution.xml`
- `data/Model PRGdia_Full_Definitivo Solution/t_data_0.BIN`

Si falta alguno, el reporte saldrá incompleto (o vacío en la parte afectada).

#### Paso B: Ejecutar y abrir el reporte

1. Ejecutar `python main.py`.
2. Abrir `reports/cen_revision_diaria.xlsx`.
3. Validar que existan 4 hojas:
   - `generacion_centrales`
   - `cmg_y_demanda_barras`
   - `flujo_lineas`
   - `inputs_mantenimiento_hidro`

#### Paso C: Chequeo manual de insumos (`inputs_mantenimiento_hidro`)

1. Buscar filas con:
   - `input_type = mantenimiento_fallas` y contrastar contra `Gen_UnitsOut.csv`.
   - `input_type = hidrologia` y contrastar contra `Hydro_WaterFlows.csv`.
   - `input_type = restriccion_operativa` y contrastar contra nodos `Object/Property` del XML.
2. Confirmar que las columnas clave esperadas existan y no estén vacías en forma masiva.

#### Paso D: Chequeo manual de outputs por clase

1. `generacion_centrales`:
   - Revisar que `class` sea `Generator`.
   - Verificar que `property` sea de tipo generación (`Generation` en naming típico del XML).
2. `cmg_y_demanda_barras`:
   - Revisar `class = Node`.
   - Verificar propiedades ligadas a `Price`/`Demand`.
3. `flujo_lineas`:
   - Revisar `class = Line`.
   - Verificar propiedades ligadas a `Flow`.

En todas las hojas:
- `period` debe ser fecha-hora válida.
- `value` debe ser numérico y consistente en magnitud/unidad con la corrida.

#### Paso E: Trazabilidad de una muestra (control más confiable)

Para 3-5 registros por hoja:
1. Tomar `object`, `property`, `period`, `value` en Excel.
2. Buscar la `property_id` en `t_property` y el objeto en `t_object` (XML de solución).
3. Revisar su `key_id` en `t_key`.
4. Revisar `position`/`length`/`period_offset` en `t_key_index`.
5. Confirmar que el valor extraído desde `t_data_0.BIN` (float64) coincide con `value` reportado.

Este chequeo asegura que el mapeo XML↔BIN↔Excel sea correcto.

### 5) Señales típicas de desalineación a revisar

- Hoja vacía cuando sí existen datos en el escenario:
  - posible clase no mapeada (`Generator/Node/Line`) o propiedad fuera del set objetivo (`generation/price/flow/demand`).
- `period` nulo o masivamente vacío:
  - posible desajuste en tablas `t_phase_*` / `t_period_*` o en `period_type_id`.
- Valores corridos o incoherentes:
  - revisar `position` (bytes), `length` y `period_offset` en `t_key_index`.

### 6) Criterio práctico de aceptación manual

Se considera correcto para revisión diaria si:

1. Las 4 hojas existen.
2. No hay vacíos masivos inesperados.
3. La muestra trazada (Paso E) coincide entre fuente y Excel.
4. La distribución general de magnitudes y timestamps es consistente con la corrida PLEXOS esperada.

## Compatibilidad

- Linux y Windows (sin dependencias de Access/ODBC).
