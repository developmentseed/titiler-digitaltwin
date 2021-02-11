"""titiler-digitaltwin custom mosaic endpoint factory."""

import os
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Type
from urllib.parse import urlencode

import rasterio
from cogeo_mosaic.backends import BaseBackend
from morecantile import TileMatrixSet
from rio_tiler.constants import MAX_THREADS
from rio_tiler.io import BaseReader
from titiler import utils
from titiler.dependencies import DefaultDependency, TMSParams
from titiler.endpoints.factory import (
    BaseTilerFactory,
    default_deps_type,
    img_endpoint_params,
)
from titiler.errors import RasterioIOError, TileOutsideBounds
from titiler.models.mapbox import TileJSON
from titiler.resources.enums import ImageType, PixelSelectionMethod

from titiler_digitaltwin.reader import DynamicDigitalTwinBackend, S2DigitalTwinReader

from fastapi import Depends, Path, Query

from starlette.requests import Request
from starlette.responses import Response


@dataclass
class BandsExprParams(DefaultDependency):
    """Band names and Expression parameters."""

    bands: Optional[str] = Query(
        None, title="bands names", description="comma (',') delimited bands names.",
    )
    expression: Optional[str] = Query(
        None,
        title="Band Math expression",
        description="rio-tiler's band math expression.",
    )

    def __post_init__(self):
        """Post Init."""
        if self.bands is not None:
            self.kwargs["bands"] = self.bands.split(",")
        if self.expression is not None:
            self.kwargs["expression"] = self.expression


@dataclass
class PathParams:
    """Create dataset path from args"""

    year: int = Query(..., description="year")
    month: int = Query(..., description="month")
    day: int = Query(..., description="day")


@dataclass
class MosaicTilerFactory(BaseTilerFactory):
    """
    MosaicTiler Factory.

    The main difference with titiler.endpoint.factory.TilerFactory is that this factory
    needs a reader (MosaicBackend) and a dataset_reader (BaseReader).
    """

    reader: BaseBackend = field(default=DynamicDigitalTwinBackend)
    dataset_reader: Type[BaseReader] = field(default=S2DigitalTwinReader)

    path_dependency: Type[PathParams] = field(default=PathParams)
    layer_dependency: default_deps_type = field(default=BandsExprParams)

    # BaseBackend does not support other TMS than WebMercator
    tms_dependency: Callable[..., TileMatrixSet] = TMSParams

    def register_routes(self):
        """This Method register routes to the router."""
        self.tile()
        self.tilejson()

    ############################################################################
    # /tiles
    ############################################################################
    def tile(self):  # noqa: C901
        """Register /tiles endpoints."""

        @self.router.get(r"/tiles/{z}/{x}/{y}", **img_endpoint_params)
        @self.router.get(r"/tiles/{z}/{x}/{y}.{format}", **img_endpoint_params)
        @self.router.get(r"/tiles/{z}/{x}/{y}@{scale}x", **img_endpoint_params)
        @self.router.get(r"/tiles/{z}/{x}/{y}@{scale}x.{format}", **img_endpoint_params)
        @self.router.get(r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}", **img_endpoint_params)
        @self.router.get(
            r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}.{format}", **img_endpoint_params
        )
        @self.router.get(
            r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}@{scale}x", **img_endpoint_params
        )
        @self.router.get(
            r"/tiles/{TileMatrixSetId}/{z}/{x}/{y}@{scale}x.{format}",
            **img_endpoint_params,
        )
        def tile(
            z: int = Path(..., ge=0, le=30, description="Mercator tiles's zoom level"),
            x: int = Path(..., description="Mercator tiles's column"),
            y: int = Path(..., description="Mercator tiles's row"),
            tms: TileMatrixSet = Depends(self.tms_dependency),
            scale: int = Query(
                1, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
            ),
            format: ImageType = Query(
                None, description="Output image type. Default is auto."
            ),
            src_path=Depends(self.path_dependency),
            layer_params=Depends(self.layer_dependency),
            dataset_params=Depends(self.dataset_dependency),
            render_params=Depends(self.render_dependency),
            pixel_selection: PixelSelectionMethod = Query(
                PixelSelectionMethod.first, description="Pixel selection method."
            ),
            kwargs: Dict = Depends(self.additional_dependency),
        ):
            """Create map tile from a COG."""
            timings = []
            headers: Dict[str, str] = {}

            tilesize = scale * 256

            threads = int(os.getenv("MOSAIC_CONCURRENCY", MAX_THREADS))
            with utils.Timer() as t:
                with rasterio.Env(**self.gdal_config):
                    with self.reader(
                        reader=self.dataset_reader,
                        reader_options={
                            "year": src_path.year,
                            "month": src_path.month,
                            "day": src_path.day,
                        },
                    ) as src_dst:
                        mosaic_read = t.from_start
                        timings.append(("mosaicread", round(mosaic_read * 1000, 2)))

                        data, _ = src_dst.tile(
                            x,
                            y,
                            z,
                            pixel_selection=pixel_selection.method(),
                            threads=threads,
                            tilesize=tilesize,
                            # because the mosaic is dynamic, there migth be some time where the file just doesn't exist
                            allowed_exceptions=(RasterioIOError, TileOutsideBounds,),
                            **layer_params.kwargs,
                            **dataset_params.kwargs,
                            **kwargs,
                        )
            timings.append(("dataread", round((t.elapsed - mosaic_read) * 1000, 2)))

            if not format:
                format = ImageType.jpeg if data.mask.all() else ImageType.png

            with utils.Timer() as t:
                image = data.post_process(
                    in_range=render_params.rescale_range,
                    color_formula=render_params.color_formula,
                )
            timings.append(("postprocess", round(t.elapsed * 1000, 2)))

            with utils.Timer() as t:
                content = image.render(
                    add_mask=render_params.return_mask,
                    img_format=format.driver,
                    colormap=render_params.colormap,
                    **format.profile,
                )
            timings.append(("format", round(t.elapsed * 1000, 2)))

            headers["Server-Timing"] = ", ".join(
                [f"{name};dur={time}" for (name, time) in timings]
            )

            headers["X-Assets"] = ",".join(data.assets)

            return Response(content, media_type=format.mimetype, headers=headers)

    def tilejson(self):  # noqa: C901
        """Add tilejson endpoint."""

        @self.router.get(
            "/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        @self.router.get(
            "/{TileMatrixSetId}/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        def tilejson(
            request: Request,
            tms: TileMatrixSet = Depends(self.tms_dependency),
            src_path=Depends(self.path_dependency),
            tile_format: Optional[ImageType] = Query(
                None, description="Output image type. Default is auto."
            ),
            tile_scale: int = Query(
                1, gt=0, lt=4, description="Tile size scale. 1=256x256, 2=512x512..."
            ),
            minzoom: Optional[int] = Query(
                None, description="Overwrite default minzoom."
            ),
            maxzoom: Optional[int] = Query(
                None, description="Overwrite default maxzoom."
            ),
            layer_params=Depends(self.layer_dependency),  # noqa
            dataset_params=Depends(self.dataset_dependency),  # noqa
            render_params=Depends(self.render_dependency),  # noqa
            pixel_selection: PixelSelectionMethod = Query(
                PixelSelectionMethod.first, description="Pixel selection method."
            ),  # noqa
            kwargs: Dict = Depends(self.additional_dependency),  # noqa
        ):
            """Return TileJSON document for a COG."""
            route_params = {
                "z": "{z}",
                "x": "{x}",
                "y": "{y}",
                "scale": tile_scale,
                "TileMatrixSetId": tms.identifier,
            }
            if tile_format:
                route_params["format"] = tile_format.value
            tiles_url = self.url_for(request, "tile", **route_params)

            q = dict(request.query_params)
            q.pop("TileMatrixSetId", None)
            q.pop("tile_format", None)
            q.pop("tile_scale", None)
            q.pop("minzoom", None)
            q.pop("maxzoom", None)
            qs = urlencode(list(q.items()))
            tiles_url += f"?{qs}"

            with self.reader(
                reader=self.dataset_reader,
                reader_options={
                    "year": src_path.year,
                    "month": src_path.month,
                    "day": src_path.day,
                },
            ) as src_dst:
                center = list(src_dst.center)
                if minzoom:
                    center[-1] = minzoom
                tjson = {
                    "bounds": src_dst.bounds,
                    "center": tuple(center),
                    "minzoom": minzoom if minzoom is not None else src_dst.minzoom,
                    "maxzoom": maxzoom if maxzoom is not None else src_dst.maxzoom,
                    "name": "Sentinel 2 Digital Twin",
                    "tiles": [tiles_url],
                }

            return tjson
