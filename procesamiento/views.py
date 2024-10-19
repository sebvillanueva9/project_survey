from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse # type: ignore
from django.contrib import messages

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Usar el backend "Agg" para evitar abrir ventanas GUI
import matplotlib.pyplot as plt
import seaborn as sns

import os
import tempfile
import io
import base64
import zipfile

import openpyxl
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.drawing.image import Image

# Recategorizar las respuestas del tipo Likert
def recategorize_likert(df):
    likert_map = {
        'Totalmente De Acuerdo': 'Aliados',
        'En Acuerdo': 'Aliados',
        'Indeciso': 'Indecisos',
        'En Desacuerdo': 'Detractores',
        'Totalmente en Desacuerdo': 'Detractores'
    }
    for column in df.columns[1:]:  # Asumiendo que la primera columna es Regional/Agencia
        df[column] = df[column].map(likert_map)
    return df

# Generar gráficos y procesar los datos
def generate_results_and_charts(df):
    # Recategorizar los datos
    df = recategorize_likert(df)

    # Generar los resúmenes de los datos
    summary_data = df.iloc[:, 1:].apply(pd.Series.value_counts).transpose().fillna(0)

    # Gráfico de torta para la distribución general
    overall_counts = summary_data.sum()
    fig, ax = plt.subplots()
    ax.pie(overall_counts, labels=overall_counts.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette("pastel"))
    ax.set_title("Distribución General de Aliados, Indecisos, y Detractores")
    plt.tight_layout()

    # Guardar el gráfico de torta en un buffer
    pie_buffer = io.BytesIO()
    plt.savefig(pie_buffer, format='png')
    pie_buffer.seek(0)
    plt.close()

    # Gráfico de barras para la distribución por regional y agencia
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=summary_data, palette="Blues_d", ax=ax)
    ax.set_title("Distribución de Aliados, Indecisos, y Detractores por Regional/Agencia")
    ax.set_xlabel("Regional/Agencia")
    ax.set_ylabel("Frecuencia")
    plt.xticks(rotation=45, ha='right')

    # Guardar el gráfico de barras en un buffer
    bar_buffer = io.BytesIO()
    plt.savefig(bar_buffer, format='png')
    bar_buffer.seek(0)
    plt.close()

    return summary_data, pie_buffer, bar_buffer

# Vista principal para manejar la subida y procesamiento de archivos
def home(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        # Validar el tipo de archivo
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'El archivo no es un documento Excel válido.')
            return render(request, 'procesamiento/home.html')

        # Guardar el archivo subido
        fs = FileSystemStorage()
        filename = fs.save(excel_file.name, excel_file)
        file_path = fs.path(filename)

        try:
            # Leer el archivo Excel subido
            df = pd.read_excel(file_path)

            # Generar los resultados y gráficos
            summary_data, pie_buffer, bar_buffer = generate_results_and_charts(df)

            # Crear un archivo Excel con las tablas de resultados
            excel_output_path = os.path.join(tempfile.gettempdir(), 'results.xlsx')
            wb = Workbook()
            ws1 = wb.active
            ws1.title = "Processed Data"

            # Añadir los datos procesados al archivo Excel
            for r in dataframe_to_rows(summary_data.reset_index(), index=False, header=True):
                ws1.append(r)

            # Guardar el archivo Excel
            wb.save(excel_output_path)

            # Crear un archivo ZIP que contenga el archivo Excel y los gráficos
            zip_output_path = os.path.join(tempfile.gettempdir(), 'results_with_charts.zip')
            with zipfile.ZipFile(zip_output_path, 'w') as zipf:
                # Añadir el archivo Excel al ZIP
                zipf.write(excel_output_path, 'results.xlsx')

                # Añadir el gráfico de torta al ZIP
                with open(os.path.join(tempfile.gettempdir(), 'pie_chart.png'), 'wb') as f:
                    f.write(pie_buffer.getvalue())
                    zipf.write(f.name, 'pie_chart.png')

                # Añadir el gráfico de barras al ZIP
                with open(os.path.join(tempfile.gettempdir(), 'bar_chart.png'), 'wb') as f:
                    f.write(bar_buffer.getvalue())
                    zipf.write(f.name, 'bar_chart.png')

            # Descargar el archivo ZIP
            with open(zip_output_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=results_with_charts.zip'
                return response

        except Exception as e:
            messages.error(request, f'Ocurrió un error al procesar el archivo: {e}')
            return render(request, 'procesamiento/home.html')

    return render(request, 'procesamiento/home.html')