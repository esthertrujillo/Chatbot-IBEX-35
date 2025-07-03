# prueba_series.py

from series_model import ejecutar_prediccion

def main():
    # Puedes ajustar estas rutas según la estructura de tu proyecto
    modelos_dir = "C:/Users/Esther/Documents/GitHub/Chatbot-IBEX-35/modelos_por_empresa"
    path_csv = "C:/Users/Esther/Documents/GitHub/Chatbot-IBEX-35/IBEX35_cotizaciones_20_Limpio.csv"

    # Prueba con empresa y lag concretos
    empresa = "BBVA"
    lag = 7

    resultado = ejecutar_prediccion(empresa, lag, path_csv, modelos_dir)

    # Mostrar el resultado
    print("\n📝 Resultado de la predicción:")
    print(f"Respuesta: {resultado['respuesta']}")
    print(f"RMSE: {resultado['rmse']}")
    print(f"Última predicción: {resultado['ultima_prediccion']}")

if __name__ == "__main__":
    main()
