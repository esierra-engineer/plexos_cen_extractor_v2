from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    data_root: Path
    inputs_root: Path
    outputs_root: Path
    gen_units_out_csv: Path
    hydro_waterflows_csv: Path
    dbsen_xml: Path
    solution_xml: Path
    data_bin: Path
    report_path: Path

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "Paths":
        data_root = repo_root / "data"
        inputs_root = data_root / "DATOS20260509"
        outputs_root = data_root / "Model PRGdia_Full_Definitivo Solution"
        report_path = repo_root / "reports" / "cen_revision_diaria.xlsx"

        return cls(
            data_root=data_root,
            inputs_root=inputs_root,
            outputs_root=outputs_root,
            gen_units_out_csv=inputs_root / "Gen_UnitsOut.csv",
            hydro_waterflows_csv=inputs_root / "Hydro_WaterFlows.csv",
            dbsen_xml=inputs_root / "DBSEN_PRGDIARIO.xml",
            solution_xml=outputs_root / "Model PRGdia_Full_Definitivo Solution.xml",
            data_bin=outputs_root / "t_data_0.BIN",
            report_path=report_path,
        )
