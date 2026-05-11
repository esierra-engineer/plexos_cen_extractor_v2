from dataclasses import dataclass
from pathlib import Path


def _resolve_file(root: Path, file_name: str) -> Path:
    direct_path = root / file_name
    if direct_path.exists():
        return direct_path

    for candidate in root.rglob(file_name):
        if candidate.is_file():
            return candidate

    return direct_path


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
        solution_xml = _resolve_file(outputs_root, "Model PRGdia_Full_Definitivo Solution.xml")
        data_bin = _resolve_file(outputs_root, "t_data_0.BIN")

        return cls(
            data_root=data_root,
            inputs_root=inputs_root,
            outputs_root=outputs_root,
            gen_units_out_csv=inputs_root / "Gen_UnitsOut.csv",
            hydro_waterflows_csv=inputs_root / "Hydro_WaterFlows.csv",
            dbsen_xml=inputs_root / "DBSEN_PRGDIARIO.xml",
            solution_xml=solution_xml,
            data_bin=data_bin,
            report_path=report_path,
        )
