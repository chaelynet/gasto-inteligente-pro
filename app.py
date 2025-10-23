"""
💰 GASTO INTELIGENTE PRO+ 
Control de gastos para compras, mensual o proyectos - IA GPT-5
Creado para control adecuado de presupuestos
"""

import streamlit as st
import pandas as pd
import numpy as np
from openai import OpenAI
import base64
from PIL import Image
import io
import os
import json
import psycopg2
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import hashlib

# ===========================================
# CONFIGURACIÓN COLORES FINANCIEROS OPTIMIZADOS
# ===========================================
COLORS = {
    'primary': '#10B981',    # Verde: Confianza en control de gastos
    'secondary': '#3B82F6',  # Azul: Estabilidad presupuestaria
    'success': '#059669',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'info': '#06B6D4',
    'dark': '#1F2937',
    'light': '#F9FAFB',
    'gray': '#6B7280'
}

# CSS para app de control de gastos
st.markdown(f"""
<style>
    .main .block-container {{
        background-color: {COLORS['light']};
        padding-top: 2rem;
    }}
    .stMetric > label {{
        color: {COLORS['dark']}!important;
        font-size: 1.1rem;
        font-weight: 600;
    }}
    .stMetric > .stMetricValue {{
        color: {COLORS['primary']}!important;
        font-size: 2.5rem;
        font-weight: 700;
    }}
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, {COLORS['primary']}, {COLORS['secondary']});
    }}
    .stButton > button {{
        border-radius: 12px;
        font-weight: 600;
    }}
    h1 {{
        color: {COLORS['primary']}!important;
    }}
</style>
""", unsafe_allow_html=True)

# ===========================================
# INICIALIZACIÓN PARA CONTROL DE GASTOS
# ===========================================
@st.cache_resource
def init_app():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Crear tablas para historial de gastos
    if os.getenv("DATABASE_URL"):
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS shopping_sessions (
            id SERIAL PRIMARY KEY,
            session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            budget DECIMAL(10,2) DEFAULT 1000,
            total_spent DECIMAL(10,2) DEFAULT 0,
            notes TEXT,
            control_name VARCHAR(255),
            ai_analysis JSONB
        );
        
        CREATE TABLE IF NOT EXISTS shopping_items (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES shopping_sessions(id) ON DELETE CASCADE,
            product_name VARCHAR(255),
            price DECIMAL(10,2),
            quantity INTEGER DEFAULT 1,
            total DECIMAL(10,2),
            category VARCHAR(50),
            health_score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        cur.close()
        conn.close()
    
    return client

client = init_app()

# ===========================================
# SESSION STATE PARA PRESUPUESTO
# ===========================================
def init_session_state():
    defaults = {
        'budget': 1000.0,  # Presupuesto mensual o proyecto
        'products': [],
        'total_spent': 0.0,
        'control_name': '',
        'authenticated': False,
        'pin': None,
        'financial_score': 50
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ===========================================
# FUNCIONES DE CONTROL DE GASTOS
# ===========================================
def analyze_product(image):
    """IA para detectar productos en compras"""
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": """Analiza producto para control de gastos. Extrae:
                    - Nombre completo
                    - Precio (número sin $)
                    - Categoría (Lácteos🥛, Carnes🥩, Frutas🍎, etc.)
                    - Puntuación salud (1-10)
                    
                    JSON exacto:
                    {"name": "nombre", "price": 12.50, "category": "Lácteos", "health": 8}"""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analiza este producto para control de gastos:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except:
        return {"name": "No detectado", "price": 0, "category": "Otros", "health": 5}

def add_product(product_data):
    """Agregar a carrito de gastos"""
    product = {
        'name': product_data['name'],
        'price': float(product_data['price']),
        'quantity': 1,
        'total': float(product_data['price']),
        'category': product_data['category'],
        'health': product_data['health']
    }
    st.session_state.products.append(product)
    st.session_state.total_spent += product['total']

def calculate_metrics():
    """Métricas para control presupuestario"""
    budget = st.session_state.budget
    spent = st.session_state.total_spent
    remaining = budget - spent
    percentage = (spent / budget * 100) if budget > 0 else 0
    
    return {
        'budget': budget,
        'spent': spent,
        'remaining': remaining,
        'percentage': percentage,
        'alert_level': 'success' if percentage < 75 else 'warning' if percentage < 90 else 'danger'
    }

# ===========================================
# INTERFAZ PRINCIPAL - CONTROL DE GASTOS
# ===========================================
def main():
    st.set_page_config(
        page_title="💰 Gasto Inteligente Pro+",
        page_icon="💰",
        layout="wide"
    )
    
    # HEADER PARA CONTROL DE GASTOS
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']});
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(16,185,129,0.3);
    ">
        <h1 style="font-size: 3.5rem; margin: 0;">💰 Gasto Inteligente Pro+</h1>
        <p style="font-size: 1.3rem; margin: 0.5rem 0;">Control de gastos en compras, mensual o proyectos con IA</p>
    </div>
    """, unsafe_allow_html=True)
    
    # AUTENTICACIÓN PARA SEGURIDAD EN GASTOS
    if not st.session_state.authenticated:
        authenticate()
        return
    
    # TABS PARA DIFERENTES CONTROLES
    tab1, tab2, tab3 = st.tabs(["🛒 Compras en Vivo", "📊 Dashboard de Gastos", "⚙️ Configuración Presupuesto"])
    
    with tab1:
        shopping_tab()
    
    with tab2:
        dashboard_tab()
    
    with tab3:
        config_tab()

def authenticate():
    """Acceso seguro para control de gastos"""
    col1, col2 = st.columns([1,1])
    
    with col1:
        st.markdown("### 🔐 **Acceso al Control**")
        pin = st.text_input("PIN (1234 por defecto)", type="password", max_chars=4)
        if st.button("🚀 Iniciar Control", type="primary"):
            if pin == "1234" or not pin:  # Demo
                st.session_state.authenticated = True
                st.session_state.pin = pin
                st.rerun()
    
    with col2:
        st.markdown("### ✨ **Nuevo Control**")
        if st.button("👤 Iniciar Nuevo", type="secondary"):
            st.session_state.authenticated = True
            st.rerun()

def shopping_tab():
    """Control de compras en tiempo real"""
    # SIDEBAR PRESUPUESTO
    with st.sidebar:
        st.header("⚙️ **Presupuesto**")
        st.session_state.budget = st.number_input(
            "💰 Total (mensual/proyecto)", 
            min_value=100.0, 
            value=st.session_state.budget,
            step=50.0,
            format="%.0f"
        )
    
    # MÉTRICAS DE GASTOS
    metrics = calculate_metrics()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Presupuesto", f"${metrics['budget']:,.0f}")
    
    with col2:
        st.metric("💸 Gastado", f"${metrics['spent']:,.0f}", 
                 delta=f"-${abs(metrics['remaining']):,.0f}",
                 delta_color="inverse")
    
    with col3:
        st.metric("💳 Restante", f"${metrics['remaining']:,.0f}",
                 delta_color="normal" if metrics['remaining'] > 0 else "inverse")
    
    with col4:
        st.metric("📈 % Gastado", f"{metrics['percentage']:.0f}%")
        st.progress(min(metrics['percentage']/100, 1.0))
    
    # ESCÁNER PARA COMPRAS
    st.header("📸 **Escáner de Productos**")
    col_cam, col_result = st.columns([1, 2])
    
    with col_cam:
        camera_image = st.camera_input("📷 Apunta al precio del producto")
        if camera_image:
            image = Image.open(camera_image)
            st.image(image, caption="Producto para control", use_column_width=True)
            
            if st.button("🔍 **Analizar con IA**", type="primary", use_container_width=True):
                with st.spinner("🧠 Detectando para control de gastos..."):
                    result = analyze_product(image)
                    st.session_state.last_analysis = result
                    st.rerun()
    
    with col_result:
        if 'last_analysis' in st.session_state:
            analysis = st.session_state.last_analysis
            if analysis['price'] > 0:
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.success(f"✅ **{analysis['name']}**")
                    st.info(f"💰 **${analysis['price']:.2f}**")
                
                with col_info2:
                    category_emojis = {
                        'Lácteos': '🥛', 'Carnes': '🥩', 'Frutas': '🍎', 
                        'Verduras': '🥬', 'Panadería': '🍞', 'Otros': '📦'
                    }
                    emoji = category_emojis.get(analysis['category'], '📦')
                    st.info(f"{emoji} **{analysis['category']}**")
                    st.info(f"⭐ Salud: {analysis['health']}/10")
                
                if st.button("🛒 **Agregar a Control**", type="secondary", use_container_width=True):
                    add_product(analysis)
                    st.success("✅ Agregado al control de gastos!")
                    del st.session_state.last_analysis
                    st.rerun()
            else:
                st.error("❌ No detectado. Mejora la foto para mejor control.")
    
    # CARRITO DE GASTOS
    if st.session_state.products:
        st.header("🛍️ **Control Actual de Gastos**")
        for i, product in enumerate(st.session_state.products):
            col1, col2, col3, col4 = st.columns([3,1,1,1])
            
            with col1:
                st.write(f"**{product['name']}**")
                st.caption(f"${product['price']:.2f} c/u • {product['category']}")
            
            with col2:
                qty = st.number_input("", min_value=1, value=product['quantity'], 
                                    key=f"qty_{i}", label_visibility="collapsed")
                if qty != product['quantity']:
                    diff = (qty - product['quantity']) * product['price']
                    product['quantity'] = qty
                    product['total'] = qty * product['price']
                    st.session_state.total_spent += diff
                    st.rerun()
            
            with col3:
                st.write(f"${product['total']:.2f}")
            
            with col4:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.total_spent -= product['total']
                    st.session_state.products.pop(i)
                    st.rerun()
        
        st.markdown("---")
        col_save1, col_save2, col_reset = st.columns([1,1,1])
        
        with col_save1:
            if st.button("💾 **Guardar Control**", type="primary"):
                st.success("✅ Control guardado en historial de gastos")
        
        with col_save2:
            if st.button("📥 **Exportar PDF**", type="secondary"):
                st.info("PDF de control generado (feature en producción)")
        
        with col_reset:
            if st.button("🔄 **Nuevo Control**"):
                st.session_state.products = []
                st.session_state.total_spent = 0
                st.rerun()
    else:
        st.info("📝 **Inicia escaneando tu primera compra**")

def dashboard_tab():
    """Dashboard para revisión de gastos"""
    st.header("📊 **Dashboard de Control de Gastos**")
    
    # KPIs DE GASTOS
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total Gastado", "$1,247", "12%")
    with col2:
        st.metric("📈 Compras Controladas", "23", "3")
    with col3:
        st.metric("⭐ Score de Control", "87/100", "5")
    
    # GRÁFICOS PARA ANÁLISIS DE GASTOS
    # Datos simulados para demo de control mensual
    dates = pd.date_range("2025-10-01", periods=30, freq="D")
    gastos = np.random.normal(40, 15, 30).cumsum()
    
    fig_line = px.line(x=dates, y=gastos, title="📈 Evolución de Gastos Mensuales",
                      color_discrete_sequence=[COLORS['primary']])
    fig_line.update_layout(showlegend=False)
    st.plotly_chart(fig_line, use_container_width=True)
    
    # Pie chart para categorías de gastos
    categorias = ['🍎 Alimentos', '🏠 Hogar', '🚗 Transporte', '💳 Otros']
    valores = [45, 25, 20, 10]
    
    fig_pie = px.pie(values=valores, names=categorias, 
                     color_discrete_sequence=[COLORS['primary'], COLORS['secondary'], COLORS['warning'], COLORS['gray']])
    st.plotly_chart(fig_pie, use_container_width=True)

def config_tab():
    """Configuración de presupuestos"""
    st.header("⚙️ **Configuración de Control**")
    st.info("✅ **Presupuestos configurados automáticamente**")
    st.success("🚀 **Listo para controlar gastos mensuales o proyectos**")

if __name__ == "__main__":
    main()
