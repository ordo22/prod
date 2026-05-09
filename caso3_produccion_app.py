
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ─── Configuración de página ──────────────────────────────────
st.set_page_config(
    page_title="MetalParts — Dashboard de Producción",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Carga de datos (cacheada) ─────────────────────────────────
@st.cache_data
def cargar_datos(ruta="caso3_produccion_dataset.csv"):
    df = pd.read_csv(ruta)
    df["fecha_produccion"] = pd.to_datetime(df["fecha_produccion"])
    return df

df = cargar_datos()

# ─── Sidebar: filtros ─────────────────────────────────────────
st.sidebar.title("🎛️ Filtros")

lineas = st.sidebar.multiselect(
    "Línea de producción",
    options=sorted(df["linea_produccion"].unique()),
    default=sorted(df["linea_produccion"].unique()),
)

turnos = st.sidebar.multiselect(
    "Turno",
    options=df["turno"].unique().tolist(),
    default=df["turno"].unique().tolist(),
)

maquinas = st.sidebar.multiselect(
    "Máquina",
    options=sorted(df["maquina"].unique()),
    default=sorted(df["maquina"].unique()),
)

# Bonus: rango de fechas
fecha_min, fecha_max = df["fecha_produccion"].min(), df["fecha_produccion"].max()
rango_fechas = st.sidebar.date_input(
    "Rango de fechas",
    value=(fecha_min, fecha_max),
    min_value=fecha_min, max_value=fecha_max,
)

# Aplicar filtros
df_f = df[
    df["linea_produccion"].isin(lineas)
    & df["turno"].isin(turnos)
    & df["maquina"].isin(maquinas)
]
if len(rango_fechas) == 2:
    df_f = df_f[
        (df_f["fecha_produccion"] >= pd.to_datetime(rango_fechas[0]))
        & (df_f["fecha_produccion"] <= pd.to_datetime(rango_fechas[1]))
    ]

st.sidebar.markdown("---")
st.sidebar.metric("Órdenes filtradas", f"{len(df_f):,}")
st.sidebar.download_button(
    "⬇️ Descargar datos filtrados (CSV)",
    data=df_f.to_csv(index=False).encode("utf-8"),
    file_name="produccion_filtrada.csv",
    mime="text/csv",
)

# ─── Encabezado ───────────────────────────────────────────────
st.title("🏭 MetalParts Colombia — Dashboard de Producción")
st.caption("Zona Industrial de Itagüí · Datos 2024")

if df_f.empty:
    st.warning("No hay datos con los filtros seleccionados.")
    st.stop()

# ─── KPIs (patrón Z) ───────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📊 Eficiencia prom.", f"{df_f['eficiencia_pct'].mean():.1f}%")
k2.metric("⚠️ Defectos prom.",  f"{df_f['tasa_defectos_pct'].mean():.2f}%")
k3.metric("📦 Unidades prod.",  f"{df_f['unidades_producidas'].sum():,}")
k4.metric("💰 Costo total",     f"${df_f['costo_produccion_cop'].sum()/1e6:,.1f}M")
k5.metric("⏱️ Paro total",      f"{df_f['tiempo_paro_min'].sum():,.0f} min")

st.markdown("---")

# ─── Tabs con las gráficas ────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Operación", "🛑 Calidad y Paros", "🚨 Alertas"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.box(
            df_f, x="linea_produccion", y="eficiencia_pct",
            color="linea_produccion", points="all",
            title="Eficiencia (%) por Línea",
            labels={"linea_produccion": "Línea", "eficiencia_pct": "Eficiencia (%)"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        prod_sem = df_f.groupby("semana")["unidades_producidas"].sum().reset_index()
        fig = px.line(
            prod_sem, x="semana", y="unidades_producidas", markers=True,
            title="Producción semanal",
            labels={"semana": "Semana", "unidades_producidas": "Unidades"},
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        defectos = df_f.groupby(["turno", "linea_produccion"])["tasa_defectos_pct"].mean().reset_index()
        fig = px.bar(
            defectos, x="turno", y="tasa_defectos_pct", color="linea_produccion",
            barmode="group", text_auto=".2f",
            title="Tasa de defectos por Turno y Línea",
            labels={"turno": "Turno", "tasa_defectos_pct": "Defectos (%)",
                    "linea_produccion": "Línea"},
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        paro = df_f.groupby("maquina")["tiempo_paro_min"].sum().sort_values().reset_index()
        fig = px.bar(
            paro, x="tiempo_paro_min", y="maquina", orientation="h",
            color="tiempo_paro_min", color_continuous_scale="Reds",
            title="Paro total por Máquina (min)",
            labels={"maquina": "Máquina", "tiempo_paro_min": "Paro (min)"},
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Temperatura vs Defectos")
    fig = px.scatter(
        df_f, x="temperatura_c", y="tasa_defectos_pct",
        color="linea_produccion", size="unidades_producidas",
        trendline="ols", trendline_scope="overall",
        hover_data=["maquina", "producto"],
        labels={"temperatura_c": "Temperatura (°C)",
                "tasa_defectos_pct": "Defectos (%)",
                "linea_produccion": "Línea"},
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("🚨 Órdenes con tasa de defectos > 10%")
    alertas = df_f[df_f["tasa_defectos_pct"] > 10].sort_values(
        "tasa_defectos_pct", ascending=False
    )
    if alertas.empty:
        st.success("✅ Ninguna orden supera el 10% de defectos en el filtro actual.")
    else:
        st.warning(f"Se encontraron {len(alertas)} órdenes que requieren revisión.")
        st.dataframe(
            alertas[[
                "id_orden", "fecha_produccion", "linea_produccion", "turno",
                "maquina", "producto", "unidades_producidas",
                "unidades_defectuosas", "tasa_defectos_pct", "causa_paro",
            ]],
            use_container_width=True, hide_index=True,
        )

st.markdown("---")
st.caption("Dashboard construido con Streamlit + Plotly · Caso 3 — Producción Industrial")
