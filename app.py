import folium
import geojson
import json
import pandas as pd
import geopandas as gpd
import re
import pickle
import numpy as np
import base64
###### ------ Dash ------ #### 
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from waitress import serve
import ee
#### ------ Load credentials by key------ #####
Credentials = ee.ServiceAccountCredentials('ge.gonzalez100@gmail.com','data/key.json')
ee.Initialize(Credentials)



##### ----- Create the map ----- #### 
def create_layer(self, ee_object, vis_params, name):
        
    try:    
        if isinstance(ee_object, ee.image.Image):    
            map_id_dict = ee.Image(ee_object).getMapId(vis_params)
            folium.raster_layers.TileLayer(
            tiles = map_id_dict['tile_fetcher'].url_format,
            attr = 'Google Earth Engine',
            name = name,
            overlay = True,
            control = True
            ).add_to(self)

        elif isinstance(ee_object, ee.imagecollection.ImageCollection):    
            ee_object_new = ee_object.mosaic()
            map_id_dict = ee.Image(ee_object_new).getMapId(vis_params)
            folium.raster_layers.TileLayer(
            tiles = map_id_dict['tile_fetcher'].url_format,
            attr = 'Google Earth Engine',
            name = name,
            overlay = True,
            control = True
            ).add_to(self)

        elif isinstance(ee_object, ee.geometry.Geometry):    
            folium.GeoJson(
            data = ee_object.getInfo(),
            name = name,
            overlay = True,
            control = True
            ).add_to(self)

        elif isinstance(ee_object, ee.featurecollection.FeatureCollection):  
            ee_object_new = ee.Image().paint(ee_object, 0, 2)
            map_id_dict = ee.Image(ee_object_new).getMapId(vis_params)
            folium.raster_layers.TileLayer(
            tiles = map_id_dict['tile_fetcher'].url_format,
            attr = 'Google Earth Engine',
            name = name,
            overlay = True,
            control = True
            ).add_to(self)
        
    except:
        print("Could not display {}".format(name))

        
class CreateMap:
    # The init method or constructor  
    def __init__(self, location,zoom_start,height):  
            
        # Instance Variable  
        self.location = location
        self.zoom_start = zoom_start
        self.height = height
    
    def Initialize(self):
        folium.Map.add_ee_layer = create_layer
        return folium.Map(location=self.location, 
                          zoom_start=self.zoom_start, 
                          height=self.height,tiles='cartodbpositron')


##### ----- Graph map ------ ###
def Graph_map(img_graph,paddocks):
    mapObject = CreateMap(location=[-34.849247,149.677968],zoom_start=14,height=600)
    my_map = mapObject.Initialize()
    ndviParams = {min: -1, max: 1, 'palette': ['red', 'white', 'green']};
    my_map.add_ee_layer(img_graph,ndviParams,'ndvi')
    paddocks.apply(lambda x: folium.Marker([x['Latitude'],x['Longitude']], 
                                           icon=folium.features.CustomIcon('assets/icons/land.png', 
                                                                           icon_size=(35,35)),
                                           popup='Canola Paddock').add_to(my_map) ,axis=1)
    return(my_map.get_root().render())
    return(my_map)



### ----- Load outputs ------ ####
paddocks = pd.read_csv('data/coords.csv')
data = pickle.load(open("outputs/NDVI.pickle", "rb"))

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
### --- Principal Title --- ### 
app.title = 'CSIRO - Canola'
### ---------------- Logo - Image ------------------ ###
Header = dbc.NavbarSimple(children=[
html.Img(src='https://style.csiro.au/assets/media/CSIRO-logo--white.png',width=60,height=60)],
    brand="NDVI - Dashboard",
    brand_href="#",
    color="black",
    dark=True,
)

##### ------ Tooltips ------ ######
def Tooltip_area(ID):
    return(html.Div(
    [html.Span(children="Select the area to analyse", style={'color':'black'},id="tooltip"+ID),
        dbc.Tooltip(style={'font-size':'16px'},children="Please select the area you would like to analyse. ",
            target="tooltip"+ID)]))

def Tooltip_time(ID):
    return(html.Div(
    [html.Span(children="Select the time to analyse", style={'color':'black'},id="tooltip"+ID),
        dbc.Tooltip(style={'font-size':'16px'},children="Please select the time you would like to analyse. ",
            target="tooltip"+ID)]))



####### ------------ Body ----------- ######### 
Body = html.Div([dbc.Toast([html.Div([html.P('Welcome to NDVI Dashboard. This tool shows the heatmap of NDVI by date. Please choose the area and the time.'),
    dbc.Row(html.Img(src='data:image/png;base64,{}'.format(base64.b64encode(open('assets/scale.png', 'rb').read()).decode()),height="120px"),justify='center'),html.Br(),
    dbc.Row(html.Label(html.B(Tooltip_area(ID='TWO'), style={'textAlign': 'center','color': 'black','marginTop': 20})),justify="center"),
    dcc.Dropdown(id='area',
        options=[{'label': 'All the paddocks', 'value': 'aggregate'},{'label': 'Paddock 1', 'value': 'hotspot1'},
            {'label': 'Paddock 2', 'value': 'hotspot3'},
            {'label': 'Paddock 3', 'value': 'hotspot2'}
        ],
        value='aggregate'
    ),html.Br(),dbc.Row(html.Label(html.B(Tooltip_time(ID='ONE'), style={'textAlign': 'center','color': 'black','marginTop': 20})),justify="center"),
    dcc.Slider(
    id='value_date',
    min=0,
    max=12,
    value=0,
    marks={
        0: {'label': str(data['aggregate']['start'].iloc[0].strftime("%d %b")), 'style': {'color': '#0d7722'}},
        3: {'label': str(data['aggregate']['start'].iloc[3].strftime("%d %b")), 'style': {'color': '#0d7722'}},
        6: {'label': str(data['aggregate']['start'].iloc[6].strftime("%d %b")), 'style': {'color': '#0d7722'}},
        9: {'label': str(data['aggregate']['start'].iloc[9].strftime("%d %b")), 'style': {'color': '#0d7722'}},
        12: {'label': str(data['aggregate']['start'].iloc[11].strftime("%d %b")), 'style': {'color': '#0d7722'}}
    },
    included=False),html.Br(),html.Div(id='outputs_map')])],
                    header= 'NDVI',header_style = {'textAlign': 'center','height': 30, 
                          'display': 'block', 'margin-left': 'auto',
                          'margin-right': 'auto','width': '100%',
                          'color': '#ffffff',"background-color": '#292929'},
                   style={"max-width": "2000px","opacity": 0.9, 
                          "background-color": "#f5f5f5",'textAlign': 'center'})],style={
            'marginTop': '5%',
            'marginBottom': '3%',
            'marginLeft': '2%',
            'marginRight': '2%',
            'padding': 0,'background': "#f5f5f5","opacity": 1,})


@app.callback(
    Output('outputs_map', 'children'),
    [Input('area', 'value'),
     Input('value_date', 'value')])
def Decision_analisis(area,value_date): 

    #### ---- Create map --- ### 
    result_map=Graph_map(img_graph=data[area]['images'].iloc[int(value_date)],paddocks=paddocks)
    text_overal = data[area]['nvdi'].iloc[int(value_date)]
    text_shows = 'The average NDVI in the choose area was is ' + str(round(text_overal,2))
    html_map = html.Section(
        children=[html.H5(text_shows,style={'textAlign': 'center','color': 'black','font-size': '12px'}),html.Iframe(id='Mapa_general',srcDoc = str(result_map) ,height = 600, 
            style={'display': 'flex','width': '100%','border': 0,
               'top': 0,
               'left' : 0,
               'bottom': 0,
               'right': 0} )],
        style={
            'padding': 0,
            'margin': 0,
            'borderRadius': 0,
            'border': 'thin lightgrey ridge',
            'border-color': '#c7bfbf',
            'border-width': '0px','background': '#f5f5f5',"opacity": 0.9
        })
    
    return(html_map)

########## ------------- Footer ------------- ############# 
Footer = html.Div([html.H5(
        children='Germán González - Copyright ©  2021.',
        style={'textAlign': 'center','color': 'black'})])

app.layout = html.Div(children=[Header,Body,Footer])
############# --------------- Server ----------- ############# 
serve(app.server,host='127.0.0.1',port=7787) #this connects with the server

######## ------- Desplegar servidor -------- ########
server = create_server(app,threaded=True)
server.run()

##### ----------- Layout: All elements --------- ########
#server = app.server



