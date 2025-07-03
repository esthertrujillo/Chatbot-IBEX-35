import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
import xgboost as xgb
from sklearn.metrics import mean_squared_error

def dividir_train_test(df, fecha_test):
    
    #fecha_test = pd.to_datetime(fecha_test)
    train = df[df.index < fecha_test]
    test = df[df.index >= fecha_test]
    return train.drop(columns=['Precio_cierre']), train['Precio_cierre'], test.drop(columns=['Precio_cierre']), test['Precio_cierre']

def definir_modelos():
    models = {
        'Linear Regression': LinearRegression(),
        'Decision Tree': DecisionTreeRegressor(),
        'Random Forest': RandomForestRegressor(),
        'Gradient Boosting': GradientBoostingRegressor(),
        'XGBoost': xgb.XGBRegressor(),
        'SVR': SVR()
    }

    param_grids = {
        'Linear Regression': {},
        'Decision Tree': {
            'max_depth': [5, 10, 20],
            'min_samples_split': [2, 5, 10]
        },
        'Random Forest': {
            'n_estimators': [100, 200],
            'max_depth': [5, 10, 20],
            'min_samples_split': [2, 5, 10]
        },
        'Gradient Boosting': {
            'n_estimators': [100, 200],
            'learning_rate': [0.01, 0.05, 0.1],
            'max_depth': [3, 5, 7]
        },
        'XGBoost': {
            'n_estimators': [100, 200],
            'learning_rate': [0.01, 0.05, 0.1],
            'max_depth': [3, 5, 7]
        },
        'SVR': {
            'C': [0.1, 1, 10],
            'kernel': ['linear', 'rbf'],
            'gamma': ['scale', 'auto']
        }
    }

    return models, param_grids

def entrenar_y_evaluar_modelos(X_train, y_train, X_test, y_test, models, param_grids):
    best_model = None
    best_rmse = float('inf')
    best_model_name = ""

    for model_name, model in models.items():
        print(f"Entrenando {model_name}...")
        grid_search = GridSearchCV(model, param_grids[model_name], scoring='neg_root_mean_squared_error', cv=3, verbose=0)
        grid_search.fit(X_train, y_train)
        y_pred = grid_search.best_estimator_.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        print(f"{model_name} - RMSE: {rmse}")
        if rmse < best_rmse:
            best_rmse = rmse
            best_model = grid_search.best_estimator_
            best_model_name = model_name

    return best_model_name, best_model, best_rmse
