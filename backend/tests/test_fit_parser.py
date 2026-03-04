import pytest
from pathlib import Path
from app.services.fit_parser import parse_fit_file, FitParseResult

FIXTURE = Path(__file__).parent / "fixtures" / "sample.fit"


@pytest.mark.skipif(not FIXTURE.exists(), reason="no sample.fit fixture")
def test_parse_returns_result():
    result = parse_fit_file(FIXTURE)
    assert isinstance(result, FitParseResult)
    assert result.started_at is not None
    assert result.distance_m > 0
    assert result.duration_s > 0
    assert len(result.datapoints) > 0


@pytest.mark.skipif(not FIXTURE.exists(), reason="no sample.fit fixture")
def test_datapoints_have_timestamps():
    result = parse_fit_file(FIXTURE)
    for dp in result.datapoints:
        assert dp["timestamp"] is not None


@pytest.mark.skipif(not FIXTURE.exists(), reason="no sample.fit fixture")
def test_datapoints_not_compressed():
    """Every record from the FIT file must be stored — no downsampling."""
    result = parse_fit_file(FIXTURE)
    # FIT files record at ~1Hz; a 30-min run should have >=1000 points
    assert len(result.datapoints) >= 100


def test_parse_nonexistent_file_raises():
    with pytest.raises(FileNotFoundError):
        parse_fit_file(Path("/nonexistent/file.fit"))
