"""Setup titiler."""

from setuptools import find_packages, setup

inst_reqs = ["titiler==0.2.0", "mangum>=0.10"]


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
