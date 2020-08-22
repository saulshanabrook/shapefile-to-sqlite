from click.testing import CliRunner
from shapefile_to_sqlite import cli, utils
import pytest
from pytest import approx
import sqlite_utils
import json
import pathlib
import pytest


testdir = pathlib.Path(__file__).parent


def test_missing(tmpdir):
    db_path = str(tmpdir / "output.db")
    result = CliRunner().invoke(
        cli.cli, [db_path, str(testdir / "missing.shp")], catch_exceptions=False
    )
    assert 2 == result.exit_code
    assert "does not exist" in result.stdout.strip()


@pytest.mark.parametrize("table", [None, "customtable"])
def test_import_features(tmpdir, table):
    db_path = str(tmpdir / "output.db")
    args = [db_path, str(testdir / "features.shp")]
    expected_table = "features"
    if table:
        expected_table = table
        args.extend(("--table", table))
    result = CliRunner().invoke(cli.cli, args, catch_exceptions=False)
    assert 0 == result.exit_code, result.stdout
    db = sqlite_utils.Database(db_path)
    assert [expected_table] == db.table_names()
    rows = list(db[expected_table].rows)
    expected_rows = [
        {
            "id": 0,
            "id_": 123,
            "geometry": '{"type": "Polygon", "coordinates": [[[-8.0859375, 60.930432202923335], [1.0546875, 60.06484046010452], [4.21875, 52.26815737376817], [-5.9765625, 48.922499263758255], [-16.875, 50.28933925329178], [-8.0859375, 60.930432202923335]]]}',
            "slug": "uk",
            "about": "Rough area around the UK",
        },
        {
            "id": 1,
            "id_": 456,
            "geometry": '{"type": "Polygon", "coordinates": [[[-129.375, 47.754097979680026], [-115.31249999999999, 50.736455137010665], [-100.8984375, 50.064191736659104], [-84.375, 51.39920565355378], [-61.52343749999999, 44.33956524809713], [-77.34374999999999, 25.48295117535531], [-85.4296875, 24.206889622398023], [-96.6796875, 25.48295117535531], [-119.53125, 33.43144133557529], [-129.375, 47.754097979680026]]]}',
            "slug": "usa",
            "about": "Very rough area around the USA",
        },
    ]
    assert expected_rows == rows


@pytest.mark.skipif(not utils.find_spatialite(), reason="Could not find SpatiaLite")
def test_import_features_spatialite(tmpdir):
    db_path = str(tmpdir / "output.db")
    result = CliRunner().invoke(
        cli.cli,
        [db_path, str(testdir / "features.shp"), "--spatialite"],
        catch_exceptions=False,
    )
    assert 0 == result.exit_code, result.stdout
    db = sqlite_utils.Database(db_path)
    utils.init_spatialite(db, utils.find_spatialite())
    assert {"features", "spatial_ref_sys"}.issubset(db.table_names())
    rows = db.execute_returning_dicts(
        "select slug, AsGeoJSON(geometry) as geometry from features"
    )
    expected_rows = [
        {
            "slug": "uk",
            "geometry": '{"type":"Polygon","coordinates":[[[-8.0859375,60.93043220292332],[1.0546875,60.06484046010452],[4.21875,52.26815737376816],[-5.9765625,48.92249926375824],[-16.875,50.28933925329177],[-8.0859375,60.93043220292332]]]}',
        },
        {
            "slug": "usa",
            "geometry": '{"type":"Polygon","coordinates":[[[-129.375,47.75409797968003],[-115.3125,50.73645513701067],[-100.8984375,50.06419173665909],[-84.375,51.39920565355377],[-61.52343749999999,44.33956524809713],[-77.34374999999998,25.48295117535531],[-85.4296875,24.20688962239802],[-96.6796875,25.48295117535531],[-119.53125,33.43144133557529],[-129.375,47.75409797968003]]]}',
        },
    ]
    assert ["id"] == db["features"].pks
    assert expected_rows == rows


@pytest.mark.skipif(not utils.find_spatialite(), reason="Could not find SpatiaLite")
def test_import_features_spatialite_with_custom_crs(tmpdir):
    db_path = str(tmpdir / "output.db")
    result = CliRunner().invoke(
        cli.cli,
        [
            db_path,
            str(testdir / "features.shp"),
            "--spatialite",
            "--crs",
            "epsg:2227",
            "-v",
        ],
        catch_exceptions=False,
    )
    assert 0 == result.exit_code, result.stdout
    db = sqlite_utils.Database(db_path)
    utils.init_spatialite(db, utils.find_spatialite())
    assert {"features", "spatial_ref_sys"}.issubset(db.table_names())
    rows = db.execute_returning_dicts(
        "select slug, srid(geometry), AsGeoJSON(geometry) as geometry from features"
    )
    for row in rows:
        row["geometry"] = json.loads(row["geometry"])
    expected_rows = [
        {
            "slug": "uk",
            "srid(geometry)": 2227,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [approx(23657775.32853747), approx(22529666.28541567)],
                        [approx(24556455.05763163), approx(24135172.24177192)],
                        [approx(27652738.70766846), approx(24033449.61854204)],
                        [approx(28150883.53219706), approx(21343916.93640194)],
                        [approx(26640920.79348303), approx(19116447.67223906)],
                        [approx(23657775.32853747), approx(22529666.28541567)],
                    ]
                ],
            },
        },
        {
            "slug": "usa",
            "srid(geometry)": 2227,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [approx(4346640.819945158), approx(5865811.33053253)],
                        [approx(7796046.518982057), approx(6906735.031612804)],
                        [approx(11246615.05156807), approx(7113130.806141029)],
                        [approx(14856355.43933342), approx(8742646.756998315)],
                        [approx(21088511.50955399), approx(9236831.236157331)],
                        [approx(20601665.850453), approx(896152.8569381489)],
                        [approx(18284784.27434483), approx(-652093.4496258244)],
                        [approx(14506308.7237259), approx(-1383122.899243944)],
                        [approx(6858031.882782473), approx(523720.8423723599)],
                        [approx(4346640.819945158), approx(5865811.33053253)],
                    ]
                ],
            },
        },
    ]
    assert ["id"] == db["features"].pks
    assert expected_rows == rows


@pytest.mark.skipif(not utils.find_spatialite(), reason="Could not find SpatiaLite")
def test_import_features_spatial_index(tmpdir):
    db_path = str(tmpdir / "output.db")
    result = CliRunner().invoke(
        cli.cli,
        [db_path, str(testdir / "features.shp"), "--spatialite", "--spatial-index"],
        catch_exceptions=False,
    )
    assert 0 == result.exit_code, result.stdout
    db = sqlite_utils.Database(db_path)
    utils.init_spatialite(db, utils.find_spatialite())
    assert "idx_features_geometry" in db.table_names()
