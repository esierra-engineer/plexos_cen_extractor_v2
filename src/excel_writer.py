from pathlib import Path

import pandas as pd


def export_report(outputs_df: pd.DataFrame, inputs_df: pd.DataFrame, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    generator_df = outputs_df[outputs_df["class"].str.lower() == "generator"]
    node_df = outputs_df[outputs_df["class"].str.lower() == "node"]
    line_df = outputs_df[outputs_df["class"].str.lower() == "line"]

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        generator_df.to_excel(writer, sheet_name="generacion_centrales", index=False)
        node_df.to_excel(writer, sheet_name="cmg_y_demanda_barras", index=False)
        line_df.to_excel(writer, sheet_name="flujo_lineas", index=False)
        inputs_df.to_excel(writer, sheet_name="inputs_mantenimiento_hidro", index=False)
