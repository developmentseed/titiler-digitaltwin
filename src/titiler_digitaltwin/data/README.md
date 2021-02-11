
The MGRS geojson has be created from https://github.com/klaukh/MGRS

```
$ ogr2ogr -of GeoJSON -t_srs epsg:4326 -simplify 0.0001 -select "GZD" -wrapdateline MGRS.geojson MGRS_GZD_world.shp
```

Right now we are using a static file to get the bounds of the grid (also used in the mosaic backend to find the intersecting grid).

This might be temporary and we might use a programatic way later: https://github.com/search?q=MGRS
