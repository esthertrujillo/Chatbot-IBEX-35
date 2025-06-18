# Suponiendo que ya tienes `empresa` como variable accesible
def crear_variables_lag_y_temporales(df, empresa=None):
    df['year'] = df.index.year
    df['month'] = df.index.month
    df['quarter'] = df.index.quarter
    df['day'] = df.index.day
    df['day_of_week'] = df.index.dayofweek
    df['week_of_year'] = df.index.isocalendar().week

    df['Precio_cierre_lag1'] = df['Precio_cierre'].shift(1)
    df['year_lag1'] = df['year'].shift(1)
    df['month_lag1'] = df['month'].shift(1)
    df['quarter_lag1'] = df['quarter'].shift(1)
    df['day_of_week_lag1'] = df['day_of_week'].shift(1)
    df['week_of_year_lag1'] = df['week_of_year'].shift(1)

    # Decide qué ventanas usar
    ventanas = [7, 30, 60]
    if len(df) > 1440 and empresa not in ["PUIG", "ACCIONA ENERGIA"]:
        ventanas.append(1440)

    for window in ventanas:
        df[f'rolling_mean_{window}'] = df['Precio_cierre'].shift(1).rolling(window=window).mean()
        df[f'rolling_std_{window}'] = df['Precio_cierre'].shift(1).rolling(window=window).std()

    df = df.dropna()
    return df
