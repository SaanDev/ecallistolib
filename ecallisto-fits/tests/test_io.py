from ecallisto_fits.io import parse_callisto_filename

def test_parse_callisto_filename_basic():
    p = parse_callisto_filename("ALASKA-COHOE_20240101_123000_01.fit.gz")
    assert p.station == "ALASKA-COHOE"
    assert p.date_yyyymmdd == "20240101"
    assert p.time_hhmmss == "123000"
    assert p.focus == "01"
