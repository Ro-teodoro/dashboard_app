

from dash import Dash, html, dcc, Input, Output, State ,ctx
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv
import psycopg2
import geopandas as gpd
import sys
import warnings
warnings.filterwarnings('ignore')

#funciones
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#**************************************************************************#
#███████╗██╗   ██╗███╗   ██╗ ██████╗████████╗██╗ ██████╗ ███╗   ██╗███████╗#
#██╔════╝██║   ██║████╗  ██║██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║██╔════╝#
#█████╗  ██║   ██║██╔██╗ ██║██║        ██║   ██║██║   ██║██╔██╗ ██║███████╗#
#██╔══╝  ██║   ██║██║╚██╗██║██║        ██║   ██║██║   ██║██║╚██╗██║╚════██║#
#██║     ╚██████╔╝██║ ╚████║╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║███████║#
#╚═╝      ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝#
#**************************************************************************#

def connect(params_dic):
    """ 
    Generar la coneccion con la base de datos

    Args:
        params_dic (dic) -> diccionario con los datos que se usan para la conecicon

    Returns:
        (obj) -> coneccion a base de datos
    """
    conn = None
    try:
        # connect to the PostgreSQL server
        conn = psycopg2.connect(**params_dic)
    except (Exception, psycopg2.DatabaseError) as error:
        sys.exit(1) 
    return conn

def query_columnas(conn,esquema = 'Dashboards', datos = 'caracteristicas_poblacionales'):
    """ 
    Obtencion de columnas del tema especificado

    Args:
        conn (obj) -> coneccion a base de datos
        esquema (str) -> string con el nombre del esquema al que se conecta la bse de datos
        datos (str) -> nombre de la tabla a la que se piden las columnas

    Returns:
        (str) -> cadena de caracteres con el query para obtener las columnas de una tabla.
    """

    Q = """SELECT * FROM (                                                
        SELECT column_name FROM information_schema.columns                
            WHERE table_schema = '{}' AND table_name   = '{}') as tab     
                WHERE column_name ~ '^[A-Z].*$' ;""".format(esquema,datos) #  se genera el query para obtener las columnas de cada base de datos  
    
    cursor = conn.cursor()
    try: 
        df = pd.read_sql(Q, con=conn) #se transfiere el query a un DF de pandas
    except: 
        return "Error: en query_columnas"
    cursor.close()

    return df['column_name'].to_list() # se regresa el DF como una lista

def col_description_query(tabla= 'caracteristicas_poblacionales',esquema='Dashboards'):
    '''Generador de query para la obtencion de la descripcion de las columnas

    Args:
        tabla (str) -> string con el nombre de la tabla de datos de donde se obtienen las columnas
        esquema (str) -> string con el nombre del esquema al que se conecta la bse de datos
        cols (list) -> Lista con strings de cada nombre de columna a obtener 
    
    '''

    QQ = """

    select * FROM (

    SELECT COALESCE(c.column_name, 'table') AS col, d.description
    FROM pg_catalog.pg_description AS d
    LEFT JOIN information_schema.columns AS c ON
      c.ordinal_position = d.objsubid
      AND c.table_name = '{}'
    WHERE objoid = (
      SELECT oid
      FROM pg_class
      WHERE relname = '{}' AND relnamespace = (
        SELECT oid FROM pg_catalog.pg_namespace WHERE nspname = '{}'
      )
    )
    	) as tt ;

    """.format(tabla,tabla,esquema)

    return QQ

def map_query_constructor(esquema = 'Dashboards', 
                      base = 'manzanas', 
                      datos = 'caracteristicas_poblacionales' , 
                      agreg = 'sectores',
                      col1_1 = 'POB1',
                      col1_2 = 'POB2',
                      estad1_1 = 'suma',
                      estad1_2 = 'suma'
                      ):
    """ 
    Constructor de query para la obtencion de la tabla c yo con la union y la agrupacion

    Args:
        esquema (str) -> string con el nombre del esquema al que se conecta la bse de datos
        base (str) -> string con el nombre de la tabla con la minima granularidad
        datos (str) -> nombre de la tabla a la que se piden las columnas
        agreg (str) -> string con el nombre de la tabla con la que se agrupara y unira la base
        col1_1 (str) -> string con el nombre de la columna del primer campo a utilizar en el mapa 1
        col1_2 (str) -> string con el nombre de la columna del segundo campo a utilizar en la grafica 1
        col2_1 (str) -> string con el nombre de la columna del primer campo a utilizar en el mapa 2
        col2_2 (str) -> string con el nombre de la columna del segundo campo a utilizar en la grafica 2
        estad1_1 (str) -> string con el nombre del estadistico que se usara para col1_1 
        estad1_2 (str) -> string con el nombre del estadistico que se usara para col1_2 
        estad2_1 (str) -> string con el nombre del estadistico que se usara para col2_1 
        estad2_2 (str) -> string con el nombre del estadistico que se usara para col2_2 

    Returns:
        (str) -> cadena de caracteres con el query para obtener la tabla de datos a usar en el dashboard.
    """

    if datos == 'Poblacion' : d = 'caracteristicas_poblacionales' #  elije entre las opciones de tablas de datos para la variable datos
    elif datos == 'Economia' : d = 'caracteristicas_economicas'   

    try: 
        Q = 'select ' 

        Q = Q + '{} as {}, '.format(agreg, agreg[0:4]) #elije las columnas segun la agregacion que se necesita

        Q = Q + 'COUNT({}) as {}_cont, '.format(agreg,agreg)  #genera la columna del conteo segun la agregacion que se necesita

        #get statistics
        l = [col1_1,col1_2]
        e = [estad1_1, estad1_2]
        rep =[]

        for i in range(0,len(l)):

            if l[i] not in rep:
                #elije el estadistico para cada columna elegida
                if e[i]== 'suma' : est = 'SUM'
                elif e[i]== 'prom' : est = 'AVG'
                elif e[i]== 'count' : est = 'COUNT'
                else: est = 'COUNT'
                
                Q = Q +  '{}(tabla."{}") as "{}", '.format(est, l[i], l[i])

                rep.append(l[i])    


        Q = Q[:-2] + ' '

        Q = Q + 'FROM (SELECT {}, {}.* '.format(agreg,d) #inicia el query de union

        Q = Q + 'FROM "{}".{} '.format(esquema, base) 

        Q = Q + 'LEFT JOIN "{}".{} '.format(esquema, d)  

        Q = Q + 'ON {}.cvegeo = {}.cvegeo ) as tabla GROUP BY {};'.format(base, d,agreg[0:4] ) #agrupacion

    except:

        print('error en query constructor.')

    return Q

def geoQuery(esquema = 'Dashboards',agreg = 'sectores'): 
    """ 
    Constructor de query para la obtencion de los Geo Data Frames

    Args:
        esquema (str) -> string con el nombre del esquema al que se conecta la bse de datos
        agreg (str) -> string con el nombre de la tabla con la que se agrupara y unira la base

    Returns:
        (str) -> cadena de caracteres con el query para obtener la tabla de datos a usar en el dashboard.

    """ 

    return 'SELECT * FROM "{}"."{}" '.format(esquema,agreg)

def postgresql_to_dataframe(conn, select_query):
    """ 
    Funcion para obtener el DataFrame a partir de una query

    Args:
        conn (obj) -> coneccion a base de datos
        select_query (str) -> string con la consulta para obtener un DataFrame


    Returns:
        (obj) -> Dataframe obtenido a partir de la query
    
    """

    cursor = conn.cursor()
    try:
        df = pd.read_sql( select_query, con=conn ) #obtener DF de un query de posrtgresql
    except:
        
       return "Error: en postgresql_to_dataframe"
    
    cursor.close()

    return df

def postgresql_to_GEOdataframe(conn, select_query):
    """ 
    Funcion para obtener el GeoDataFrame a partir de una query

    Args:
        conn (obj) -> coneccion a base de datos
        select_query (str) -> string con la consulta para obtener un GeoDataFrame


    Returns:
        (obj) -> GeoDataframe obtenido a partir de la query
    
    """
    cursor = conn.cursor()
    try:
        gdf = gpd.read_postgis(select_query, con=conn)
    except:
        
       return "Error: en postgresql_to_GEOdataframe"
    
    cursor.close()

    return gdf

def mapa(conn, esquema = 'Dashboards',
    base = 'manzanas' ,
    datos = 'caracteristicas_poblacionales',

    col1_1 = 'POB1',
    col1_2 = 'POB2',
    estad1_1 = 'suma',
    estad1_2 = 'suma',

    agreg1 = 'sectores'):
    """ descripcion de funcion"""

    #obtener los primeros 4 caracteres de la columna de agregacion para crear los nombres de las nuevas columnas de agrupacion
    loc1 = agreg1[0:4]

    #get column descriptions
    l = [col1_1,col1_2]
    rep =[]

    for i in range(0,len(l)):
        if l[i] not in rep:
            rep.append(l[i])
            
    if datos == 'Poblacion' : d = 'caracteristicas_poblacionales' #  elije entre las opciones de tablas de datos para la variable datos
    elif datos == 'Economia' : d = 'caracteristicas_economicas'
    
    col_desc = postgresql_to_dataframe(conn, col_description_query(tabla=d, esquema=esquema) )

    df1 = postgresql_to_dataframe(conn,map_query_constructor(esquema=esquema, #obtener el primer DF
                                                         agreg=agreg1, 
                                                         base=base ,
                                                         datos=datos ,
                                                         col1_1=col1_1,
                                                         col1_2=col1_2,
                                                         estad1_1=estad1_1,
                                                         estad1_2=estad1_2
                                                         ))        

    gdf1 = postgresql_to_GEOdataframe(conn, geoQuery(agreg=agreg1) ) #obtener el primer GDF
    gdf1.set_index('id', inplace=True)

    #graficando el primer mapa

    un1 = pd.merge(gdf1,df1,how='left', left_on=gdf1.index,right_on=loc1 )
    un1.set_index(loc1, inplace = True)
    un1 = un1.fillna(0)
    un1[loc1]= un1.index.values
    l1 = un1.columns.to_list()
    l1.remove('geom')



    labs1 = { #labels
            col1_2: estad1_1 + ' de ' + col_desc[col_desc['col']== col1_2].iloc[0,1],
            col1_1: estad1_2 + ' de ' + col_desc[col_desc['col']== col1_1].iloc[0,1],
            'ident':agreg1,
            agreg1+'_cont':'conteo de manzanas',
            loc1:agreg1,
            'index':'id'
            }

    #----------------------------------------------------------------------------------------------------
    fig = px.choropleth_mapbox(un1, width = 800,
                               geojson=un1.geometry, 
                               locations=un1.index , color=col1_1,
                               hover_name= 'ident',
                               hover_data=l1,
                               color_continuous_scale="Viridis",
                               range_color=(df1[col1_1].min(), df1[col1_1].max()),
                               mapbox_style="carto-positron",
                               zoom=10, 
                               center = {"lat": 32.484948, "lon": -116.936904},
                               opacity=0.5,
                               labels=labs1
                               )
    fig.update_layout(margin={"r":10,"t":10,"l":10,"b":10},coloraxis_colorbar = dict( titleside = 'right'), autosize=True)

    return fig ,un1

def grafica(conn, esquema = 'Dashboards',
    base = 'manzanas' ,
    datos = 'caracteristicas_poblacionales',

    col1_1 = 'POB1',
    col1_2 = 'POB2',
    estad1_1 = 'suma',
    estad1_2 = 'suma',
    select_1 = [],

    agreg1 = 'sectores'):
    """ descripcion de funcion"""

    #obtener los primeros 4 caracteres de la columna de agregacion para crear los nombres de las nuevas columnas de agrupacion
    loc1 = agreg1[0:4]

    #get column descriptions
    l = [col1_1,col1_2]
    rep =[]

    for i in range(0,len(l)):
        if l[i] not in rep:
            rep.append(l[i])
            
    if datos == 'Poblacion' : d = 'caracteristicas_poblacionales' #  elije entre las opciones de tablas de datos para la variable datos
    elif datos == 'Economia' : d = 'caracteristicas_economicas'
    
    col_desc = postgresql_to_dataframe(conn, col_description_query(tabla=d, esquema=esquema) )

    df1 = postgresql_to_dataframe(conn,map_query_constructor(esquema=esquema, #obtener el primer DF
                                                         agreg=agreg1, 
                                                         base=base ,
                                                         datos=datos ,
                                                         col1_1=col1_1,
                                                         col1_2=col1_2,
                                                         estad1_1=estad1_1,
                                                         estad1_2=estad1_2
                                                         ))        

    gdf1 = postgresql_to_GEOdataframe(conn, geoQuery(agreg=agreg1) ) #obtener el primer GDF
    gdf1.set_index('id', inplace=True)

    #se seleccionan los datos desde la seleccion del mapa para visualizarlos en grafica
    if select_1 == []: sel1 = df1[loc1].to_list()
    else:sel1 = select_1

    #graficando el primer mapa

    un1 = pd.merge(gdf1,df1,how='left', left_on=gdf1.index,right_on=loc1 )
    un1.set_index(loc1, inplace = True)
    un1 = un1.fillna(0)
    un1[loc1]= un1.index.values
    l1 = un1.columns.to_list()
    l1.remove('geom')
    labs1 = {
            col1_2: estad1_1 + ' de ' + col_desc[col_desc['col']== col1_2].iloc[0,1],
            col1_1: estad1_2 + ' de ' + col_desc[col_desc['col']== col1_1].iloc[0,1],
            'ident':agreg1,
            agreg1+'_cont':'conteo de manzanas',
            loc1:agreg1,
            'index':'id'
            }

    #----------------------------------------------------------------------------------------------------
    fig = px.bar(un1.loc[un1[loc1].isin(sel1)] , width=800,
                    x=col1_1, y='ident',
                    orientation='h' ,
                    hover_name= 'ident', 
                    hover_data=l1,
                    color = col1_2,
                    labels=labs1
                    )
    
    fig.update_layout(margin={"r":10,"t":10,"l":10,"b":10},
                        height = len(un1.loc[un1[loc1].isin(sel1)].index) * 50, 
                        coloraxis_colorbar = dict( titleside = 'right'),
                        barmode='stack', 
                        yaxis={'categoryorder':'total ascending'}
                        )

    fig.update_traces(width= 0.75 )

    return fig

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#************************************************************************************#
#██████╗  █████╗ ██████╗  █████╗ ███╗   ███╗███████╗████████╗███████╗██████╗ ███████╗#
#██╔══██╗██╔══██╗██╔══██╗██╔══██╗████╗ ████║██╔════╝╚══██╔══╝██╔════╝██╔══██╗██╔════╝#
#██████╔╝███████║██████╔╝███████║██╔████╔██║█████╗     ██║   █████╗  ██████╔╝███████╗#
#██╔═══╝ ██╔══██║██╔══██╗██╔══██║██║╚██╔╝██║██╔══╝     ██║   ██╔══╝  ██╔══██╗╚════██║#
#██║     ██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║███████╗   ██║   ███████╗██║  ██║███████║#
#╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝#
#************************************************************************************#                                                                                    

load_dotenv()

param_dic = { #} parametros de coneccion
    "host"      : os.getenv('HOST'),
    "database"  : os.getenv('DATABASE'),
    "user"      :  os.getenv('USER'),
    "password"  : os.getenv('PASSWORD')
    } 

esqu = os.getenv('esqu') # lista de esquemas

estad = os.getenv('estad').split(',') #lsita de estadisticos
temas =os.getenv('temas').split(',') #lista de temas
bds = os.getenv('bds').split(',') #lsita de nombre de tablas de temas
agreg = os.getenv('agreg').split(',') #lista de agregaciones

conn = connect(param_dic) #coneccion a base de datos

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

#********************************************************************************#
# █████╗ ██████╗ ██████╗     ██╗      █████╗ ██╗   ██╗ ██████╗ ██╗   ██╗████████╗#
#██╔══██╗██╔══██╗██╔══██╗    ██║     ██╔══██╗╚██╗ ██╔╝██╔═══██╗██║   ██║╚══██╔══╝#
#███████║██████╔╝██████╔╝    ██║     ███████║ ╚████╔╝ ██║   ██║██║   ██║   ██║   #
#██╔══██║██╔═══╝ ██╔═══╝     ██║     ██╔══██║  ╚██╔╝  ██║   ██║██║   ██║   ██║   #
#██║  ██║██║     ██║         ███████╗██║  ██║   ██║   ╚██████╔╝╚██████╔╝   ██║   #
#╚═╝  ╚═╝╚═╝     ╚═╝         ╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝  ╚═════╝    ╚═╝   #
#********************************************************************************#                                                                                

app.layout = html.Div([

    html.Div([

            dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle( id ='m_title', children="Fullscreen modal")),
            dcc.Graph(id='map_mod',style={"height": "100%", "width": "100%"})
        ],
        id="modal-fs",
        fullscreen=True,
        is_open=False
        ),

        html.Div([  

            dcc.Markdown(
                '## PANEL 1',
                id='mk_1'),

            dcc.Dropdown(
                temas,
                id='selector_de_tema1',
                placeholder="Selecciona un tema"
            ),

            dcc.Dropdown(
                agreg,
                agreg[2],
                id='agreg_1',
                placeholder="Selecciona una agregacion",
                disabled = True
            ) ,
            dcc.Dropdown(
                id='col_1',
                placeholder="Selecciona un columna para el mapa",
                optionHeight=70,
                disabled = True
            ) ,
            dcc.Dropdown(
                estad,
                estad[0],
                id='tipo_1-1',
                placeholder="Selecciona un estadistico",
                disabled = True
            ) ,
            dcc.Dropdown(
                id='color_1', 
                placeholder="Selecciona un columna para graficar",
                optionHeight=70,
                disabled = True
            ),
            dcc.Dropdown(
                estad,
                estad[0],
                id='tipo_1-2',
                placeholder="Selecciona un estadistico",
                disabled = True
            ),
            html.Button(
                'Trigger_1',
                id='boton_1'
            ),
            dcc.Markdown(
                '## PANEL 2',
                id= 'mk_2'),

            dcc.Dropdown(
                temas,
                id='selector_de_tema2',
                placeholder="Selecciona un tema"
            ),

            dcc.Dropdown(
                agreg,
                agreg[2],
                id='agreg_2',
                placeholder="Selecciona una agregacion",
                disabled = True
            ) ,
            dcc.Dropdown(
                id='col_2',
                placeholder="Selecciona un columna para el mapa",
                optionHeight=70,
                disabled = True
            ) ,
            dcc.Dropdown(
                estad,
                estad[0],
                id='tipo_2-1',
                placeholder="Selecciona un estadistico",
                disabled = True
            ) ,
            dcc.Dropdown(
                id='color_2', 
                placeholder="Selecciona un columna para graficar",
                optionHeight=70,
                disabled = True
            ),
            dcc.Dropdown(
                estad,
                estad[0],
                id='tipo_2-2',
                placeholder="Selecciona un estadistico",
                disabled = True
            ),
            html.Button(
                'Trigger_2',
                id='boton_2'
            ),
            
            html.Div(id='hidden-div', style={'display':'none'}, children = 'mhe') #este se va a eliminar alv

            ], style={'width': '15%', 'display': 'inline-block', "height": "350"}),

        html.Div([

            html.Div([
                dcc.Markdown('## MAPA 1'), 
                html.Button( 'maximizar mapa' ,id="max_map1" ,disabled = True),
                html.Button('Get Data tab1',id='tabla1',disabled = True),
                dcc.Download(id="download-csv1"),   

                html.Div([

                    dcc.Graph(id='mapa_1',style={ 'maxWidth': '900px'}),
                    
                    dcc.Graph(id='grafica_1', style={'overflowY': 'scroll', 'maxHeight': '500px', 'maxWidth': '500'}),

                ], style={'display': 'inline-block'})

            ], style={'width': '50%', 'float': 'left','display': 'inline-block'}),

            html.Div([
                dcc.Markdown('## MAPA 2'),
                html.Button( 'maximizar mapa' ,id="max_map2",disabled = True ),
                html.Button('Get Data tab2',id='tabla2',disabled = True),
                dcc.Download(id="download-csv2"),

                html.Div([

                    dcc.Graph(id='mapa_2',style={ 'maxWidth': '900px'}),
                    
                    dcc.Graph(id='grafica_2' , style={'overflowY': 'scroll', 'maxHeight': '500px', 'maxWidth': '500'} ),

                ], style={'display': 'inline-block'})

            ], style={'width': '50%', 'float': 'right','display': 'inline-block'})


        ],style={'width': '85%', 'float': 'right', 'display': 'inline-block'})

    ]),

])

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#********************************************************************************************************#
#███████╗██╗██████╗ ███████╗████████╗     ██████╗ █████╗ ██╗     ██╗     ██████╗  █████╗  ██████╗██╗  ██╗#
#██╔════╝██║██╔══██╗██╔════╝╚══██╔══╝    ██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝#
#█████╗  ██║██████╔╝███████╗   ██║       ██║     ███████║██║     ██║     ██████╔╝███████║██║     █████╔╝ #
#██╔══╝  ██║██╔══██╗╚════██║   ██║       ██║     ██╔══██║██║     ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ #
#██║     ██║██║  ██║███████║   ██║       ╚██████╗██║  ██║███████╗███████╗██████╔╝██║  ██║╚██████╗██║  ██╗#
#╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝        ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝#
#********************************************************************************************************#                                                                                                    

@app.callback(
    [
    Output(component_id='col_1', component_property='options'),
    Output(component_id='color_1', component_property='options'),
    Output(component_id='tipo_1-1', component_property='disabled'),
    Output(component_id='tipo_1-2', component_property='disabled'),
    Output(component_id='agreg_1', component_property='disabled'),
    Output(component_id='col_1', component_property='disabled'),
    Output(component_id='color_1', component_property='disabled'),
    ],

    [
    Input(component_id='selector_de_tema1', component_property= 'value')
    ], prevent_initial_call=True
)

def first( tema):
    print('first callback...')
    if tema == 'Poblacion':
        d ='caracteristicas_poblacionales'
        c = query_columnas(conn,datos=d)
        
    elif tema == 'Economia':
        d='caracteristicas_economicas'
        c = query_columnas(conn,datos=d)
    

    col_desc = postgresql_to_dataframe(conn, col_description_query(tabla=d) )
    c = col_desc.groupby(['col']).apply(lambda x: x['description'].tolist()).to_dict()

    return c,c, False, False, False, False, False

@app.callback(
    [
    Output(component_id='col_2', component_property='options'),
    Output(component_id='color_2', component_property='options'),
    Output(component_id='tipo_2-1', component_property='disabled'),
    Output(component_id='tipo_2-2', component_property='disabled'),
    Output(component_id='agreg_2', component_property='disabled'),
    Output(component_id='col_2', component_property='disabled'),
    Output(component_id='color_2', component_property='disabled')
    ],

    [
    Input(component_id='selector_de_tema2', component_property= 'value'),
    ], prevent_initial_call=True
)

def second( tema):
    print('first callback...')
    if tema == 'Poblacion':
        d ='caracteristicas_poblacionales'
        c = query_columnas(conn,datos=d)
        
    elif tema == 'Economia':
        d='caracteristicas_economicas'
        c = query_columnas(conn,datos=d)
    

    col_desc = postgresql_to_dataframe(conn, col_description_query(tabla=d) )
    c = col_desc.groupby(['col']).apply(lambda x: x['description'].tolist()).to_dict()

    return c,c, False, False, False, False, False

#***********************************************************************************************************************#
#███████╗███████╗ ██████╗ ██████╗ ███╗   ██╗██████╗      ██████╗ █████╗ ██╗     ██╗     ██████╗  █████╗  ██████╗██╗  ██╗#
#██╔════╝██╔════╝██╔════╝██╔═══██╗████╗  ██║██╔══██╗    ██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝#
#███████╗█████╗  ██║     ██║   ██║██╔██╗ ██║██║  ██║    ██║     ███████║██║     ██║     ██████╔╝███████║██║     █████╔╝ #
#╚════██║██╔══╝  ██║     ██║   ██║██║╚██╗██║██║  ██║    ██║     ██╔══██║██║     ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ #
#███████║███████╗╚██████╗╚██████╔╝██║ ╚████║██████╔╝    ╚██████╗██║  ██║███████╗███████╗██████╔╝██║  ██║╚██████╗██║  ██╗#
#╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═════╝      ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝#
#***********************************************************************************************************************#

@app.callback(
    [
    Output(component_id='mapa_1', component_property='figure'),
    Output(component_id='tabla1', component_property='disabled'),
    Output(component_id='max_map1',component_property='disabled')
    ],
    [
    Input(component_id='boton_1', component_property= 'n_clicks'),
    State(component_id='selector_de_tema1', component_property= 'value'),
    State(component_id='tipo_1-1', component_property='value'),
    State(component_id='tipo_1-2', component_property='value'),
    State(component_id='agreg_1', component_property='value'),
    State(component_id='col_1', component_property='value'),
    State(component_id='color_1', component_property='value')
    ], prevent_initial_call=True
)

def mapas(n, tema1, est1_1, est1_2, agreg_1, col_1, color_1 ):
    print('second.1 callback...')
    s1= None
    ss1 = []

    if s1 is None:
        pass
    else:
        for i in s1['points']:
            ss1.append(i['location'])

    m1 = mapa(conn,datos = tema1, agreg1 = agreg_1,col1_1 = col_1 ,col1_2=color_1,estad1_1 = est1_1, estad1_2 = est1_2)[0]

    return m1, False, False


@app.callback(
    [
    Output(component_id='mapa_2', component_property='figure'),
    Output(component_id='tabla2', component_property='disabled'),
    Output(component_id='max_map2',component_property='disabled')
    ],
    [
    Input(component_id='boton_2', component_property= 'n_clicks'),
    State(component_id='selector_de_tema2', component_property= 'value'),
    State(component_id='tipo_2-1', component_property='value'),
    State(component_id='tipo_2-2', component_property='value'),
    State(component_id='agreg_2', component_property='value'),
    State(component_id='col_2', component_property='value'),
    State(component_id='color_2', component_property='value')
    ], prevent_initial_call=True
)

def mapas(n, tema2,est2_1, est2_2 , agreg_2, col_2, color_2):
    print('second.2 callback...')

    s2 = None

    ss2 = []

    if s2  is None:
        pass
    else:
        for i in s2['points']:
            ss2.append(i['location'])

    m2 = mapa(conn, datos = tema2,agreg1 = agreg_2,col1_1 = col_2 ,col1_2=color_2,estad1_1 = est2_1, estad1_2 = est2_2)[0]

    return m2, False, False



#********************************************************************************************************#
#████████╗██╗  ██╗██╗██████╗ ██████╗      ██████╗ █████╗ ██╗     ██╗     ██████╗  █████╗  ██████╗██╗  ██╗#
#╚══██╔══╝██║  ██║██║██╔══██╗██╔══██╗    ██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝#
#   ██║   ███████║██║██████╔╝██║  ██║    ██║     ███████║██║     ██║     ██████╔╝███████║██║     █████╔╝ #
#   ██║   ██╔══██║██║██╔══██╗██║  ██║    ██║     ██╔══██║██║     ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ #
#   ██║   ██║  ██║██║██║  ██║██████╔╝    ╚██████╗██║  ██║███████╗███████╗██████╔╝██║  ██║╚██████╗██║  ██╗#
#   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═════╝      ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝#
#********************************************************************************************************#       

@app.callback(
Output(component_id='grafica_1', component_property='figure'),
[
Input(component_id='mapa_1', component_property= 'selectedData'),
State(component_id='selector_de_tema1', component_property= 'value'),
State(component_id='tipo_1-1', component_property='value'),
State(component_id='tipo_1-2', component_property='value'),
State(component_id='agreg_1', component_property='value'),
State(component_id='col_1', component_property='value'),
State(component_id='color_1', component_property='value')
], prevent_initial_call=True
)

def filt1(s1, tema, est1_1, est1_2, agreg_1, col_1, color_1 ):
    print('third callback...')
    ss1 =[]

    try:
        for i in s1['points']:

            ss1.append(i['location'])

    except:
        s1 = None
        pass

    g = grafica(conn, select_1=ss1, datos = tema, agreg1 = agreg_1, col1_1 = col_1, col1_2=color_1, estad1_1 = est1_1, estad1_2 = est1_2 ) 

    return g

@app.callback(

Output(component_id='grafica_2', component_property='figure')
,
[

Input(component_id='mapa_2', component_property= 'selectedData'),

State(component_id='selector_de_tema2', component_property= 'value'),

State(component_id='tipo_2-1', component_property='value'),
State(component_id='tipo_2-2', component_property='value'),
State(component_id='agreg_2', component_property='value'),
State(component_id='col_2', component_property='value'),
State(component_id='color_2', component_property='value')

], prevent_initial_call=True
)

def filt2(s2,  tema ,est2_1, est2_2 , agreg_2, col_2, color_2):
    print('third callback...')
    ss2 =[]

    try:
        for i in s2['points']:

            ss2.append(i['location'])
    except:
        s2 = None
        pass

    g = grafica(conn,select_1=ss2,datos = tema,agreg1 = agreg_2,col1_1 = col_2,col1_2=color_2, estad1_1 = est2_1, estad1_2 = est2_2) 

    return g


#**************************************************************************************************************#
#███████╗ ██████╗ ██████╗ ████████╗██╗  ██╗     ██████╗ █████╗ ██╗     ██╗     ██████╗  █████╗  ██████╗██╗  ██╗#
#██╔════╝██╔═══██╗██╔══██╗╚══██╔══╝██║  ██║    ██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝#
#█████╗  ██║   ██║██████╔╝   ██║   ███████║    ██║     ███████║██║     ██║     ██████╔╝███████║██║     █████╔╝ #
#██╔══╝  ██║   ██║██╔══██╗   ██║   ██╔══██║    ██║     ██╔══██║██║     ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ #
#██║     ╚██████╔╝██║  ██║   ██║   ██║  ██║    ╚██████╗██║  ██║███████╗███████╗██████╔╝██║  ██║╚██████╗██║  ██╗#
#╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝     ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝#                                                                                                          
#**************************************************************************************************************#                                                                                                     

@app.callback(
    Output("download-csv1", "data"),
    [
    Input("tabla1", "n_clicks"),
    State(component_id='selector_de_tema1', component_property= 'value'),
    State(component_id='tipo_1-1', component_property='value'),
    State(component_id='tipo_1-2', component_property='value'),
    State(component_id='agreg_1', component_property='value'),
    State(component_id='col_1', component_property='value'),
    State(component_id='color_1', component_property='value')
    ],prevent_initial_call=True,
)                                          

def download1(n, tema1, est1_1, est1_2, agreg_1, col_1, color_1 ):
    print('forth callback...')
    m1 = mapa(conn,datos = tema1, agreg1 = agreg_1,col1_1 = col_1 ,col1_2=color_1,estad1_1 = est1_1, estad1_2 = est1_2)[1]

    return dcc.send_data_frame(m1.drop('geom',axis=1).to_csv, "data.csv") 

@app.callback(
    Output("download-csv2", "data"),
    [
    Input("tabla2", "n_clicks"),
    State(component_id='selector_de_tema2', component_property= 'value'),
    State(component_id='tipo_2-1', component_property='value'),
    State(component_id='tipo_2-2', component_property='value'),
    State(component_id='agreg_2', component_property='value'),
    State(component_id='col_2', component_property='value'),
    State(component_id='color_2', component_property='value')
    ],prevent_initial_call=True,
)                                          

def download2(n, tema1, est1_1, est1_2, agreg_1, col_1, color_1 ):
    print('forth callback...')
    m1 = mapa(conn,datos = tema1, agreg1 = agreg_1,col1_1 = col_1 ,col1_2=color_1,estad1_1 = est1_1, estad1_2 = est1_2)[1]

    return dcc.send_data_frame(m1.drop('geom',axis=1).to_csv, "data.csv") 


#********************************************************************************************************# 
#███████╗██╗███████╗████████╗██╗  ██╗     ██████╗ █████╗ ██╗     ██╗     ██████╗  █████╗  ██████╗██╗  ██╗#
#██╔════╝██║██╔════╝╚══██╔══╝██║  ██║    ██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝#
#█████╗  ██║█████╗     ██║   ███████║    ██║     ███████║██║     ██║     ██████╔╝███████║██║     █████╔╝ #
#██╔══╝  ██║██╔══╝     ██║   ██╔══██║    ██║     ██╔══██║██║     ██║     ██╔══██╗██╔══██║██║     ██╔═██╗ #
#██║     ██║██║        ██║   ██║  ██║    ╚██████╗██║  ██║███████╗███████╗██████╔╝██║  ██║╚██████╗██║  ██╗#
#╚═╝     ╚═╝╚═╝        ╚═╝   ╚═╝  ╚═╝     ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝#                                                                                                       
#********************************************************************************************************#                                                           

@app.callback(
    [
    Output(component_id='modal-fs', component_property='is_open'),
    Output(component_id='map_mod', component_property='figure'),
    Output(component_id='m_title' , component_property='children')
    ] , 
    [ 
    Input(component_id='max_map1', component_property='n_clicks'), 
    Input(component_id='max_map2', component_property='n_clicks'), 
    State(component_id='selector_de_tema1', component_property= 'value'),
    State(component_id='selector_de_tema2', component_property= 'value'),
    State(component_id='tipo_1-1', component_property='value'),
    State(component_id='tipo_1-2', component_property='value'),
    State(component_id='agreg_1', component_property='value'),
    State(component_id='col_1', component_property='value'),
    State(component_id='color_1', component_property='value'),
    State(component_id='tipo_2-1', component_property='value'),
    State(component_id='tipo_2-2', component_property='value'),
    State(component_id='agreg_2', component_property='value'),
    State(component_id='col_2', component_property='value'),
    State(component_id='color_2', component_property='value')
    ], prevent_initial_call=True
    )

def mapas_max(n1,n2, tema1, tema2, est1_1, est1_2, agreg_1, col_1, color_1 ,est2_1, est2_2 , agreg_2, col_2, color_2):

    print('quinto callback')

    triggered_id = ctx.triggered_id

    if triggered_id == 'max_map1':
        m1 = mapa(conn,datos = tema1, agreg1 = agreg_1,col1_1 = col_1 ,col1_2=color_1,estad1_1 = est1_1, estad1_2 = est1_2)[0]

        m1.update_layout(width = 1000)

        return True, m1 , 'Mapa por ' + agreg_1

    elif triggered_id == 'max_map2':

        m2 = mapa(conn, datos = tema2,agreg1 = agreg_2,col1_1 = col_2 ,col1_2=color_2,estad1_1 = est2_1, estad1_2 = est2_2)[0]

        m2.update_layout(width = 1000)

        return True, m2 , 'Mapa por ' + agreg_2
    
    else:

        return 'error al generar la grafica...'

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port=8080 , debug=False)
