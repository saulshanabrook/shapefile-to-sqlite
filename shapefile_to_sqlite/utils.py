from shapely.geometry import shape, mapping
from shapely.ops import transform
import fiona
import pyproj
from pyproj import CRS
from functools import partial
import sqlite_utils
import itertools
import os

# I used this to debug a segmentation fault:
# import faulthandler
# faulthandler.enable()


SPATIALITE_PATHS = (
    "/usr/lib/x86_64-linux-gnu/mod_spatialite.so",
    "/usr/local/lib/mod_spatialite.dylib",
)
WGS_84 = CRS.from_epsg(4326)


class SpatiaLiteError(Exception):
    pass


import json


def import_features(
    db_path, table, features, shapefile_crs, target_crs=None, alter=False, spatialite=False, spatialite_mod=None,
):
    db = sqlite_utils.Database(db_path)
    target_crs = WGS_84

    # We need to convert from shapefile_crs to target_crs
    project = partial(pyproj.transform, pyproj.Proj(shapefile_crs), pyproj.Proj(target_crs))

    def yield_features():
        for feature in features:
            if isinstance(feature["id"], str) and feature["id"].isdigit():
                feature["id"] = int(feature["id"])
            feature.pop("type")
            properties = feature.pop("properties") or {}
            for key in list(properties.keys()):
                if key.lower() == "id":
                    properties["id_"] = properties.pop(key)
            feature.update(properties)
            # Transform co-ordinates:
            geometry = transform(project, shape(feature["geometry"]))
            if spatialite:
                feature["geometry"] = geometry.wkt
            else:
                feature["geometry"] = mapping(geometry)
            yield feature

    features_iter = yield_features()

    conversions = {}
    if spatialite_mod:
        spatialite = True
    if spatialite:
        lib = spatialite_mod or find_spatialite()
        if not lib:
            raise SpatiaLiteError("Could not find SpatiaLite module")
        init_spatialite(db, lib)
        if table not in db.table_names():
            # Create the table, using detected column types
            first_100 = list(itertools.islice(features_iter, 0, 100))
            features_iter = itertools.chain(first_100, features_iter)
            column_types = sqlite_utils.suggest_column_types(first_100)
            column_types.pop("geometry")
            db[table].create(column_types, pk="id")
            ensure_table_has_geometry(db, table)
        conversions = {"geometry": "GeomFromText(?, 4326)"}

    db[table].insert_all(
        features_iter, conversions=conversions, alter=alter, pk="id", replace=True
    )
    return db[table]


def find_spatialite():
    for path in SPATIALITE_PATHS:
        if os.path.exists(path):
            return path
    return None


def init_spatialite(db, lib):
    db.conn.enable_load_extension(True)
    db.conn.load_extension(lib)
    # Initialize SpatiaLite if not yet initialized
    if "spatial_ref_sys" in db.table_names():
        return
    db.conn.execute("select InitSpatialMetadata(1)")


def ensure_table_has_geometry(db, table):
    if "geometry" not in db[table].columns_dict:
        db.conn.execute(
            "SELECT AddGeometryColumn(?, 'geometry', 4326, 'GEOMETRY', 2);", [table]
        )


def has_ids(features):
    return all(f.get("id") is not None for f in features)
