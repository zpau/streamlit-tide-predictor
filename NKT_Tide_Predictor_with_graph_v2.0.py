import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objs as go

st.title("🌊 Predicción de Marea")

# --- Sidebar ---
with st.sidebar:
    st.header("Configuración")

    uploaded_file = st.file_uploader("📂 Sube el archivo de Tidal Forecast (CSV):", type=["csv"])

    if uploaded_file is not None:
        # Nombres correctos de columnas
        column_names = [
            "datetime",
            "water_level_astro",
            "water_level_meteo",
            "surge",
            "depth_averaged_velocity",
            "current_direction"
        ]

        # Leer CSV
        df = pd.read_csv(
            uploaded_file,
            skiprows=2,
            header=None,
            names=column_names
        )

        # Convertir timestamps
        df['timestamp'] = pd.to_datetime(df['datetime'], format="%d-%b-%Y %H:%M:%S")

        # Selección por fecha y hora
        unique_dates = df['timestamp'].dt.date.unique()
        selected_date = st.selectbox("Selecciona día de predicción:", unique_dates)
        available_hours = df[df['timestamp'].dt.date == selected_date]['timestamp'].dt.time.unique()
        selected_time = st.selectbox("Selecciona hora:", available_hours)

        # Calado mínimo
        min_draft = st.number_input("Calado mínimo a mostrar (línea gris)", value=2.85, step=0.1, format="%.2f")

        # Calcular rango para slider
        start_time = df['timestamp'].min().to_pydatetime()
        end_time = df['timestamp'].max().to_pydatetime()
        default_end = min(start_time + pd.Timedelta(hours=24), end_time)

        time_range = st.slider(
            "🕓 Rango de tiempo para visualizar:",
            min_value=start_time,
            max_value=end_time,
            value=(start_time, default_end),
            format="YYYY-MM-DD HH:mm"
        )

# --- Main content ---
if uploaded_file is not None:
    selected_timestamp = datetime.combine(selected_date, selected_time)
    row = df[df['timestamp'] == selected_timestamp].iloc[0]

    # --- Tabla compacta ---
    st.subheader("Valores de predicción:")
    pred_values = {
        "Hora": selected_timestamp.strftime('%Y-%m-%d %H:%M'),
        "Tide level (astro) [m + LAT]": row['water_level_astro'],
        "Tide level (meteo) [m + LAT]": row['water_level_meteo'],
        "Surge [m]": row['surge'],
        "Velocidad media [knots]": row['depth_averaged_velocity'],
        "Dirección de corriente [°]": row['current_direction']
    }
    pred_df = pd.DataFrame.from_dict(pred_values, orient='index', columns=["Valor"])

    def format_value(x):
        if isinstance(x, (float, int)):
            return f"{x:.2f}"
        return x

    pred_df["Valor"] = pred_df["Valor"].apply(format_value)
    st.table(pred_df)

    # --- Cálculo de calados ---
    points = {
        "Barra de Arena (-1.4 m LAT)": -1.4,
        "CPT-NS-01 (-3.20 m LAT)": -3.20,
        "CPT-NS-02 (-1.76 m LAT)": -1.76
    }

    results = []
    for name, lat in points.items():
        astro = row['water_level_astro']
        meteo = row['water_level_meteo']
        surge = row['surge']
        results.append({
            "Punto": name,
            "Tide astro": str(round(astro - lat, 2)),
            "Tide astro + surge": str(round(astro + surge - lat, 2)),
            "Tide meteo": str(round(meteo - lat, 2)),
            "Tide meteo + surge": str(round(meteo + surge - lat, 2))
        })

    results_df = pd.DataFrame(results)
    st.subheader("Predicción de Calados [m LAT] (" + selected_timestamp.strftime('%Y-%m-%d %H:%M') + ")")
    st.dataframe(results_df, use_container_width=True)

    # --- Gráficos ---
    st.subheader("📊 Gráficos de la predicción de calados")

    df_range = df[(df['timestamp'] >= time_range[0]) & (df['timestamp'] <= time_range[1])]

    for point_name, lat in points.items():
        st.markdown(f"### {point_name}")

        df_point = df_range.copy()
        df_point['astro'] = df_point['water_level_astro'] - lat
        df_point['astro+surge'] = df_point['water_level_astro'] + df_point['surge'] - lat
        df_point['meteo'] = df_point['water_level_meteo'] - lat
        df_point['meteo+surge'] = df_point['water_level_meteo'] + df_point['surge'] - lat

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=df_point['timestamp'], y=df_point['astro'],
                                 mode='lines', name='Calado (astro)', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df_point['timestamp'], y=df_point['astro+surge'],
                                 mode='lines', name='Calado (astro + surge)', line=dict(color='cyan')))
        fig.add_trace(go.Scatter(x=df_point['timestamp'], y=df_point['meteo'],
                                 mode='lines', name='Calado (meteo)', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=df_point['timestamp'], y=df_point['meteo+surge'],
                                 mode='lines', name='Calado (meteo + surge)', line=dict(color='red')))

        fig.add_hline(
            y=min_draft, line_dash="dash", line_color="gray",
            annotation_text=f"Calado mínimo: {min_draft:.2f} m", annotation_position="bottom right"
        )

        fig.update_layout(
            xaxis_title='Tiempo',
            yaxis_title='Calado (m LAT)',
            legend_title="Curvas",
            hovermode='x unified',
            height=450,
            margin=dict(t=20, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Por favor, sube un archivo CSV en la barra lateral para comenzar.")
