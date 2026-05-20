import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ----------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ----------------------------------------------------------------------

st.set_page_config(
    page_title="Cargo Dashboard",
    page_icon="✈️",
    layout="wide"
)


# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------------------

def format_weight(value):
    """
    Convierte números a formato legible:
    950 -> 950 kg
    12,500 -> 12.5 K kg
    2,500,000 -> 2.5 M kg
    """
    value = float(value)
    abs_val = abs(value)

    if abs_val >= 1_000_000:
        return f"{value / 1_000_000:.1f} M kg"
    elif abs_val >= 1_000:
        return f"{value / 1_000:.1f} K kg"
    else:
        return f"{value:,.0f} kg"


@st.cache_data
def load_data(uploaded_file):
    """
    Carga y prepara el dataset.
    Columnas requeridas:
    - AG
    - AER.
    - FECHA
    - DESTINO
    - PESO VOLUMEN
    """

    # Leer archivo
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Normalizar nombres de columnas
    df.columns = [str(col).strip().upper() for col in df.columns]

    # Validar columnas requeridas
    required = ["AG", "AER.", "FECHA", "DESTINO", "PESO VOLUMEN"]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            "Faltan las siguientes columnas:\n"
            + ", ".join(missing)
        )

    # Convertir FECHA
    df["FECHA"] = pd.to_datetime(
        df["FECHA"],
        dayfirst=True,
        errors="coerce"
    )

    # Eliminar fechas inválidas
    df = df.dropna(subset=["FECHA"])

    # Convertir peso
    df["PESO VOLUMEN"] = pd.to_numeric(
        df["PESO VOLUMEN"],
        errors="coerce"
    ).fillna(0)

    # Limpiar textos
    df["AG"] = df["AG"].astype(str).str.strip()
    df["AER."] = df["AER."].astype(str).str.strip()
    df["DESTINO"] = df["DESTINO"].astype(str).str.strip()

    # Crear columnas auxiliares
    df["MES"] = df["FECHA"].dt.to_period("M").astype(str)
    df["AÑO"] = df["FECHA"].dt.year
    df["MES_NUM"] = df["FECHA"].dt.month

    return df


# ----------------------------------------------------------------------
# TÍTULO PRINCIPAL
# ----------------------------------------------------------------------

st.title("✈️ Cargo Dashboard")
st.caption("Análisis de Peso Volumen por Aerolínea, Destino y Mes")


# ----------------------------------------------------------------------
# CARGA DE ARCHIVO
# ----------------------------------------------------------------------

uploaded_file = st.sidebar.file_uploader(
    "Cargar Dataset",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is None:
    st.info(
        "Cargue un archivo Excel o CSV con las columnas:\n"
        "AG, AER., FECHA, DESTINO y PESO VOLUMEN."
    )
    st.stop()


# ----------------------------------------------------------------------
# CARGA Y VALIDACIÓN
# ----------------------------------------------------------------------

try:
    df_original = load_data(uploaded_file)
except Exception as e:
    st.error(str(e))
    st.stop()


# ----------------------------------------------------------------------
# FILTROS EN SIDEBAR
# ----------------------------------------------------------------------

st.sidebar.header("Filtros")

# Mes
months = ["Todos"] + sorted(df_original["MES"].unique().tolist())
selected_month = st.sidebar.selectbox(
    "Mes",
    months
)

# Aerolínea
airlines = ["Todas"] + sorted(df_original["AER."].unique().tolist())
selected_airline = st.sidebar.selectbox(
    "Aerolínea",
    airlines
)

# Destino
destinations = ["Todos"] + sorted(df_original["DESTINO"].unique().tolist())
selected_destination = st.sidebar.selectbox(
    "Destino",
    destinations
)

# Agencia
agencies = ["Todas"] + sorted(df_original["AG"].unique().tolist())
selected_agency = st.sidebar.selectbox(
    "Agencia",
    agencies
)


# ----------------------------------------------------------------------
# APLICAR FILTROS
# ----------------------------------------------------------------------

df = df_original.copy()

if selected_month != "Todos":
    df = df[df["MES"] == selected_month]

if selected_airline != "Todas":
    df = df[df["AER."] == selected_airline]

if selected_destination != "Todos":
    df = df[df["DESTINO"] == selected_destination]

if selected_agency != "Todas":
    df = df[df["AG"] == selected_agency]

filter_suffix = (
    f"{selected_month}_"
    f"{selected_airline}_"
    f"{selected_destination}_"
    f"{selected_agency}"
    )

# ----------------------------------------------------------------------
# VALIDAR RESULTADOS
# ----------------------------------------------------------------------

if df.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()


# ----------------------------------------------------------------------
# INDICADORES (KPIs)
# ----------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Peso Total",
    format_weight(df["PESO VOLUMEN"].sum())
)

col2.metric(
    "Registros",
    f"{len(df):,}"
)

col3.metric(
    "Aerolíneas",
    df["AER."].nunique()
)

col4.metric(
    "Destinos",
    df["DESTINO"].nunique()
)

# ----------------------------------------------------------------------
# GRÁFICOS
# ----------------------------------------------------------------------

# ==============================================================
# 1. PESO POR AEROLÍNEA (BARRAS APILADAS POR DESTINO)
# ==============================================================

st.subheader("📦 Peso por Aerolínea (segmentado por Destino)")

pivot_airline = pd.pivot_table(
    df,
    values="PESO VOLUMEN",
    index="AER.",
    columns="DESTINO",
    aggfunc="sum",
    fill_value=0
)

if not pivot_airline.empty:
    # Seleccionar Top 15 aerolíneas
    pivot_airline["TOTAL"] = pivot_airline.sum(axis=1)
    pivot_airline = (
        pivot_airline
        .sort_values("TOTAL", ascending=False)
        .head(15)
    )
    pivot_airline = pivot_airline.drop(columns="TOTAL")

    # Mantener Top 10 destinos para no saturar el gráfico
    top_destinations = (
        pivot_airline.sum(axis=0)
        .sort_values(ascending=False)
        .head(10)
        .index
    )

    pivot_airline = pivot_airline[top_destinations]

    # Convertir a formato largo para Plotly
    plot_airline = (
        pivot_airline
        .reset_index()
        .melt(
            id_vars="AER.",
            var_name="DESTINO",
            value_name="PESO VOLUMEN"
        )
    )

    fig_airline = px.bar(
        plot_airline,
        x="AER.",
        y="PESO VOLUMEN",
        color="DESTINO",
        title="Top 15 Aerolíneas por Peso Volumen",
        labels={
            "AER.": "Aerolínea",
            "PESO VOLUMEN": "Peso Volumen (kg)"
        }
    )

    fig_airline.update_layout(
        xaxis_title="Aerolínea",
        yaxis_title="Peso Volumen (kg)",
        legend_title="Destino",
        height=600
    )

    st.plotly_chart(fig_airline, use_container_width=True)


# ==============================================================
# 2. PESO POR DESTINO
# ==============================================================

st.subheader("🌍 Peso por Destino")

destination_data = (
    df.groupby("DESTINO")["PESO VOLUMEN"]
    .sum()
    .sort_values(ascending=False)
    .head(20)
    .reset_index()
)

if not destination_data.empty:
    fig_destination = px.bar(
        destination_data,
        x="DESTINO",
        y="PESO VOLUMEN",
        title="Top 20 Destinos por Peso Volumen",
        text="PESO VOLUMEN",
        labels={
            "DESTINO": "Destino",
            "PESO VOLUMEN": "Peso Volumen (kg)"
        }
    )

    fig_destination.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    fig_destination.update_layout(
        xaxis_title="Destino",
        yaxis_title="Peso Volumen (kg)",
        height=600
    )

    st.plotly_chart(fig_destination, use_container_width=True)


# ==============================================================
# 3. PESO POR MES
# ==============================================================

st.subheader("📅 Peso por Mes")

monthly_data = (
    df_original.groupby("MES")["PESO VOLUMEN"]
    .sum()
    .reset_index()
    .sort_values("MES")
)

if not monthly_data.empty:
    fig_month = px.line(
        monthly_data,
        x="MES",
        y="PESO VOLUMEN",
        markers=True,
        title="Evolución del Peso Volumen por Mes",
        labels={
            "MES": "Mes",
            "PESO VOLUMEN": "Peso Volumen (kg)"
        }
    )

    fig_month.update_layout(
        xaxis_title="Mes",
        yaxis_title="Peso Volumen (kg)",
        height=500
    )

    st.plotly_chart(fig_month, use_container_width=True)

# ----------------------------------------------------------------------
# GRÁFICOS
# ----------------------------------------------------------------------

# ==============================================================
# 1. PESO POR AEROLÍNEA (BARRAS APILADAS POR DESTINO)
# ==============================================================

st.subheader("📦 Peso por Aerolínea (segmentado por Destino)")

pivot_airline = pd.pivot_table(
    df,
    values="PESO VOLUMEN",
    index="AER.",
    columns="DESTINO",
    aggfunc="sum",
    fill_value=0
)

if not pivot_airline.empty:
    # Seleccionar Top 15 aerolíneas
    pivot_airline["TOTAL"] = pivot_airline.sum(axis=1)
    pivot_airline = (
        pivot_airline
        .sort_values("TOTAL", ascending=False)
        .head(15)
    )
    pivot_airline = pivot_airline.drop(columns="TOTAL")

    # Mantener Top 10 destinos para no saturar el gráfico
    top_destinations = (
        pivot_airline.sum(axis=0)
        .sort_values(ascending=False)
        .head(10)
        .index
    )

    pivot_airline = pivot_airline[top_destinations]

    # Convertir a formato largo para Plotly
    plot_airline = (
        pivot_airline
        .reset_index()
        .melt(
            id_vars="AER.",
            var_name="DESTINO",
            value_name="PESO VOLUMEN"
        )
    )

    fig_airline = px.bar(
        plot_airline,
        x="AER.",
        y="PESO VOLUMEN",
        color="DESTINO",
        title="Top 15 Aerolíneas por Peso Volumen",
        labels={
            "AER.": "Aerolínea",
            "PESO VOLUMEN": "Peso Volumen (kg)"
        }
    )

    fig_airline.update_layout(
        xaxis_title="Aerolínea",
        yaxis_title="Peso Volumen (kg)",
        legend_title="Destino",
        height=600
    )

    st.plotly_chart(fig_airline, use_container_width=True)


# ==============================================================
# 2. PESO POR DESTINO
# ==============================================================

st.subheader("🌍 Peso por Destino")

destination_data = (
    df.groupby("DESTINO")["PESO VOLUMEN"]
    .sum()
    .sort_values(ascending=False)
    .head(20)
    .reset_index()
)

if not destination_data.empty:
    fig_destination = px.bar(
        destination_data,
        x="DESTINO",
        y="PESO VOLUMEN",
        title="Top 20 Destinos por Peso Volumen",
        text="PESO VOLUMEN",
        labels={
            "DESTINO": "Destino",
            "PESO VOLUMEN": "Peso Volumen (kg)"
        }
    )

    fig_destination.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    fig_destination.update_layout(
        xaxis_title="Destino",
        yaxis_title="Peso Volumen (kg)",
        height=600
    )

    st.plotly_chart(fig_destination, use_container_width=True)


# ==============================================================
# 3. PESO POR MES
# ==============================================================

st.subheader("📅 Peso por Mes")

monthly_data = (
    df_original.groupby("MES")["PESO VOLUMEN"]
    .sum()
    .reset_index()
    .sort_values("MES")
)

if not monthly_data.empty:
    fig_month = px.line(
        monthly_data,
        x="MES",
        y="PESO VOLUMEN",
        markers=True,
        title="Evolución del Peso Volumen por Mes",
        labels={
            "MES": "Mes",
            "PESO VOLUMEN": "Peso Volumen (kg)"
        }
    )

    fig_month.update_layout(
        xaxis_title="Mes",
        yaxis_title="Peso Volumen (kg)",
        height=500
    )

    st.plotly_chart(fig_month, use_container_width=True)

# ==============================================================
# 4. HEATMAP: MES × AEROLÍNEA
# ==============================================================

st.subheader("🔥 Heatmap Mes × Aerolínea")

pivot_heat_airline = pd.pivot_table(
    df_original,
    values="PESO VOLUMEN",
    index="AER.",
    columns="MES",
    aggfunc="sum",
    fill_value=0
)

if not pivot_heat_airline.empty:
    # Seleccionar Top 15 aerolíneas por volumen total
    pivot_heat_airline["TOTAL"] = pivot_heat_airline.sum(axis=1)
    pivot_heat_airline = (
        pivot_heat_airline
        .sort_values("TOTAL", ascending=False)
        .head(15)
    )
    pivot_heat_airline = pivot_heat_airline.drop(columns="TOTAL")

    fig_heat_airline = px.imshow(
        pivot_heat_airline,
        aspect="auto",
        labels=dict(
            x="Mes",
            y="Aerolínea",
            color="Peso Volumen (kg)"
        ),
        title="Heatmap Mes × Aerolínea"
    )

    fig_heat_airline.update_layout(height=700)

    st.plotly_chart(fig_heat_airline, use_container_width=True)


# ==============================================================
# 5. HEATMAP: MES × DESTINO
# ==============================================================

st.subheader("🌐 Heatmap Mes × Destino")

pivot_heat_destination = pd.pivot_table(
    df_original,
    values="PESO VOLUMEN",
    index="DESTINO",
    columns="MES",
    aggfunc="sum",
    fill_value=0
)

if not pivot_heat_destination.empty:
    # Seleccionar Top 20 destinos por volumen total
    pivot_heat_destination["TOTAL"] = pivot_heat_destination.sum(axis=1)
    pivot_heat_destination = (
        pivot_heat_destination
        .sort_values("TOTAL", ascending=False)
        .head(20)
    )
    pivot_heat_destination = pivot_heat_destination.drop(columns="TOTAL")

    fig_heat_destination = px.imshow(
        pivot_heat_destination,
        aspect="auto",
        labels=dict(
            x="Mes",
            y="Destino",
            color="Peso Volumen (kg)"
        ),
        title="Heatmap Mes × Destino"
    )

    fig_heat_destination.update_layout(height=800)

    st.plotly_chart(fig_heat_destination, use_container_width=True)


# ==============================================================
# 6. TABLA DE DATOS FILTRADOS
# ==============================================================

st.subheader("📋 Datos Filtrados")

st.dataframe(
    df.sort_values("FECHA", ascending=False),
    use_container_width=True,
    height=500
)


# ==============================================================
# 7. DESCARGA DE DATOS FILTRADOS
# ==============================================================

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Descargar datos filtrados (CSV)",
    data=csv_data,
    file_name="cargo_dashboard_filtered.csv",
    mime="text/csv"
)


# ==============================================================
# 8. INFORMACIÓN ADICIONAL
# ==============================================================

with st.expander("ℹ️ Información del Dataset"):
    st.write(f"**Fecha mínima:** {df_original['FECHA'].min().date()}")
    st.write(f"**Fecha máxima:** {df_original['FECHA'].max().date()}")
    st.write(f"**Peso total histórico:** {format_weight(df_original['PESO VOLUMEN'].sum())}")
    st.write(f"**Total de agencias:** {df_original['AG'].nunique()}")
    st.write(f"**Total de aerolíneas:** {df_original['AER.'].nunique()}")
    st.write(f"**Total de destinos:** {df_original['DESTINO'].nunique()}")
    st.write(f"**Total de meses:** {df_original['MES'].nunique()}")
