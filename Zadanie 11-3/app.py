from IPython.core import interactiveshell
from IPython.core import interactiveshell
import pandas as pd
import datetime as dt
import os
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import tab1
import tab2
import tab3


base_path = os.path.dirname(os.path.abspath(__file__))
class db:
    def __init__(self):
        self.transactions = db.transation_init()
        self.cc = pd.read_csv(os.path.join(base_path, r'db\country_codes.csv'),index_col=0)
        self.customers = pd.read_csv(os.path.join(base_path, r'db\customers.csv'),index_col=0)
        self.prod_info = pd.read_csv(os.path.join(base_path, r'db\prod_cat_info.csv'))

    @staticmethod
    def transation_init():
        src = os.path.join(base_path, r'db\transactions')
        
        # Tworzymy listę na ramki danych, zamiast pustego DataFrame
        files_list = []
        for filename in os.listdir(src):
            files_list.append(pd.read_csv(os.path.join(src,filename),index_col=0))
            
        # Łączymy wszystkie pliki na raz za pomocą pd.concat
        transactions = pd.concat(files_list, ignore_index=True) if files_list else pd.DataFrame()

        def convert_dates(x):
            try:
                return dt.datetime.strptime(x,'%d-%m-%Y')
            except:
                return dt.datetime.strptime(x,'%d/%m/%Y')

        transactions['tran_date'] = transactions['tran_date'].apply(lambda x: convert_dates(x))

        return transactions

    def merge(self):
        df = self.transactions.join(self.prod_info.drop_duplicates(subset=['prod_cat_code'])
        .set_index('prod_cat_code')['prod_cat'],on='prod_cat_code',how='left')

        df = df.join(self.prod_info.drop_duplicates(subset=['prod_sub_cat_code'])
        .set_index('prod_sub_cat_code')['prod_subcat'],on='prod_subcat_code',how='left')

        df = df.join(self.customers.join(self.cc,on='country_code')
        .set_index('customer_Id'),on='cust_id')

        self.merged = df
        return self.merged

database = db()
df = database.merge()



external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

app.layout = html.Div([
    html.Div([
        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='Sprzedaż globalna', value='tab-1'),
            dcc.Tab(label='Produkty', value='tab-2'),
            dcc.Tab(label='Kanały sprzedaży', value='tab-3'),
        ]),
        html.Div(id='tabs-content')
    ], style={'width': '80%', 'margin': 'auto'})
], style={'height': '100%'})



@app.callback(Output('tabs-content', 'children'), [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return tab1.render_tab(database.merged)  # Poprawione pobieranie z bazy danych
    elif tab == 'tab-2':
        return tab2.render_tab(database.merged)
    elif tab == 'tab-3':
        return tab3.render_tab(database.merged)

# Zakładka 1 wykres
@app.callback(Output('bar-sales', 'figure'),
              [Input('sales-range', 'start_date'), Input('sales-range', 'end_date')])
def tab1_bar_sales(start_date, end_date):
    truncated = database.merged[(database.merged['tran_date'] >= start_date) & (database.merged['tran_date'] <= end_date)]
    grouped = truncated[truncated['total_amt'] > 0].groupby([pd.Grouper(key='tran_date', freq='ME'), 'Store_type'])['total_amt'].sum().round(2).unstack()

    traces = []
    for col in grouped.columns:
        traces.append(go.Bar(
            x=grouped.index, y=grouped[col], name=col, hoverinfo='text',
            hovertext=[f'{y/1e3:.2f}k' for y in grouped[col].values]
        ))

    fig = go.Figure(data=traces, layout=go.Layout(title='Przychody', barmode='stack', legend=dict(x=0, y=-0.5)))
    return fig

# Zakładka 1 mapa
@app.callback(Output('choropleth-sales', 'figure'),
              [Input('sales-range', 'start_date'), Input('sales-range', 'end_date')])
def tab1_choropleth_sales(start_date, end_date):
    truncated = database.merged[(database.merged['tran_date'] >= start_date) & (database.merged['tran_date'] <= end_date)]
    grouped = truncated[truncated['total_amt'] > 0].groupby('country')['total_amt'].sum().round(2)

    trace0 = go.Choropleth(
        colorscale='Viridis', reversescale=True,
        locations=grouped.index, locationmode='country names',
        z=grouped.values, colorbar=dict(title='Sales')
    )
    fig = go.Figure(data=[trace0], layout=go.Layout(title='Mapa', geo=dict(showframe=False, projection={'type': 'natural earth'})))
    return fig

# Zakładka 2
@app.callback(Output('barh-prod-subcat', 'figure'),
              [Input('prod_dropdown', 'value')])
def tab2_barh_prod_subcat(chosen_cat):
    if not chosen_cat:
        return go.Figure()

    grouped = database.merged[(database.merged['total_amt'] > 0) & (database.merged['prod_cat'] == chosen_cat)].pivot_table(
        index='prod_subcat', columns='Gender', values='total_amt', aggfunc='sum'
    ).assign(_sum=lambda x: x['F'] + x['M']).sort_values(by='_sum').round(2)

    traces = []
    for col in ['F', 'M']:
        if col in grouped.columns:
            traces.append(go.Bar(x=grouped[col], y=grouped.index, orientation='h', name=col))

    fig = go.Figure(data=traces, layout=go.Layout(barmode='stack', margin={'t': 20}))
    return fig

# Zakładka 3
@app.callback(
    Output('sales-day-of-week', 'figure'),
    [Input('channel_dropdown', 'value')])
    
def tab3_sales_by_day(chosen_channel):
    if not chosen_channel:
        return go.Figure()

    truncated = database.merged[(database.merged['Store_type'] == chosen_channel)&(database.merged['total_amt'] > 0)].copy()
    truncated['day_of_week'] = truncated['tran_date'].apply(lambda x: pd.to_datetime(x).day_name())
    grouped = truncated.groupby('day_of_week')['total_amt'].sum().round(2)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    grouped = grouped.reindex(days_order).dropna()
    
    trace = go.Bar(
        x=grouped.index,
        y=grouped.values,
        marker=dict(color='grey'),
        hoverinfo='y'
    )
    fig = go.Figure(data=[trace], layout=go.Layout( title=f'Sprzedaż w zależności od dnia tygodnia dla: {chosen_channel}',
        xaxis=dict(title='Dzień tygodnia'), yaxis=dict(title='Suma sprzedaży'), margin={'t': 50}))
    return fig

@app.callback(
    Output('customer-gender-pie', 'figure'),
    [Input('channel_dropdown', 'value')])

def tab3_customer_gender(chosen_channel):
    if not chosen_channel:
        return go.Figure()

    truncated = database.merged[(database.merged['Store_type'] == chosen_channel) & (database.merged['total_amt'] > 0)]
    grouped = truncated.groupby('Gender')['total_amt'].sum().round(2)

    fig = go.Figure(
        data=[go.Pie(
            labels=['Kobiety', 'Mężczyźni'], 
            values=[grouped.get('F', 0), grouped.get('M', 0)],
            hole=.3)],
        layout=go.Layout(title='Udział płci w przychodach')
    )
    return fig


@app.callback(
    Output('customer-age-bar', 'figure'),
    [Input('channel_dropdown', 'value')])

def tab3_customer_age(chosen_channel):
    if not chosen_channel:
        return go.Figure()

    truncated = database.merged[(database.merged['Store_type'] == chosen_channel) & (database.merged['total_amt'] > 0)].copy()
    if truncated.empty:
        return go.Figure()
    
    truncated['tran_year'] = pd.to_datetime(truncated['tran_date'], format='mixed').dt.year
    truncated['birth_year'] = pd.to_datetime(truncated['DOB'], format='mixed').dt.year
    truncated['Age'] = truncated['tran_year'] - truncated['birth_year']

    bins = [0, 25, 35, 45, 55, 100]
    labels = ['<25', '25-34', '35-44', '45-54', '55+']
    truncated['Age_Group'] = pd.cut(truncated['Age'], bins=bins, labels=labels)

    grouped = truncated.groupby('Age_Group', observed=False)['total_amt'].sum().round(2)

    fig = go.Figure(data=[go.Bar(x=grouped.index,y=grouped.values,marker=dict(color='indigo'))],
        layout=go.Layout( title='Przychody według grup wiekowych klientów', xaxis=dict(title='Grupa wiekowa'), yaxis=dict(title='Suma sprzedaży'))
    )
    return fig




if __name__ == '__main__':
    app.run(debug=True)
