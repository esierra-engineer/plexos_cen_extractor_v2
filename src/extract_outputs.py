from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

TARGET_PROPERTIES = {"generation", "price", "flow", "demand"}
FLOAT64_BYTE_SIZE = 8


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


def _build_period_sequence(tables: dict[str, pd.DataFrame], phase_id: int, period_type_id: int) -> list[object]:
    period_df = tables.get(f"t_period_{period_type_id}", pd.DataFrame())
    if period_df.empty:
        for i in range(10):
            candidate = tables.get(f"t_period_{i}")
            if candidate is not None and not candidate.empty:
                period_df = candidate
                break

    if period_df.empty:
        return []

    period_key_col = _find_col(period_df, "interval_id", "period_id", "id")
    period_value_col = _find_col(period_df, "datetime", "start_time", "timestamp", "date", "name")
    if period_key_col is None or period_value_col is None:
        return []

    period = period_df[[period_key_col, period_value_col]].copy()
    period[period_key_col] = pd.to_numeric(period[period_key_col], errors="coerce")
    period = period.dropna(subset=[period_key_col])
    period_map = dict(zip(period[period_key_col].astype(int), period[period_value_col]))

    phase_df = tables.get(f"t_phase_{phase_id}", pd.DataFrame())
    if phase_df.empty:
        return list(period[period_value_col])

    phase_interval_col = _find_col(phase_df, "interval_id", "period_id", "id")
    phase_order_col = _find_col(phase_df, "period_id", "interval_id", "id")
    if phase_interval_col is None or phase_order_col is None:
        return list(period[period_value_col])

    phase = phase_df[[phase_interval_col, phase_order_col]].copy()
    phase[phase_interval_col] = pd.to_numeric(phase[phase_interval_col], errors="coerce")
    phase[phase_order_col] = pd.to_numeric(phase[phase_order_col], errors="coerce")
    phase = phase.dropna(subset=[phase_interval_col, phase_order_col]).sort_values(phase_order_col)

    return [period_map.get(int(interval_id), "") for interval_id in phase[phase_interval_col]]


def _expand_key_values(
    key: pd.DataFrame,
    key_index_df: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    values: np.ndarray,
    key_id_col: str,
) -> pd.DataFrame:
    idx_key_col = _find_col(key_index_df, "key_id", "id")
    idx_position_col = _find_col(key_index_df, "position")
    idx_length_col = _find_col(key_index_df, "length")
    idx_offset_col = _find_col(key_index_df, "period_offset")
    phase_id_col = _find_col(key, "phase_id")
    period_type_id_col = _find_col(key, "period_type_id")

    period_cache: dict[tuple[int, int], list[object]] = {}
    key_index_map: dict[int, tuple[int, int, int]] = {}
    if (
        idx_key_col is not None
        and idx_position_col is not None
        and idx_length_col is not None
        and not key_index_df.empty
    ):
        idx = key_index_df[[idx_key_col, idx_position_col, idx_length_col]].copy()
        if idx_offset_col is not None:
            idx[idx_offset_col] = pd.to_numeric(key_index_df[idx_offset_col], errors="coerce").fillna(0)
        else:
            idx["period_offset"] = 0
            idx_offset_col = "period_offset"
        idx[idx_key_col] = pd.to_numeric(idx[idx_key_col], errors="coerce")
        idx[idx_position_col] = pd.to_numeric(idx[idx_position_col], errors="coerce")
        idx[idx_length_col] = pd.to_numeric(idx[idx_length_col], errors="coerce")
        idx = idx.dropna(subset=[idx_key_col, idx_position_col, idx_length_col])
        idx = idx[(idx[idx_position_col] >= 0) & (idx[idx_length_col] > 0)]
        key_index_map = {
            int(row[idx_key_col]): (int(row[idx_position_col]), int(row[idx_length_col]), int(row[idx_offset_col]))
            for _, row in idx.iterrows()
        }

    rows: list[dict[str, object]] = []
    for _, row in key.iterrows():
        key_id = int(row[key_id_col])

        if key_id in key_index_map:
            position, length, period_offset = key_index_map[key_id]
            # t_key_index position is stored in bytes; float64 values use 8 bytes each.
            start_idx = position // FLOAT64_BYTE_SIZE
            end_idx = start_idx + length
            series_values = values[start_idx:end_idx]

            phase_id = int(row[phase_id_col]) if phase_id_col is not None and pd.notna(row[phase_id_col]) else 0
            period_type_id = (
                int(row[period_type_id_col])
                if period_type_id_col is not None and pd.notna(row[period_type_id_col])
                else 0
            )
            cache_key = (phase_id, period_type_id)
            if cache_key not in period_cache:
                period_cache[cache_key] = _build_period_sequence(tables, phase_id=phase_id, period_type_id=period_type_id)

            period_sequence = period_cache[cache_key]
            period_slice = period_sequence[period_offset : period_offset + len(series_values)]

            for i, value in enumerate(series_values):
                period_value = period_slice[i] if i < len(period_slice) else ""
                rows.append(
                    {
                        "key_id": key_id,
                        "period": period_value,
                        "class": row["class"],
                        "object": row["object"],
                        "property": row["property"],
                        "value": value,
                    }
                )
            continue

        if 0 < key_id <= len(values):
            rows.append(
                {
                    "key_id": key_id,
                    "period": "",
                    "class": row["class"],
                    "object": row["object"],
                    "property": row["property"],
                    "value": values[key_id - 1],
                }
            )

    return pd.DataFrame(rows, columns=["key_id", "period", "class", "object", "property", "value"])


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

    key_id_col = _find_col(key_df, "key_id", "id")
    property_id_col = _find_col(key_df, "property_id")

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
    key_index_df = tables.get("t_key_index", pd.DataFrame())

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
    key = key[key["property"].str.lower().isin(TARGET_PROPERTIES)].copy()

    if key.empty:
        return pd.DataFrame(columns=["key_id", "period", "class", "object", "property", "value"])

    result = _expand_key_values(key, key_index_df, tables, values, key_id_col)
    result["period"] = pd.to_datetime(result["period"], errors="coerce", dayfirst=True)
    return result
