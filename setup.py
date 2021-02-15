"""Setup titiler."""

from setuptools import find_packages, setup

inst_reqs = [
    # rasterio 1.2.0 wheels are built using GDAL 3.2 and PROJ 7 which we found having a
    # performance downgrade: https://github.com/developmentseed/titiler/discussions/216
    "rasterio==1.1.8",
    # Here we use the master branch of TiTiler which has some improvement yet to be published.
    "titiler @ git+https://github.com/developmentseed/titiler.git",
    "mangum>=0.10",
]


setup(
    name="titiler_digitaltwin",
    version="0.1.0",
    description=u"",
    python_requires=">=3",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    author=u"Vincent Sarago",
    author_email="vincent@developmentseed.org",
    url="https://github.com/developmentseed/titiler-digitaltwin",
    license="MIT",
    packages=find_packages(exclude=["tests*", "stack*"]),
    package_data={"titiler_digitaltwin": ["templates/*.html", "data/*.geojson"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
)
