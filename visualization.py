# visualization.py
import matplotlib.pyplot as plt
import io
import base64

def graficar_predicciones(y_test, y_pred, titulo="Predicción vs Real"):
    fig, ax = plt.subplots(figsize=(10, 6)) # Create a figure and an axes object
    
    # Check if y_test and y_pred are pandas Series/DataFrames with an index
    # Or convert them to have a simple range index for plotting if they are just arrays
    if hasattr(y_test, 'index') and y_test.index is not None:
        plot_index = y_test.index
    else:
        plot_index = range(len(y_test)) # Fallback for array-like inputs

    ax.plot(plot_index, y_test, label='Valores reales', color='blue')
    ax.plot(plot_index, y_pred, label='Predicciones', color='red')
    ax.set_title(titulo)
    ax.legend()
    ax.grid()
    
    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig) # Close the figure to free up memory
    buf.seek(0)
    
    # Encode the image to base64
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return image_base64 # Return the base64 string instead of showing