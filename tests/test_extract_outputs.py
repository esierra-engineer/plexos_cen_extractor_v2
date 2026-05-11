import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.extract_outputs import extract_outputs


XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<MasterDataSet xmlns="http://tempuri.org/MasterDataSet.xsd">
  <t_class>
    <class_id>1</class_id>
    <name>Generator</name>
  </t_class>
  <t_object>
    <object_id>100</object_id>
    <class_id>1</class_id>
    <name>GenA</name>
  </t_object>
  <t_property>
    <property_id>2</property_id>
    <name>Generation</name>
  </t_property>
  <t_membership>
    <membership_id>200</membership_id>
    <child_object_id>100</child_object_id>
  </t_membership>
  <t_key>
    <key_id>1</key_id>
    <membership_id>200</membership_id>
    <phase_id>3</phase_id>
    <property_id>2</property_id>
    <period_type_id>0</period_type_id>
  </t_key>
  <t_key_index>
    <key_id>1</key_id>
    <period_type_id>0</period_type_id>
    <position>0</position>
    <length>2</length>
    <period_offset>0</period_offset>
  </t_key_index>
  <t_phase_3>
    <period_id>1</period_id>
    <interval_id>1</interval_id>
  </t_phase_3>
  <t_phase_3>
    <period_id>2</period_id>
    <interval_id>2</interval_id>
  </t_phase_3>
  <t_period_0>
    <interval_id>1</interval_id>
    <datetime>09/05/2026 00:00:00</datetime>
  </t_period_0>
  <t_period_0>
    <interval_id>2</interval_id>
    <datetime>09/05/2026 01:00:00</datetime>
  </t_period_0>
</MasterDataSet>
"""


class ExtractOutputsTests(unittest.TestCase):
    def test_extract_outputs_expands_key_index_and_maps_period_datetime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            solution_xml = root / "solution.xml"
            data_bin = root / "t_data_0.BIN"

            solution_xml.write_text(XML_TEMPLATE, encoding="utf-8")
            np.array([10.0, 11.0], dtype=np.float64).tofile(data_bin)

            df = extract_outputs(solution_xml=solution_xml, data_bin=data_bin)

            self.assertEqual(2, len(df))
            self.assertEqual(["Generation", "Generation"], df["property"].tolist())
            self.assertEqual(["Generator", "Generator"], df["class"].tolist())
            self.assertEqual(["GenA", "GenA"], df["object"].tolist())
            self.assertEqual([10.0, 11.0], df["value"].tolist())
            self.assertEqual(
                [pd.Timestamp("2026-05-09 00:00:00"), pd.Timestamp("2026-05-09 01:00:00")],
                df["period"].tolist(),
            )


if __name__ == "__main__":
    unittest.main()
