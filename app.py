import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# =============================
# CONFIGURACIÓN GENERAL
# =============================
st.set_page_config(layout="wide")

TITULO = "🎟️ RIFA – Selección de Números"
PRECIO_TICKET = 10
ADMIN_PASSWORD = "admin123"

RANGOS = [
    (121, 140),
    (1561, 1580),
    (1586, 1605),
    (1696, 1715),
    (1771, 1790),
    (2036, 2060),
]

SHEET_ID = "1_kiS4BeYT80GfmyrHhhCyycPcNmmC1SDOAfR1K4JjT8"
SHEET_NAME = "Hoja 1"

# =============================
# GOOGLE SHEETS (CONEXIÓN)
# =============================
@st.cache_resource
def conectar_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# =============================
# DATA
# =============================
def cargar_data():
    sheet = conectar_sheet()
    data = sheet.get_all_records()

    if not data:
        return pd.DataFrame(columns=["Nombre", "Numero", "Estado", "Fecha"])

    df = pd.DataFrame(data)
    df["Numero"] = df["Numero"].astype(int)
    return df


def guardar_filas(filas):
    sheet = conectar_sheet()
    sheet.append_rows(filas, value_input_option="USER_ENTERED")

# =============================
# SESSION STATE
# =============================
if "seleccionados" not in st.session_state:
    st.session_state.seleccionados = set()

if "nombre" not in st.session_state:
    st.session_state.nombre = ""

if "cantidad" not in st.session_state:
    st.session_state.cantidad = 1

# =============================
# CARGA INICIAL
# =============================
df = cargar_data()
ocupados = set(df["Numero"].tolist())

# =============================
# UI PRINCIPAL
# =============================
st.title(TITULO)

pagados = len(df[df["Estado"] == "PAGADO"])
reservados = len(df[df["Estado"] == "RESERVADO"])
total_vendido = pagados * PRECIO_TICKET

c1, c2, c3 = st.columns(3)
c1.metric("🎟️ Pagados", pagados)
c2.metric("⏳ Reservados", reservados)
c3.metric("💰 Total vendido", f"S/ {total_vendido}")

st.markdown("---")

# =============================
# DATOS PARTICIPANTE
# =============================
st.subheader("👤 Datos del participante")
st.text_input("Nombre completo", key="nombre")
st.number_input("Cantidad de tickets", min_value=1, max_value=20, key="cantidad")

st.info(
    f"Seleccionados: {len(st.session_state.seleccionados)} / {st.session_state.cantidad}"
)

# =============================
# BOTONES (UX CORRECTA)
# =============================
def boton(num):
    key = f"btn_{num}"

    # Ocupado
    if num in ocupados:
        st.button(f"🔴 {num}", key=key)
        return

    # Seleccionado (se puede quitar)
    if num in st.session_state.seleccionados:
        if st.button(f"🔵 {num}", key=key):
            st.session_state.seleccionados.remove(num)
        return

    # Límite alcanzado → visible pero no seleccionable
    if len(st.session_state.seleccionados) >= st.session_state.cantidad:
        st.button(f"⚪ {num}", key=key)
        return

    # Disponible
    if st.button(f"🟢 {num}", key=key):
        st.session_state.seleccionados.add(num)

# =============================
# GRID DE NÚMEROS
# =============================
st.subheader("📋 Selecciona tus números")

for a, b in RANGOS:
    st.markdown(f"### 🔢 Rango {a:04d} – {b:04d}")
    cols = st.columns(10)
    for i, n in enumerate(range(a, b + 1)):
        with cols[i % 10]:
            boton(n)

# =============================
# RESUMEN
# =============================
st.markdown("---")
numeros = sorted(st.session_state.seleccionados)
monto = len(numeros) * PRECIO_TICKET

st.write(f"👤 **{st.session_state.nombre}**")
st.write(f"🎟️ **Números:** {', '.join(map(str, numeros))}")
st.write(f"💰 **Monto:** S/ {monto}")

# =============================
# CONFIRMAR (ÚNICO WRITE)
# =============================
if (
    st.session_state.nombre
    and len(numeros) == st.session_state.cantidad
):
    if st.button("✅ CONFIRMAR RESERVA"):
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filas = []

        for n in numeros:
            filas.append([
                st.session_state.nombre,
                n,
                "RESERVADO",
                ahora,
            ])

        guardar_filas(filas)

        st.success("Reserva registrada correctamente")
        st.session_state.seleccionados = set()
        st.rerun()

# =============================
# ADMIN
# =============================
st.markdown("---")
st.subheader("🔐 Panel Administrador")

pwd = st.text_input("Contraseña de administrador", type="password")

if pwd == ADMIN_PASSWORD:
    st.success("Acceso concedido")
    st.dataframe(df, use_container_width=True)