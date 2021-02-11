"""titiler-digitaltwin custom readers."""

import json
import pathlib
from typing import Any, Dict, List, Tuple, Type

import attr
from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.mosaic import MosaicJSON
from morecantile import TileMatrixSet
from pygeos import Geometry, STRtree, points, polygons
from rasterio.features import bounds as featureBounds
from rio_tiler import constants
from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.errors import InvalidBandName
from rio_tiler.io import BaseReader, COGReader, MultiBandReader
from rio_tiler.models import ImageData
from rio_tiler.mosaic import mosaic_reader
from rio_tiler.tasks import multi_values

# Load the grid from local geojson
with open(f"{str(pathlib.Path(__file__).parent)}/data/MGRS.geojson") as f:
    mgrs_grid = json.load(f)

# Create List of grid names and STRtree
grid_names = [feat["properties"]["GZD"] for feat in mgrs_grid["features"]]
tree = STRtree(
    [polygons(feat["geometry"]["coordinates"][0]) for feat in mgrs_grid["features"]]
)

default_bands = (
    "B02",
    "B03",
    "B04",
    "B08",
    "B11",
    "B12",
)


def get_grid_bbox(name: str) -> Tuple[float, float, float, float]:
    """Get grid bbox."""
    feat = list(
        filter(lambda x: x["properties"]["GZD"] == name, mgrs_grid["features"])
    )[0]
    return featureBounds(feat["geometry"])


@attr.s
class S2DigitalTwinReader(MultiBandReader):
    """Sentinel DigitalTwin Reader

    Note: this should be added to rio-tiler-pds
    """

    grid: str = attr.ib()
    year: int = attr.ib()
    month: int = attr.ib()
    day: int = attr.ib()
    reader: Type[COGReader] = attr.ib(default=COGReader)

    # Nodata seems to be missing (might be added in the second iteration)
    reader_options: Dict = attr.ib({"nodata": 0})

    tms: TileMatrixSet = attr.ib(default=constants.WEB_MERCATOR_TMS)
    minzoom: int = attr.ib(default=6)
    maxzoom: int = attr.ib(default=10)

    bands: tuple = attr.ib(init=False, default=default_bands)

    _scheme: str = "s3"
    _hostname: str = "sentinel-s2-l2a-mosaic-120"
    _prefix: str = "{year}/{month}/{day}/{grid}"

    def __attrs_post_init__(self):
        """Fetch item.json and get bounds and bands."""
        self.bounds = get_grid_bbox(self.grid)

    def _get_band_url(self, band: str) -> str:
        """Validate band name and return band's url."""
        band = band if len(band) == 3 else f"B0{band[-1]}"

        if band not in self.bands:
            raise InvalidBandName(f"{band} is not valid.\nValid bands: {self.bands}")

        prefix = self._prefix.format(
            year=self.year, month=self.month, day=self.day, grid=self.grid
        )
        return f"{self._scheme}://{self._hostname}/{prefix}/{band}.tif"


@attr.s
class DynamicDigitalTwinBackend(BaseBackend):
    """Dynamic Mosaic Backend for S2DigitalTwinReader.

    Note: Because the data is aligned to a regular grid (MGRS) and has set a fixed date
        we can create a Dynamic Mosaic Backend which will fetch the intersecting data (point/bbox)
        for a specifc set of year-month-day

    Examples:
        >>> with DynamicDigitalTwinBackend(reader_options={"year": 2019, "month": 1, "day": 1}) as mosaic:
            img = mosaic.tile(482, 164, 9, bands="B02")

    """

    reader: Type[BaseReader] = attr.ib(default=S2DigitalTwinReader)
    reader_options: Dict = attr.ib(factory=dict)
    backend_options: Dict = attr.ib(factory=dict)

    query: Dict = attr.ib(factory=dict)

    # default values for bounds and zoom
    bounds: Tuple[float, float, float, float] = attr.ib(
        init=False, default=(-180, -90, 180, 90)
    )

    minzoom: int = attr.ib(default=5)
    maxzoom: int = attr.ib(default=10)

    # Because we are not using mosaicjson we are not limited to the WebMercator TMS
    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    path: str = attr.ib(init=False, default="digital_twin_sentinel2")

    # The reader is read-only, we can't pass mosaic_def to the init method
    mosaic_def: MosaicJSON = attr.ib(init=False)

    _backend_name = "DynamicDigitalTwin"

    def __attrs_post_init__(self):
        """Post Init."""
        # Construct a FAKE mosaicJSON
        # mosaic_def has to be defined. As we do for the DynamoDB and SQLite backend
        # we set `tiles` to an empty list.
        self.mosaic_def = MosaicJSON(
            mosaicjson="0.0.2",
            name="it's fake but it's ok",
            minzoom=self.minzoom,
            maxzoom=self.maxzoom,
            tiles=[],
        )

    def write(self, overwrite: bool = True):
        """This method is not used but is required by the abstract class."""
        pass

    def update(self):
        """We overwrite the default method."""
        pass

    def _read(self) -> MosaicJSON:
        """This method is not used but is required by the abstract class."""
        pass

    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        bbox = self.tms.bounds(x, y, z)
        geom = polygons(
            [
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
            ]
        )
        return self.get_assets(geom)

    def assets_for_point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        return self.get_assets(points([lng, lat]))

    def get_assets(self, geom: Geometry) -> List[str]:
        """Find assets."""
        idx = tree.query(geom, predicate="intersects").tolist()
        return [grid_names[n] for n in idx]

    def tile(  # type: ignore
        self, x: int, y: int, z: int, reverse: bool = False, **kwargs: Any,
    ) -> Tuple[ImageData, List[str]]:
        """Get Tile from multiple observation."""
        mosaic_assets = self.assets_for_tile(x, y, z)
        if not mosaic_assets:
            raise NoAssetFoundError(f"No assets found for tile {z}-{x}-{y}")

        if reverse:
            mosaic_assets = list(reversed(mosaic_assets))

        def _reader(asset: str, x: int, y: int, z: int, **kwargs: Any) -> ImageData:
            with self.reader(asset, **self.reader_options) as src_dst:
                return src_dst.tile(x, y, z, **kwargs)

        return mosaic_reader(mosaic_assets, _reader, x, y, z, **kwargs)

    def point(
        self, lon: float, lat: float, reverse: bool = False, **kwargs: Any,
    ) -> Dict:
        """Get Point value from multiple observation."""
        mosaic_assets = self.assets_for_point(lon, lat)
        if not mosaic_assets:
            raise NoAssetFoundError(f"No assets found for point ({lon},{lat})")

        if reverse:
            mosaic_assets = list(reversed(mosaic_assets))

        def _reader(asset: str, lon: float, lat: float, **kwargs) -> Dict:
            with self.reader(asset, **self.reader_options) as src_dst:
                return src_dst.point(lon, lat, **kwargs)

        return multi_values(mosaic_assets, _reader, lon, lat, **kwargs)

    @property
    def _quadkeys(self) -> List[str]:
        return []
