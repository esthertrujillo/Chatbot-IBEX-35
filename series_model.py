import os
import pickle
import numpy as np
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error
from preprocessing import cargar_datos
from features import crear_variables_lag_y_temporales
from model_training import dividir_train_test
from scaling import escalar_datos
from visualization import graficar_predicciones  # opcional

def ejecutar_prediccion(empresa, lag, path_csv, modelos_dir):
    nombre_archivo = f"{empresa.replace(' ', '_').upper()}_lag{lag}.pkl"
    modelo_path = os.path.join(modelos_dir, nombre_archivo)

    if not os.path.exists(modelo_path):
        return {
            "respuesta": f"❌ No se encuentra el modelo para {empresa} con lag {lag}.",
            "rmse": None,
            "ultima_prediccion": None
        }

    with open(modelo_path, "rb") as f:
        modelo = pickle.load(f)

    df = cargar_datos(path_csv, empresa)
    df = crear_variables_lag_y_temporales(df, empresa=empresa)

    if lag != 1:
        df["Precio_cierre"] = df["Precio_cierre"].shift(-lag)
        df.dropna(inplace=True)

    X_train, y_train, X_test, y_test = dividir_train_test(df, fecha_test="2022-04-01")

    if isinstance(modelo, SVR):
        X_train, X_test = escalar_datos(X_train, X_test)

    y_pred = modelo.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    ultima_pred = y_pred[-1]

    return {
        "respuesta": f"La Predicción para {empresa} a {lag} días: {ultima_pred:.2f} €",
        "rmse": rmse,
        "ultima_prediccion": ultima_pred
    }
