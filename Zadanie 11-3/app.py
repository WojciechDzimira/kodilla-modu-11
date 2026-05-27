import pandas as pd
import datetime as dt
import os
import dash
from dash import html, dcc
from dash.dependencies import Input, Output

# Dynamiczne pobranie ścieżki do folderu, w którym znajduje się ten skrypt
base_path = os.path.dirname(os.path.abspath(__file__))

print("Python szuka plików w folderze:", os.path.abspath(os.path.join(base_path, r'db\transactions')))
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
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div([
        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='Sprzedaż globalna', value='tab-1'),
            dcc.Tab(label='Produkty', value='tab-2'),
            dcc.Tab(label='Produkty2', value='tab-3'),
        ]),
        html.Div(id='tabs-content')
    ], style={'width': '80%', 'margin': 'auto'})
], style={'height': '100%'})



if __name__ == '__main__':
    app.run(debug=True)