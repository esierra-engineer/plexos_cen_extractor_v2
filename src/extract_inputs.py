from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd


def _read_csv_chunked(path: Path, input_type: str, chunksize: int = 100_000) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["input_type"])

    chunks = []
    for chunk in pd.read_csv(path, chunksize=chunksize):
        chunk = chunk.copy()
        chunk["input_type"] = input_type
        chunks.append(chunk)

    if not chunks:
        return pd.DataFrame(columns=["input_type"])

    return pd.concat(chunks, ignore_index=True)


def _extract_operational_restrictions(xml_path: Path) -> pd.DataFrame:
    if not xml_path.exists():
        return pd.DataFrame(columns=["object", "property", "value", "input_type"])

    tree = ET.parse(xml_path)
    root = tree.getroot()

    rows: list[dict[str, str]] = []
    for object_node in root.iter():
        if object_node.tag.split("}", 1)[-1].lower() != "object":
            continue
        object_name = object_node.attrib.get("Name") or object_node.attrib.get("name") or ""
        for property_node in object_node:
            if property_node.tag.split("}", 1)[-1].lower() != "property":
                continue
            property_name = (
                property_node.attrib.get("Name")
                or property_node.attrib.get("name")
                or property_node.attrib.get("Property")
                or ""
            )
            value = (property_node.text or "").strip()
            rows.append(
                {
                    "object": object_name,
                    "property": property_name,
                    "value": value,
                    "input_type": "restricción_operativa",
                }
            )

    return pd.DataFrame(rows)


def extract_inputs(gen_units_out_csv: Path, hydro_waterflows_csv: Path, dbsen_xml: Path) -> pd.DataFrame:
    gen_df = _read_csv_chunked(gen_units_out_csv, "mantenimiento_fallas")
    hydro_df = _read_csv_chunked(hydro_waterflows_csv, "hidrologia")
    restrictions_df = _extract_operational_restrictions(dbsen_xml)

    return pd.concat([gen_df, hydro_df, restrictions_df], ignore_index=True, sort=False)
