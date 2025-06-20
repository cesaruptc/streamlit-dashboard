import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from datetime import datetime

# Configuración inicial
st.set_page_config(page_title="Dashboard de Ventas", layout="wide")
st.title("📊 Dashboard de Ventas y Clientes")

# Cargar datos
@st.cache_data
def cargar_datos():
    clientes = pd.read_csv("df_clientes.csv")
    productos = pd.read_csv("df_productos.csv")
    transacciones = pd.read_csv("df_transacciones.csv")
    transacciones['fecha'] = pd.to_datetime(transacciones['fecha'])
    df = transacciones.merge(clientes, on='cliente_id').merge(productos, on='producto_id')
    return df

df = cargar_datos()

# --- SIDEBAR - Filtros ---
st.sidebar.header("🔎 Filtros")
fecha_min = df['fecha'].min()
fecha_max = df['fecha'].max()
fecha_range = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

categorias = st.sidebar.multiselect(
    "Categorías de Producto",
    options=df['categoria'].unique(),
    default=df['categoria'].unique()
)

# Aplicar filtros
df_filtrado = df[
    (df['fecha'] >= pd.to_datetime(fecha_range[0])) &
    (df['fecha'] <= pd.to_datetime(fecha_range[1])) &
    (df['categoria'].isin(categorias))
    ]

# --- KPIs ---
st.subheader("📌 Indicadores Clave")

# KPI 1: Ventas mensuales
ventas_mensuales = df_filtrado.resample('M', on='fecha').agg({'total': 'sum'}).reset_index()
fig_ventas = px.line(ventas_mensuales, x='fecha', y='total', title='Ventas Mensuales', markers=True)
fig_ventas.update_layout(height=300)

# KPI 2: Retención de clientes
clientes_frecuencia = df_filtrado.groupby('cliente_id').size()
retencion = (clientes_frecuencia > 1).mean()

# Mostrar KPIs
col1, col2 = st.columns(2)
col1.metric("💰 Ventas Totales", f"${df_filtrado['total'].sum():,.2f}")
col2.metric("📈 Tasa de Retención", f"{retencion*100:.2f}%")

st.plotly_chart(fig_ventas, use_container_width=True)

# --- Mapa de Clientes ---
st.subheader("🗺️ Mapa Geográfico de Clientes")

# Verificamos que haya lat/lon
if 'latitud' in df_filtrado.columns and 'longitud' in df_filtrado.columns:
    m = folium.Map(location=[df_filtrado['latitud'].mean(), df_filtrado['longitud'].mean()], zoom_start=5)

    for _, row in df_filtrado.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=4,
            popup=f"Cliente: {row['cliente_id']}",
            color='blue',
            fill=True
        ).add_to(m)

    st_folium(m, width=700, height=500)
else:
    st.warning("No se encontraron columnas de latitud/longitud para mostrar el mapa.")

# --- Tabla de datos (opcional) ---
with st.expander("📄 Ver datos filtrados"):
    st.dataframe(df_filtrado)
