import streamlit as st
import pandas as pd
import plotly.express as px
import folium   # Renderizado del mapa
from streamlit_folium import st_folium
from datetime import datetime
from folium.plugins import MarkerCluster
from string import capwords

# Configuración de la página
st.set_page_config(
    page_title = "Sales Analytics Dashboard",
    layout="wide",
    initial_sidebar_state = "expanded"
)

def obtener_color(ventas):
    if ventas > 1000000:  # Más de 1M
        return '#ff0000'  # Rojo
    elif ventas > 500000:  # 500K-1M
        return '#ff6600'  # Naranja
    elif ventas > 100000:  # 100K-500K
        return '#ffcc00'  # Amarillo
    else:                  # Menos de 100K
        return '#33cc33'  # Verde

# Función para la carga de datos
def load_data():
    """
    Cargar y combinar los conjuntos de datos referentes a
    1. Transacciones de ventas
    2. Catálogo de productos
    3. Información de clientes
    Retorna una tupla con los datos
    """
    transacciones = pd.read_csv('df_transacciones.csv', parse_dates=['fecha'],dtype={'producto_id':'string', 'cliente_id':'string'})
    productos = pd.read_csv('df_productos.csv', dtype={'cliente_id': 'string'})
    clientes = pd.read_csv('df_clientes.csv', dtype={'cliente_id': 'string'})

    datos_comb = pd.merge(transacciones, productos, on = 'producto_id', how='left')
    datos_comb = pd.merge(datos_comb, clientes, on='cliente_id', how='left')

    return datos_comb, clientes

# Carga inicial de datos
df, df_clientes = load_data()

df['categoria'] = df['categoria'].str.strip().str.lower().apply(capwords)
df['segmento'] = df['segmento'].str.strip().str.lower().apply(capwords)
df['metodo_pago'] = df['metodo_pago'].str.strip().str.lower().apply(capwords)

# Barra lateral con los filtros interactivos
with st.sidebar:
    st.header("Filtros")

    # Selector de rango de fechas
    fecha_min = df['fecha'].min().date()
    fecha_max = df['fecha'].max().date()

    fechas_seleccionadas = st.date_input(
        label = "Rango de fechas",
        value = (fecha_min, fecha_max),
        min_value = fecha_min,
        max_value = fecha_max,
        help = "Selecciona el período a analizar"
    )

    # Selector de categorías
    categorias_disponibles = sorted(df['categoria'].unique())

    categorias_seleccionadas = st.multiselect(
        label = "Categorías de productos",
        options = categorias_disponibles,
        default = categorias_disponibles,
        help = "Filtra por categorías de productos"
    )

    # Filtro por segmento de clientes
    segmentos = sorted(df['segmento'].unique())

    segmentos_seleccionados = st.multiselect(
        label = "Segmentos de clientes",
        options = segmentos,
        default = segmentos,
        help = "Filtra por segmentos de clientes"
    )

    # Filtro por métodos de pago
    metodos_disponibles = sorted(df['metodo_pago'].dropna().unique())

    metodo_pago_seleccionado = st.multiselect(
        label = "Método de Pago",
        options = metodos_disponibles,
        default = metodos_disponibles,
        help = "Filtra por método de pago utilizado en las transacciones"
    )

# Aplicación de filtros
condicion_filtro = (
    (df['fecha'].dt.date >= fechas_seleccionadas[0]) &
    (df['fecha'].dt.date <= fechas_seleccionadas[1]) &
    (df['categoria'].isin(categorias_seleccionadas)) &
    (df['segmento'].isin(segmentos_seleccionados)) &
    (df['metodo_pago'].isin(metodo_pago_seleccionado))
)

# Aplicar filtros
df_filtrado = df[condicion_filtro].copy()

# Sección principal del dasboard, primero los kpis
st.title("Dashboard de Ventas")
st.markdown("""
    Visualización interactiva de métricas de ventas y distribución de clientes.
    Utiliza los filtros en la barra lateral para personalizar la vista.
""")

# KPIS Principales
st.header("Métricas clave")

# Cálculo de métricas
ventas_totales = df_filtrado['total'].sum()                   # Sumar las ventas totales
ventas_mensuales = df_filtrado.groupby(                       # Suma de las ventas totales pero ahora por mes
    pd.Grouper(key='fecha', freq='ME')
)['total'].sum().mean()
clientes_unicos = df_filtrado['cliente_id'].nunique()         # ID's de clientes únicos

# La tasa de retención indica qué porcentaje de clientes realizaron más de una compra en el período seleccionado.
compras_por_cliente = df_filtrado['cliente_id'].value_counts()
tasa_retencion = (compras_por_cliente > 1).mean() * 100

# Mostrar métricas
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        label = "Ventas totales",
        value = f"${ventas_totales:,.2f}",
        help = "Suma total de ventas en el período seleccionado"
    )

with col2:
    st.metric(
        label="Ventas Mensuales Promedio",
        value=f"${ventas_mensuales:,.2f}",
        help="Promedio de ventas por mes"
    )

with col3:
    st.metric(
        label="Clientes Únicos",
        value=f"{clientes_unicos:,}",
        help="Número de clientes distintos con compras"
    )

with col4:
    st.metric(
        label="Tasa de Retención",
        value=f"{tasa_retencion:.1f}%",
        help="Porcentaje de clientes con más de una compra"
    )

# Gráficos de tendencias
st.header("Tendencia mensual de ventas")

# Agrupar los datos por fecha con una frecuencia de mes, calculado el total (sum) y la cantidad de transacciones
datos_mensuales = df_filtrado.groupby(
    pd.Grouper(key='fecha', freq='ME')
).agg({
    'total':'sum',
    'transaccion_id':'count'
}).rename(columns={
    'transaccion_id':'numero_transacciones'
}).reset_index()

fig = px.area(
    datos_mensuales,
    x='fecha',
    y='total',
    title='Evolución mensual de ventas',
    labels={
        'fecha': 'Mes',
        'total': 'Ventas ($)'
    },
)

# Modificar el popup para que los datos sean entendibles
fig.update_traces(
    hovertemplate=
    '<b>Mes:</b> %{x|%B %Y}<br>' +
    '<b>Ventas:</b> $%{y:,.2f}<br>' +
    '<b>Número de transacciones:</b> %{customdata[0]:,}<extra></extra>',
    customdata=datos_mensuales[['numero_transacciones']].to_numpy(),
    line=dict(width=2.5),
    marker=dict(size=8),
    fill='tozeroy',
    fillcolor='rgba(100, 200, 150, 0.2)'
)

fig.update_layout(
    xaxis_title="Mes",
    yaxis_title="Ventas ($)",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width = True)

# Parte gráfica del mapa

# Hacer una copia del df de clientes y filtrarlo según lo que se vaya seleccionando
df_clientes_geo = df_clientes.copy()
df_clientes_filtrado = df_clientes[
    df_clientes['cliente_id'].isin(df_filtrado['cliente_id'].unique())
].copy()

# Calcular las ventas por ciudad o ubicación, teniendo el total (sum) y la cantidad de transacciones ( datos para el popup)
ventas_por_ubicacion = df_filtrado.groupby('cliente_id').agg({
    'total': 'sum',
    'transaccion_id': 'count'
}).rename(columns={
    'total': 'ventas_totales',
    'transaccion_id': 'num_transacciones'
}).reset_index()

# Unir el df de clientes con las ventas por ubicación
df_clientes_geo = pd.merge(
    df_clientes_filtrado,
    ventas_por_ubicacion,
    on='cliente_id',
    how='left'
)

# Agrupar por coordenadas únicas que se encuentran en el dataframe de clientes, con las métricas calculadas.
coordenadas_unicas = df_clientes_geo.groupby(['latitud', 'longitud', 'ciudad']).agg({
    'cliente_id': 'count',
    'ventas_totales': 'sum',
    'num_transacciones': 'sum',
    'segmento': lambda x: x.mode()[0] if not x.mode().empty else 'N/A'
}).reset_index().rename(columns={
    'cliente_id': 'conteo_clientes',
    'segmento': 'segmento_principal'
})

# Resumen estadístico de cantidad de ciudades, acá siempre van a ser 6 si no se meten más
st.subheader("Resumen por Ubicación")
st.metric("Ubicaciones únicas", len(coordenadas_unicas))
# Crear el mapa interactivo con las métricas que se deben tener
m = folium.Map(
    location=[coordenadas_unicas['latitud'].mean(), coordenadas_unicas['longitud'].mean()],
    zoom_start=6,
    tiles='cartodbpositron'
)

marker_cluster = MarkerCluster().add_to(m)

for _, row in coordenadas_unicas.iterrows():
    # Métricas adicionales
    avg_venta = row['ventas_totales'] / row['num_transacciones'] if row['num_transacciones'] > 0 else 0    # Cálculo promedio de ventas

    folium.CircleMarker(
        location=[row['latitud'], row['longitud']],
        radius=5 + (row['conteo_clientes']/500),  # Tamaño del círculo
        color='#3388ff',
        fill=True,
        fill_color=obtener_color(row['ventas_totales']),
        popup=f"""
            <b>Ciudad:</b> {row['ciudad']}<br>
            <b>Clientes:</b> {row['conteo_clientes']}<br>
            <b>Ventas totales:</b> ${row['ventas_totales']:,.2f}<br>
            <b>Transacciones:</b> {row['num_transacciones']}<br>
            <b>Ticket promedio:</b> ${avg_venta:,.2f}<br>
            <b>Segmento principal:</b> {row['segmento_principal']}
        """,
        tooltip=f"{row['ciudad']} - {row['conteo_clientes']} clientes"
    ).add_to(marker_cluster)

st_folium(m, use_container_width = True, height=500)

# Otros gráficos para análisis
st.header("Análisis de ventas")

col_izq, col_der = st.columns(2)

with col_izq:
    # Gráfico de pastel de ventas por categoría
    ventas_por_categoria = df_filtrado.groupby('categoria')['total'].sum().reset_index()

    fig_torta = px.pie(
        ventas_por_categoria,
        names='categoria',
        values='total',
        title='Distribución de Ventas por Categoría',
        hole=0.3,
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig_torta.update_traces(
        hovertemplate='<b>Categoría:</b> %{label}<br><b>Total:</b> $%{value:,.2f}<extra></extra>'
    )

    st.plotly_chart(fig_torta, use_container_width=True)

with col_der:
    # Gráfico de pastel de ventas por método de pago
    ventas_pago = df_filtrado.groupby('metodo_pago')['total'].sum().reset_index()

    fig_pago = px.pie(
        ventas_pago,
        names='metodo_pago',
        values='total',
        title='Distribución por Método de Pago',
        hole=0.3,
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig_pago.update_traces(
        hovertemplate='<b>Metodo de pago:</b> %{x}<br><b>Total:</b> $%{y:,.2f}<extra></extra>'
    )

    st.plotly_chart(fig_pago, use_container_width=True)

col_extra = st.container()

with col_extra:
    col1, col2 = st.columns(2)
    with col1:
        # Gráfico de barras por segmento de cliente
        ventas_por_segmento = df_filtrado.groupby('segmento')['total'].sum().reset_index()

        fig_segmento = px.bar(
            ventas_por_segmento.sort_values('total', ascending=False),
            x='segmento',
            y='total',
            title='Ventas por Segmento de Cliente',
            labels={'segmento': 'Segmento', 'total': 'Total'},
            color='segmento',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )

        fig_segmento.update_traces(
            hovertemplate='<b>Segmento:</b> %{x}<br><b>Total:</b> $%{y:,.2f}<extra></extra>'
        )

        fig_segmento.update_layout(showlegend=False)
        st.plotly_chart(fig_segmento, use_container_width=True)

    with col2:
        # Top 10 de los productos más vendidos
        top_productos = df_filtrado.groupby('nombre_x')['cantidad'].sum().nlargest(10).reset_index() # Se agrupa por producto y se obtienen los 10 primeros
        top_productos = top_productos.rename(columns={'nombre_x': 'Producto'})

        fig_top_prod = px.bar(
            top_productos,
            x='Producto',
            y='cantidad',
            title='Top 10 Productos Más Vendidos',
            labels={'nombre': 'Producto', 'cantidad': 'Cantidad Vendida'},
            color='Producto',
            color_discrete_sequence=px.colors.qualitative.Set2
        )

        fig_top_prod.update_traces(
            hovertemplate='<b>Producto:</b> %{x}<br><b>Cantidad:</b> $%{y:,.2f}<extra></extra>'
        )

        fig_top_prod.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_top_prod, use_container_width=True)

col_extra2 = st.container()

with col_extra2:
    # Gráfico de relación entre precio y cantidad de productos vendida
    col1, col2 = st.columns(2)
    with col1:
        df_precios = df_filtrado.copy()
        df_precios['precio'] = df_precios['total'] / df_precios['cantidad']
        df_precios = df_precios.rename(columns={'nombre_x': 'Producto'})

        fig_precio_cantidad = px.scatter(
            df_precios,
            x='precio',
            y='cantidad',
            color='categoria',
            hover_data=['Producto'],
            labels={
                'precio': 'Precio Unitario ($)',
                'cantidad': 'Cantidad Vendida',
                'categoria': 'Categoría'
            },
            title='Relación entre Precio Unitario y Cantidad Vendida',
            color_discrete_sequence=px.colors.qualitative.Vivid
        )

        fig_precio_cantidad.update_traces(marker=dict(size=8, opacity=0.6))
        st.plotly_chart(fig_precio_cantidad, use_container_width=True)

    with col2:
        # Gráfico de stock por categoría, este valor no varía
        stock_categoria = df_filtrado.groupby('categoria')['stock'].mean().reset_index()

        fig_stock = px.bar(
            stock_categoria.sort_values('stock', ascending=False),
            x='categoria',
            y='stock',
            title='Stock Promedio por Categoría',
            labels={'categoria': 'Categoría', 'stock': 'Stock Promedio'},
            color='categoria',
            color_discrete_sequence=px.colors.qualitative.Set3
        )

        fig_stock.update_traces(
            hovertemplate='<b>Categoría:</b> %{x}<br><b>Stock Promedio:</b> %{y:.0f}<extra></extra>'
        )

        fig_stock.update_layout(showlegend=False)
        st.plotly_chart(fig_stock, use_container_width=True)

st.header("Explorador de Datos")

# Datos filtrados para el buscador y si se desea descargar
columnas_a_mostrar = [
    'fecha',           # Fecha
    'nombre_y',        # Nombre
    'apellido',        # Apellido
    'email',           # Email
    'ciudad',          # Ciudad
    'segmento',        # Segmento
    'nombre_x',        # Producto
    'categoria',       # Categoría
    'cantidad',        # Cantidad
    'total',           # Monto
    'metodo_pago'      # Método de pago
]

df_vis = df_filtrado[columnas_a_mostrar].sort_values('fecha', ascending=False).copy()

st.dataframe(
    df_vis,
    column_config={
        "fecha": "Fecha",
        "nombre_y": "Nombre",
        "apellido": "Apellido",
        "email": "Email",
        "ciudad": "Ciudad",
        "segmento": "Segmento",
        "nombre_x": "Producto",
        "categoria": "Categoría",
        "cantidad": st.column_config.NumberColumn("Cantidad", format="%d"),
        "total": st.column_config.NumberColumn("Monto", format="$%.2f"),
        "metodo_pago": "Método de Pago"
    },
    hide_index=True,
    use_container_width=True,
    height=400
)