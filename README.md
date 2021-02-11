## titiler-digitaltwin

![](https://user-images.githubusercontent.com/10407788/107635468-3438b780-6c39-11eb-8ef6-63914e2c43a3.jpg)

This is a DEMO custom api built on top of TiTiler to create Web Map Tiles from the Digital Twin Sentinel-2 COG created by Sinergise.
For more information about the dataset please checkout: https://medium.com/sentinel-hub/digital-twin-sandbox-sentinel-2-collection-available-to-everyone-20f3b5de846e

## Data

see: https://registry.opendata.aws/sentinel-s2-l2a-mosaic-120/

## Deploy

To make the deployement fast and easy we are using a custom lambda layer: `arn:aws:lambda:us-east-1:552819999234:layer:titiler_test:1`

```bash
# Install AWS CDK requirements
$ pip install -r stack/requirements.txt
$ npm install cdk==1.76.0

$ npm run cdk bootstrap aws://${AWS_ACCOUNT_ID}/eu-central-1

# Create AWS env
$ AWS_DEFAULT_REGION=eu-central-1 AWS_REGION=eu-central-1 cdk bootstrap

# Deploy app
$ AWS_DEFAULT_REGION=eu-central-1 AWS_REGION=eu-central-1 cdk deploy
```

## Debug

```bash
$ git clone https://github.com/developmentseed/titiler-digitaltwin
$ pip install -r requirements.txt
$ cd src && uvicorn titiler_digitaltwin.main:app --reload
```
