
The MGRS geojson has be created from https://github.com/klaukh/MGRS


### Simplify and reproject the grid
```
$ ogr2ogr -of GeoJSON -t_srs epsg:4326 -simplify 0.0001 -select "GZD" -wrapdateline MGRS.geojson MGRS_GZD_world.shp
```

#### Remove empty grid

```bash
$ aws s3 ls sentinel-s2-l2a-mosaic-120/2019/1/1/ | awk '{print $2}' | sed 's/\///' > list_available.txt
```

```python
import json
with open("list_available.txt", "r") as f:
    available_grids = f.read().splitlines()

with open("MGRS.geojson", "r") as f:
    grid = json.load(f)

grid["features"] = [
    f for f in grid["features"] if f["properties"]["GZD"] in available_grids
]

with open("MGRS_filtered.geojson", "w") as f:
    f.write(json.dumps(grid))
```

Right now we are using a static file to get the bounds of the grid (also used in the mosaic backend to find the intersecting grid).

This might be temporary and we might use a programatic way later: https://github.com/search?q=MGRS
