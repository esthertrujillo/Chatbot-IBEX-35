import matplotlib.pyplot as plt

def graficar_predicciones(y_test, y_pred, titulo="Predicción vs Real"):
    plt.figure(figsize=(10, 6))
    plt.plot(y_test.index, y_test, label='Valores reales', color='blue')
    plt.plot(y_test.index, y_pred, label='Predicciones', color='red')
    plt.title(titulo)
    plt.legend()
    plt.grid()
    plt.show()

