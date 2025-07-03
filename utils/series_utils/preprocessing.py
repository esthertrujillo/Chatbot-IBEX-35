import pandas as pd

def cargar_datos(path_csv, empresa):
    df = pd.read_csv(path_csv)
    df_empresa = df[df["Empresa"] == empresa].copy()
    df_empresa["Fecha"] = pd.to_datetime(df_empresa["Fecha"], errors='coerce')
    df_empresa["Precio_cierre"] = pd.to_numeric(df_empresa["Precio_cierre"], errors='coerce')
    df_empresa = df_empresa[['Fecha', 'Precio_cierre']].set_index('Fecha')
    return df_empresa

