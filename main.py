from pathlib import Path

from src.config import Paths
from src.excel_writer import export_report
from src.extract_inputs import extract_inputs
from src.extract_outputs import extract_outputs


def main() -> None:
    paths = Paths.from_repo_root(Path(__file__).resolve().parent)

    inputs_df = extract_inputs(
        gen_units_out_csv=paths.gen_units_out_csv,
        hydro_waterflows_csv=paths.hydro_waterflows_csv,
        dbsen_xml=paths.dbsen_xml,
    )

    outputs_df = extract_outputs(
        solution_xml=paths.solution_xml,
        data_bin=paths.data_bin,
    )

    export_report(
        outputs_df=outputs_df,
        inputs_df=inputs_df,
        report_path=paths.report_path,
    )


if __name__ == "__main__":
    main()
