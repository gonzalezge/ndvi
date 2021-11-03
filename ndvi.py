######------------ Germán González CSIRO Application: Wed 3 Nov  -------- ######
#### ------- Objetive: Create a NDVI using Google Earth Engine ------- #####
# For install all libraries please use: pip install -r requirements.txt
import ee
import geetools
import ee
import folium
from folium import plugins
from io import StringIO
#### ----- Shapely and geopandas --- ####
import pandas as pd
import geopandas as gpd
## ---- Dates --- ### 
import datetime
from dateutil.relativedelta import relativedelta, MO
import json
import geojson
from scipy import interpolate
import plotly.express as px
import pickle

#### ------ Load credentials by key------ #####
Credentials = ee.ServiceAccountCredentials('ge.gonzalez100@gmail.com','data/key.json')
ee.Initialize(Credentials)
inBands = ee.List(['QA60','B2','B3','B4','B5','B6','B7','B8','B8A','B9','B10','B11','B12']);
outBands = ee.List(['QA60','blue','green','red','re1','re2','re3','nir','re4','waterVapor','cirrus','swir1','swir2']);

##### ----- Get data: Sentinel 2 ------ ####
def CreateData(studyArea,startDate,endDate):
    CloudCoverMax = 20
    # Get Sentinel-2 
    
    s2s =(ee.ImageCollection('COPERNICUS/S2')
          .filterDate(startDate,endDate)
          .filterBounds(studyArea)
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',CloudCoverMax))
          .filter(ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT',CloudCoverMax)))

    
    def scaleBands(img):
        prop = img.toDictionary()
        t = img.select(['QA60','B2','B3','B4','B5','B6','B7','B8','B8A','B9','B10','B11','B12']).divide(10000)
        t = t.addBands(img.select(['QA60'])).set(prop).copyProperties(img,['system:time_start','system:footprint'])
        return ee.Image(t)
    
    
    s2s = s2s.map(scaleBands)
    s2s = s2s.select(inBands,outBands)
   
    return s2s


#### ----- Calculate NDVI ------ ###
def CalculateNDVI(image):
    
    # Normalized difference vegetation index (NDVI)
    ndvi = image.normalizedDifference(['nir','red']).rename("ndvi")
    image = image.addBands(ndvi)
  
    return(image)


##### ----- Function to aggregate Ndvi by area ---- ###
def CalculateMeanNdvi(image,studyArea):
    ### ----- Reduce to mean ----- #####
    meanDictionary = image.reduceRegion(
      reducer=ee.Reducer.mean(),
      geometry=studyArea.geometry(),
      scale=30,
    )

    #### ----- Get Ndvi mean ------ ###
    value_mean = meanDictionary.get('ndvi').getInfo()

    return(value_mean)


##### ----- Calculate de Ndvi by area (time) ---- ###
def CalculateNdvi(startyear,endyear,geojson):
    DateStart = ee.Date.fromYMD(startyear.year,startyear.month,startyear.day)
    DateEnd = ee.Date.fromYMD(endyear.year,endyear.month,endyear.day)
    studyArea = ee.FeatureCollection(geojson)
    ### ------ Get Images ----- ###
    s2 = CreateData(studyArea,DateStart,DateEnd)
    s2 = s2.median().clip(studyArea)
    ### ----- Calculate NDVI ----- ###
    s2 = CalculateNDVI(s2)
    s2 = s2.select('ndvi')

    ### ---- Result ---- ###
    ResultsValues = CalculateMeanNdvi(image=s2,studyArea=studyArea)
    
    return(ResultsValues,s2)


## --- Create a grid for dates by n-days ---- ###
def CreateGrid(days,dateStart,dateEnd):
    size = ((dateEnd-dateStart).days)
    grid_dates = [dateStart + relativedelta(days=x) for x in range(0,size,days)] 
    return(grid_dates)


### ---- interpolation ---- ###
def interpolation_spline(data):
    out = data.dropna()
    x = list(out.index)
    y = list(out['nvdi'])
    tck = interpolate.splrep(x, y)
    ### --- Interpolate ---- ###
    data.loc[data['nvdi'].isna(),'nvdi'] = list(map(lambda x: float(interpolate.splev(x, tck)), list(data[data['nvdi'].isna()].index)))
    return(data)



## 1. Define zones 
with open('data/circle1.geojson', 'r') as j:
     hotspot1 = json.loads(j.read())

with open('data/circle2.geojson', 'r') as j:
     hotspot2 = json.loads(j.read())

with open('data/circle3.geojson', 'r') as j:
     hotspot3 = json.loads(j.read())

with open('data/aggregate.geojson', 'r') as j:
     aggregate = json.loads(j.read())
        
        
## 2. Create grid dates 
AggregateResults = dict()

for area in ['hotspot1','hotspot2','hotspot3','aggregate']:
    ###### ------- Create Grid ------ ####
    dateStart = datetime.datetime.strptime('01/04/2021', '%d/%m/%Y') 
    dateEnd = datetime.datetime.strptime('01/10/2021', '%d/%m/%Y')  
    GridDates = CreateGrid(days=14,dateStart=dateStart,dateEnd=dateEnd)
    ### ---- Order grid dates --- ###
    GridDates = pd.concat([pd.DataFrame({'start':[GridDates[x]],'end':GridDates[x+1]}) for x in range(0,len(GridDates)-1)]).reset_index(drop=True)
    #### ---- Init images ----- ####
    GridDates['images'] = None
    #### ---- Init values ----- ####
    GridDates['nvdi'] = None
    
    ### ----- Calculate NDVI for each date ---- #### 
    for j in list(GridDates[GridDates['images'].isna()].index):
        try: 
            #### ------ For hotspot1 ----- ####
            if (area == 'hotspot1'):
                ### ---- For each date: Create time line--- ##
                ndvi_mean,ndvi_image=CalculateNdvi(startyear=GridDates['start'].iloc[j],endyear=GridDates['end'].iloc[j],geojson=hotspot1)
            #### ------ For hotspot2 ----- ####
            elif (area == 'hotspot2'): 
                ### ---- For each date: Create time line--- ##
                ndvi_mean,ndvi_image=CalculateNdvi(startyear=GridDates['start'].iloc[j],endyear=GridDates['end'].iloc[j],geojson=hotspot2)
            elif (area == 'hotspot3'): 
                #### ------ For hotspot3 ----- ####
                ndvi_mean,ndvi_image=CalculateNdvi(startyear=GridDates['start'].iloc[j],endyear=GridDates['end'].iloc[j],geojson=hotspot3)
            elif (area == 'aggregate'): 
                ### ---- For each date: Create time line--- ##
                ndvi_mean,ndvi_image=CalculateNdvi(startyear=GridDates['start'].iloc[j],endyear=GridDates['end'].iloc[j],geojson=aggregate)

            GridDates.loc[j,'images'] = ndvi_image
            GridDates.loc[j,'nvdi'] = ndvi_mean
        except: 
            pass 
        
    ### ----- Interpolate --- ####
    GridDates = interpolation_spline(data=GridDates)
    ### ---- Storage results ---- ### 
    AggregateResults[area] = GridDates


### ------ Storage results ---- ###
pickle.dump(AggregateResults, open("outputs/NDVI.pickle", "wb"))  # save it into a file named save.p


####### ------ Outputs ------ ###########
### --- Graphs timeline --- ###
fig = px.line(AggregateResults['hotspot1'], x='start', y='nvdi', title='')
fig.update_traces(line=dict(color="green", width=3.5))

fig.update_layout(
    xaxis_title="",plot_bgcolor='white',
    yaxis_title="NDVI",
    font=dict(
        size=26
    )
)
fig.write_html('graph.html')



