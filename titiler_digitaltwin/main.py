"""titiler digitaltwin FastAPI app."""

import logging

from brotli_asgi import BrotliMiddleware
from titiler.endpoints.factory import TMSFactory
from titiler.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.middleware import (
    CacheControlMiddleware,
    LoggerMiddleware,
    TotalTimeMiddleware,
)

from titiler_digitaltwin.mosaic import MosaicTilerFactory
from titiler_digitaltwin.settings import ApiSettings
from titiler_digitaltwin.templates import templates

from fastapi import FastAPI

from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse

logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)

api_settings = ApiSettings()


app = FastAPI(title="Sentinel 2 Digital Twin")
add_exception_handlers(app, DEFAULT_STATUS_CODES)

if api_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

app.add_middleware(BrotliMiddleware, minimum_size=0, gzip_fallback=True)
app.add_middleware(CacheControlMiddleware, cachecontrol=api_settings.cachecontrol)
if api_settings.debug:
    app.add_middleware(LoggerMiddleware, headers=True, querystrings=True)
    app.add_middleware(TotalTimeMiddleware)

tms = TMSFactory()
app.include_router(tms.router, tags=["TileMatrixSets"])

mosaic = MosaicTilerFactory()
app.include_router(mosaic.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing(request: Request):
    """TiTiler Landing page"""
    return templates.TemplateResponse(
        name="index.html",
        context={"request": request, "endpoint": request.url_for("landing")},
        media_type="text/html",
    )
