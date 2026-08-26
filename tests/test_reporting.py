from nirs_report_app.analysis.features import FeatureResult
from nirs_report_app.reporting import PatientInfo, build_report
from nirs_report_app.settings import ReportSettings


def test_builds_docx_report(tmp_path) -> None:
    destination = tmp_path / "report.docx"
    result = FeatureResult(1.2, 2.3, 4.5, "missing", 45, -1)
    build_report(destination, ReportSettings(report_title="NIRS"), PatientInfo(), result)
    assert destination.exists()
    assert destination.stat().st_size > 0
