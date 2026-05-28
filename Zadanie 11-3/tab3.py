from dash import dcc, html

def render_tab(df):
    layout = html.Div([
        html.H1('Kanały sprzedaży', style={'text-align': 'center'}),
        
        html.Div([html.P("Wybierz kanał sprzedaży:"),
            dcc.Dropdown(
                id='channel_dropdown',
                options=[{'label': channel, 'value': channel} for channel in df['Store_type'].dropna().unique()],
                value=df['Store_type'].dropna().unique()[0],
                clearable=False)],
                style={'width': '50%', 'margin': 'auto', 'padding': '10px'}),
        
        html.Div([dcc.Graph(id='sales-day-of-week')], style={'margin-top': '20px'}),
        html.Div([html.Div([dcc.Graph(id='customer-gender-pie')], style={'width': '50%'}),
        html.Div([dcc.Graph(id='customer-age-bar')], style={'width': '50%'})], style={'display': 'flex', 'margin-top': '30px'})
    ])
    return layout