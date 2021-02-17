"""TITILER_STACK Configs."""

from typing import Dict, List, Optional

import pydantic


class StackSettings(pydantic.BaseSettings):
    """Application settings"""

    name: str = "titiler-sentinel2-digitaltwin"
    stage: str = "production"

    owner: Optional[str]
    client: Optional[str]

    additional_env: Dict = {
        "MAX_THREADS": "1",
    }

    # add S3 bucket where TiTiler could do HEAD and GET Requests
    buckets: List = ["sentinel-s2-l2a-mosaic-120"]

    ############
    # AWS LAMBDA
    timeout: int = 10
    memory: int = 3008
    # more about lambda config: https://www.sentiatechblog.com/aws-re-invent-2020-day-3-optimizing-lambda-cost-with-multi-threading

    # The maximum of concurrent executions you want to reserve for the function.
    # Default: - No specific limit - account limit.
    max_concurrent: Optional[int]

    class Config:
        """model config"""

        env_file = ".env"
