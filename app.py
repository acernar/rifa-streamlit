import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
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
# GOOGLE SHEETS
# =============================
@st.cache_resource
def conectar_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def cargar_data():
    sheet = conectar_sheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Nombre", "Numero", "Estado", "Fecha"])
    return pd.DataFrame(data)


def guardar_filas(filas):
    sheet = conectar_sheet()
    sheet.append_rows(filas, value_input_option="USER_ENTERED")


def actualizar_estado(numeros, nuevo_estado):
    sheet = conectar_sheet()
    data = sheet.get_all_values()

    cambios = 0
    for i in range(1, len(data)):
        try:
            num = int(data[i][1])  # Columna Numero (B)
        except:
            continue

        if num in numeros:
            sheet.update(f"C{i+1}", [[nuevo_estado]])
            cambios += 1

    return cambios


# =============================
# UTILIDADES
# =============================
def parsear_numeros(texto):
    nums = set()
    for parte in texto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            a, b = parte.split("-")
            nums.update(range(int(a), int(b) + 1))
        else:
            nums.add(int(parte))
    return sorted(nums)


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
ocupados = set(df["Numero"].astype(int).tolist())

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
# PARTICIPANTE
# =============================
st.subheader("👤 Datos del participante")
st.text_input("Nombre completo", key="nombre")
st.number_input("Cantidad de tickets", 1, 20, key="cantidad")

st.info(
    f"Seleccionados: {len(st.session_state.seleccionados)} / {st.session_state.cantidad}"
)

# =============================
# BOTONES
# =============================
def boton(num):
    if num in ocupados:
        st.button(f"🔴 {num}", disabled=True)
        return

    if num in st.session_state.seleccionados:
        if st.button(f"🔵 {num}"):
            st.session_state.seleccionados.remove(num)
        return

    if len(st.session_state.seleccionados) >= st.session_state.cantidad:
        st.button(f"⚪ {num}", disabled=True)
        return

    if st.button(f"🟢 {num}"):
        st.session_state.seleccionados.add(num)


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

# 🔒 recalcular SIEMPRE desde session_state ya consolidado
numeros = list(st.session_state.seleccionados)
numeros.sort()
monto = len(numeros) * PRECIO_TICKET

st.write(f"👤 **{st.session_state.nombre}**")
st.write(f"🎟️ **Números:** {', '.join(map(str, numeros))}")
st.write(f"💰 **Monto:** S/ {monto}")

# =============================
# CONFIRMAR (SOLO CAMBIO: HORA)
# =============================
if (
    st.session_state.nombre
    and len(numeros) == st.session_state.cantidad
):
    if st.button("✅ CONFIRMAR RESERVA"):
        ahora = datetime.now(ZoneInfo("America/Lima")).strftime("%d/%m/%Y %H:%M")
        filas = [
            [st.session_state.nombre, n, "RESERVADO", ahora]
            for n in numeros
        ]

        guardar_filas(filas)
        st.success("Reserva registrada correctamente")

        st.session_state.seleccionados = set()
        st.rerun()

# =============================
# PANEL ADMINISTRADOR
# =============================
st.markdown("---")
st.subheader("🔐 Panel Administrador")

pwd = st.text_input("Contraseña", type="password")

if pwd == ADMIN_PASSWORD:
    st.success("Acceso concedido")

    st.dataframe(df, use_container_width=True)

    st.markdown("### ✏️ Cambiar estado por números")
    nums_txt = st.text_input("Números (ej: 1577,1579,1600-1605)")
    nuevo_estado = st.selectbox("Nuevo estado", ["RESERVADO", "PAGADO"])

    if st.button("Actualizar estado"):
        lista = parsear_numeros(nums_txt)
        if not lista:
            st.warning("No se ingresaron números válidos")
        else:
            cambios = actualizar_estado(lista, nuevo_estado)
            if cambios:
                st.success(f"{cambios} registros actualizados")
                st.rerun()
            else:
                st.warning("No se encontró ningún número")

    st.markdown("### 📱 Reporte WhatsApp")

    def reporte_whatsapp(df):
        msg = (
            "📢 *REPORTE RIFA – PROMOCIÓN 2026*\n\n"
            f"🎟️ Total: {len(df)}\n"
            f"✅ Pagados: {len(df[df['Estado']=='PAGADO'])}\n"
            f"⏳ Reservados: {len(df[df['Estado']=='RESERVADO'])}\n"
            f"💰 Recaudado: S/ {len(df[df['Estado']=='PAGADO']) * PRECIO_TICKET}\n\n"
        )

        for nombre, g in df.groupby("Nombre"):
            nums = ", ".join(map(str, g["Numero"]))
            estado = g["Estado"].iloc[0]
            msg += f"• {nombre}\n  {nums}\n  {estado}\n\n"

        return msg

    st.text_area("Copiar y pegar", reporte_whatsapp(df), height=300)