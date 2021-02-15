
Grid of Sentinel 2 Digital Twin tiles

1. Download grid geojsons from Sinergise

https://cloud.sinergise.com/s/JCxryPJfqrNGaw5

2. Reproject geojson to epsg:4326
```
$ ls -1| while read line; do bname=$(echo $line | sed 's/\.GeoJSON//g'); ogr2ogr -of GeoJSON -t_srs epsg:4326 -wrapdateline "$bname"_epsg4326.geojson $line; done
```

3. Merge the geojson

```
$ ls -1 *_epsg4326.geojson | while read line; do grid=$(echo $line | sed 's/_epsg4326.geojson//g'); cat $line | jq -c --arg grid "$grid" '.features[0] | .properties.name = $grid'; done | fio collect > grid.geojson
```
