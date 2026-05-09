from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

TARGET_PROPERTIES = {"generation", "price", "flow", "demand"}


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_solution_tables(solution_xml: Path) -> dict[str, pd.DataFrame]:
    tree = ET.parse(solution_xml)
    root = tree.getroot()

    tables: dict[str, list[dict[str, str]]] = {}
    for row in root:
        table_name = _strip_namespace(row.tag).lower()
        row_data = {
            _strip_namespace(col.tag).lower(): (col.text or "").strip()
            for col in row
        }
        tables.setdefault(table_name, []).append(row_data)

    return {name: pd.DataFrame(rows) for name, rows in tables.items()}


def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    cols = set(df.columns)
    for candidate in candidates:
        if candidate in cols:
            return candidate
    return None


def _id_to_name(df: pd.DataFrame, id_candidates: tuple[str, ...], name_candidates: tuple[str, ...]) -> dict[int, str]:
    id_col = _find_col(df, *id_candidates)
    name_col = _find_col(df, *name_candidates)
    if id_col is None or name_col is None:
        return {}

    clean = df[[id_col, name_col]].copy()
    clean[id_col] = pd.to_numeric(clean[id_col], errors="coerce")
    clean = clean.dropna(subset=[id_col])
    clean[id_col] = clean[id_col].astype(int)
    return dict(zip(clean[id_col], clean[name_col]))


def _resolve_object_id(key_df: pd.DataFrame, membership_df: pd.DataFrame) -> pd.Series:
    direct_object_col = _find_col(key_df, "object_id", "child_object_id")
    if direct_object_col is not None:
        return pd.to_numeric(key_df[direct_object_col], errors="coerce")

    membership_id_col = _find_col(key_df, "membership_id")
    membership_key_col = _find_col(membership_df, "membership_id", "id")
    membership_object_col = _find_col(membership_df, "child_object_id", "object_id", "member_object_id")

    if membership_id_col is None or membership_key_col is None or membership_object_col is None:
        return pd.Series(index=key_df.index, dtype=float)

    tmp = membership_df[[membership_key_col, membership_object_col]].copy()
    tmp[membership_key_col] = pd.to_numeric(tmp[membership_key_col], errors="coerce")
    tmp[membership_object_col] = pd.to_numeric(tmp[membership_object_col], errors="coerce")
    tmp = tmp.dropna()
    mapping = dict(zip(tmp[membership_key_col].astype(int), tmp[membership_object_col].astype(int)))

    membership_ids = pd.to_numeric(key_df[membership_id_col], errors="coerce")
    return membership_ids.map(mapping)


def extract_outputs(solution_xml: Path, data_bin: Path) -> pd.DataFrame:
    if not solution_xml.exists() or not data_bin.exists():
        return pd.DataFrame(columns=["key_id", "period", "class", "object", "property", "value"])

    tables = _parse_solution_tables(solution_xml)

    class_df = tables.get("t_class", pd.DataFrame())
    object_df = tables.get("t_object", pd.DataFrame())
    property_df = tables.get("t_property", pd.DataFrame())
    membership_df = tables.get("t_membership", pd.DataFrame())
    key_df = tables.get("t_key", pd.DataFrame())

    if key_df.empty:
        return pd.DataFrame(columns=["key_id", "period", "class", "object", "property", "value"])

    period_df = pd.DataFrame()
    for i in range(10):
        candidate = tables.get(f"t_period_{i}")
        if candidate is not None and not candidate.empty:
            period_df = candidate
            break

    key_id_col = _find_col(key_df, "key_id", "id")
    property_id_col = _find_col(key_df, "property_id")
    period_id_col = _find_col(key_df, "period_id", "interval_id")

    if key_id_col is None or property_id_col is None:
        return pd.DataFrame(columns=["key_id", "period", "class", "object", "property", "value"])

    key = key_df.copy()
    key[key_id_col] = pd.to_numeric(key[key_id_col], errors="coerce")
    key[property_id_col] = pd.to_numeric(key[property_id_col], errors="coerce")
    key = key.dropna(subset=[key_id_col, property_id_col])
    key[key_id_col] = key[key_id_col].astype(int)
    key[property_id_col] = key[property_id_col].astype(int)

    object_ids = _resolve_object_id(key, membership_df)
    key["_object_id"] = pd.to_numeric(object_ids, errors="coerce")

    values = np.fromfile(data_bin, dtype=np.float64)
    key["value"] = np.nan
    valid_mask = (key[key_id_col] > 0) & (key[key_id_col] <= len(values))
    key.loc[valid_mask, "value"] = values[key.loc[valid_mask, key_id_col].to_numpy() - 1]

    property_map = _id_to_name(property_df, ("property_id", "id"), ("name", "property_name"))
    object_name_map = _id_to_name(object_df, ("object_id", "id"), ("name", "object_name"))

    object_class_id_col = _find_col(object_df, "class_id")
    object_id_col = _find_col(object_df, "object_id", "id")
    class_map: dict[int, str] = {}
    if object_class_id_col is not None and object_id_col is not None:
        class_id_map = _id_to_name(class_df, ("class_id", "id"), ("name", "class_name"))
        obj = object_df[[object_id_col, object_class_id_col]].copy()
        obj[object_id_col] = pd.to_numeric(obj[object_id_col], errors="coerce")
        obj[object_class_id_col] = pd.to_numeric(obj[object_class_id_col], errors="coerce")
        obj = obj.dropna()
        class_map = {
            int(object_id): class_id_map.get(int(class_id), "")
            for object_id, class_id in zip(obj[object_id_col], obj[object_class_id_col])
        }

    key["property"] = key[property_id_col].map(property_map).fillna("")
    key["object"] = key["_object_id"].map(object_name_map).fillna("")
    key["class"] = key["_object_id"].map(class_map).fillna("")

    if period_id_col is not None and not period_df.empty:
        period_key_col = _find_col(period_df, "period_id", "interval_id", "id")
        period_value_col = _find_col(period_df, "datetime", "start_time", "timestamp", "date", "name")
        if period_key_col is not None and period_value_col is not None:
            period = period_df[[period_key_col, period_value_col]].copy()
            period[period_key_col] = pd.to_numeric(period[period_key_col], errors="coerce")
            period = period.dropna(subset=[period_key_col])
            period_map = dict(zip(period[period_key_col].astype(int), period[period_value_col]))
            key[period_id_col] = pd.to_numeric(key[period_id_col], errors="coerce")
            key["period"] = key[period_id_col].map(period_map)
        else:
            key["period"] = ""
    else:
        key["period"] = ""

    key = key[key["property"].str.lower().isin(TARGET_PROPERTIES)]
    return key[[key_id_col, "period", "class", "object", "property", "value"]].rename(columns={key_id_col: "key_id"})
