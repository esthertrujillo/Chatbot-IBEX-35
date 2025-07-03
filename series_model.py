# series_model.py
import os
import pickle
import numpy as np
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error
from utils.series_utils.preprocessing import cargar_datos
from utils.series_utils.features import crear_variables_lag_y_temporales
from utils.series_utils.model_training import dividir_train_test
from utils.series_utils.scaling import escalar_datos
from utils.visualization import graficar_predicciones # Make sure this is the modified one

def ejecutar_prediccion(empresa, lag, path_csv, modelos_dir):
    nombre_archivo = f"{empresa.replace(' ', '_').upper()}_lag{lag}.pkl"
    modelo_path = os.path.join(modelos_dir, nombre_archivo)

    if not os.path.exists(modelo_path):
        return {
            "respuesta": f"❌ No se encuentra el modelo para {empresa} con lag {lag}.",
            "rmse": None,
            "ultima_prediccion": None,
            "grafico_base64": None # Added this
        }

    with open(modelo_path, "rb") as f:
        modelo = pickle.load(f)

    df = cargar_datos(path_csv, empresa)
    df = crear_variables_lag_y_temporales(df, empresa=empresa)

    # Note: If lag is not 1, 'Precio_cierre' is shifted, which means y_test will refer
    # to shifted future values. Ensure your model and data align for prediction.
    # For a future prediction, you'd typically predict the *next* value(s) given current data.
    # The current `dividir_train_test` splits by a fixed date, which might not be ideal
    # for a "future prediction" where you want to predict beyond the *last* known data point.
    # For a true future prediction, you'd feed the model with the latest available features.
    # For demonstration purposes, we'll just plot the existing y_test vs y_pred from the current setup.
    
    # Get the latest data point for X_test for simple prediction
    X_train, y_train, X_test, y_test = dividir_train_test(df, fecha_test="2022-04-01") # Using a fixed test split

    if isinstance(modelo, SVR):
        X_train, X_test = escalar_datos(X_train, X_test)

    y_pred = modelo.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    ultima_pred = y_pred[-1]

    # Generate the plot and get its base64 string
    plot_base64 = graficar_predicciones(y_test, y_pred, titulo=f"Predicción de {empresa} vs Real")

    return {
        "respuesta": f"La Predicción para {empresa} a {lag} días: {ultima_pred:.2f} €",
        "rmse": rmse,
        "ultima_prediccion": ultima_pred,
        "grafico_base64": plot_base64 # Include the base64 string
    }