import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt
from sqlalchemy import create_engine, text

# --- 1. Database Configuration (PostgreSQL) ---
@st.cache_resource
def get_engine():
    return create_engine(st.secrets["database"]["url"])

def run_query(query, params=None):
    """Execute a query and return results as DataFrame for SELECT, or commit for others."""
    with get_engine().connect() as conn:
        result = conn.execute(text(query), params or {})
        if query.strip().upper().startswith("SELECT"):
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        conn.commit()
        return None

def init_db():
    """Initialize database tables if they don't exist."""
    try:
        queries = [
            '''CREATE TABLE IF NOT EXISTS employees (
                emp_id SERIAL PRIMARY KEY, 
                emp_name TEXT UNIQUE, 
                emp_nickname TEXT, 
                position TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS job_positions (
                pos_id SERIAL PRIMARY KEY, 
                pos_name TEXT UNIQUE NOT NULL
            )''',
            '''CREATE TABLE IF NOT EXISTS categories (
                cat_id SERIAL PRIMARY KEY, 
                cat_name TEXT UNIQUE NOT NULL,
                group_name TEXT DEFAULT 'Other'
            )''',
            '''CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY, 
                product_name TEXT UNIQUE NOT NULL, 
                cat_id INTEGER, 
                price REAL
            )''',
            '''CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY, 
                full_name TEXT NOT NULL, 
                nickname TEXT, 
                phone TEXT, 
                line_id TEXT, 
                facebook TEXT, 
                instagram TEXT,
                address_detail TEXT, 
                province TEXT, 
                district TEXT, 
                sub_district TEXT, 
                zipcode TEXT,
                gender TEXT, 
                marital_status TEXT,
                has_children TEXT,
                has_children TEXT,
                birth_date DATE,
                cust_note TEXT, 
                assigned_sales_id INTEGER
            )''',
            '''CREATE TABLE IF NOT EXISTS bills (
                bill_id TEXT PRIMARY KEY,
                customer_id INTEGER,
                seller_id INTEGER,
                total_amount REAL,
                discount REAL,
                final_amount REAL,
                payment_method TEXT,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS bill_items (
                item_id SERIAL PRIMARY KEY,
                bill_id TEXT,
                product_id INTEGER,
                product_name TEXT,
                qty INTEGER,
                unit_price REAL,
                subtotal REAL
            )''',
            '''CREATE TABLE IF NOT EXISTS sales_history (
                sale_id SERIAL PRIMARY KEY, 
                customer_id INTEGER, 
                product_id INTEGER, 
                amount REAL, 
                payment_method TEXT, 
                sale_channel TEXT, 
                sale_note TEXT, 
                closed_by_emp_id INTEGER, 
                sale_date DATE
            )''',
            '''CREATE TABLE IF NOT EXISTS marketing_goals (
                goal_id SERIAL PRIMARY KEY,
                cat_id INTEGER,
                channel TEXT,
                target_amount REAL DEFAULT 0,
                lead_forecast INTEGER DEFAULT 0,
                month_year TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS daily_leads (
                lead_id SERIAL PRIMARY KEY,
                lead_date DATE DEFAULT CURRENT_DATE,
                channel TEXT,
                cat_id INTEGER,
                lead_count INTEGER DEFAULT 0
            )''',
            '''CREATE TABLE IF NOT EXISTS monthly_goals (
                goal_id SERIAL PRIMARY KEY,
                month_year TEXT UNIQUE,
                high_target REAL,
                mid_target REAL,
                low_target REAL,
                mid_pct REAL DEFAULT 75,
                low_pct REAL DEFAULT 50
            )''',
            '''CREATE TABLE IF NOT EXISTS marketing_config (
                config_id SERIAL PRIMARY KEY,
                month_year TEXT,
                cat_id INTEGER,
                team_name TEXT,
                team_weight REAL,
                channel TEXT,
                channel_weight REAL,
                chan_forecast_amount REAL DEFAULT 0,
                lead_forecast INTEGER DEFAULT 0,
                register_target INTEGER DEFAULT 0,
                UNIQUE(month_year, cat_id, team_name, channel)
            )''',
            '''CREATE TABLE IF NOT EXISTS daily_registers (
                reg_id SERIAL PRIMARY KEY,
                reg_date DATE DEFAULT CURRENT_DATE,
                channel TEXT,
                cat_id INTEGER,
                reg_count INTEGER DEFAULT 0
            )''',
            '''CREATE TABLE IF NOT EXISTS category_team_weights (
                weight_id SERIAL PRIMARY KEY,
                month_year TEXT,
                cat_id INTEGER,
                mkt_weight REAL DEFAULT 70,
                sale_weight REAL DEFAULT 30,
                UNIQUE(month_year, cat_id)
            )''',
            '''CREATE TABLE IF NOT EXISTS individual_goals (
                goal_id SERIAL PRIMARY KEY,
                month_year TEXT,
                emp_id INTEGER,
                target_amount REAL DEFAULT 0,
                UNIQUE(month_year, emp_id)
            )''',
            '''CREATE TABLE IF NOT EXISTS packages (
                package_id SERIAL PRIMARY KEY,
                package_name TEXT UNIQUE NOT NULL,
                base_price REAL,
                discounted_price REAL,
                note TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS package_products (
                id SERIAL PRIMARY KEY,
                package_id INTEGER,
                product_id INTEGER,
                is_free BOOLEAN DEFAULT FALSE
            )''',
            '''CREATE TABLE IF NOT EXISTS course_credits (
                credit_id SERIAL PRIMARY KEY,
                customer_id INTEGER,
                bill_id TEXT,
                product_id INTEGER,
                buy_date DATE DEFAULT CURRENT_DATE,
                expiry_date DATE,
                status TEXT DEFAULT 'Available'
            )''',
            '''CREATE TABLE IF NOT EXISTS refund_requests (
                request_id SERIAL PRIMARY KEY,
                bill_id TEXT,
                customer_id INTEGER,
                requested_by INTEGER,
                refund_amount REAL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                manager_note TEXT,
                approved_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )'''
        ]
        for q in queries:
            run_query(q)
        # Migration: Ensure column exists
        run_query("ALTER TABLE marketing_config ADD COLUMN IF NOT EXISTS chan_forecast_amount REAL DEFAULT 0")
        run_query("ALTER TABLE monthly_goals ADD COLUMN IF NOT EXISTS mid_pct REAL DEFAULT 75")
        run_query("ALTER TABLE monthly_goals ADD COLUMN IF NOT EXISTS low_pct REAL DEFAULT 50")
        
        # Add column to 'categories' if it doesn't exist
        try:
            run_query("ALTER TABLE categories ADD COLUMN IF NOT EXISTS group_name TEXT DEFAULT 'Other'")
        except: pass

        # Seed Categories if empty
        check_cat = run_query("SELECT COUNT(*) as cnt FROM categories")
        if check_cat['cnt'][0] == 0:
            seed_data = [
                ('Full Course', 'Cooking Course'), ('Package', 'Cooking Course'), 
                ('Japanese Course', 'Cooking Course'), ('Special Course', 'Cooking Course'), 
                ('Kids Course', 'Cooking Course'), ('E-learning', 'Cooking Course'),
                ('RomRental / Workshop', 'Service'), ('School Canteen Pinto', 'Service'), 
                ('Chef Table Dinner', 'Service'), ('Food / Equipment', 'Service'), 
                ('Naeki', 'Service'), ('Sponsor', 'Service')
            ]
            for name, grp in seed_data:
                run_query("INSERT INTO categories (cat_name, group_name) VALUES (:n, :g)", {"n": name, "g": grp})
        
        # Add columns to 'bills' if they don't exist
        try:
            run_query("ALTER TABLE bills ADD COLUMN IF NOT EXISTS sale_channel TEXT")
        except: pass
        
        # Add columns to 'customers' if they don't exist
        try:
            run_query("ALTER TABLE customers ADD COLUMN IF NOT EXISTS gender TEXT")
            run_query("ALTER TABLE customers ADD COLUMN IF NOT EXISTS marital_status TEXT")
            run_query("ALTER TABLE customers ADD COLUMN IF NOT EXISTS has_children TEXT")
            run_query("ALTER TABLE customers ADD COLUMN IF NOT EXISTS birth_date DATE")
        except: pass

        # Add columns for Package System
        try:
            run_query("ALTER TABLE bill_items ADD COLUMN IF NOT EXISTS package_id INTEGER")
            run_query("ALTER TABLE bills ADD COLUMN IF NOT EXISTS package_id INTEGER")
        except: pass
    except Exception as e:
        st.error(f"⚠️ Database Error: {e}")

def run_migration():
    """Migration placeholder - PostgreSQL tables created with correct schema."""
    st.success("✅ ระบบใช้ PostgreSQL บน Supabase - ไม่ต้อง migrate")


# --- 2. ข้อมูลที่ตั้ง (77 จังหวัด) ---
try:
    from thai_locations import LOCATION_DATA
except ImportError:
    st.error("❌ ไม่พบไฟล์ thai_locations.py")
    LOCATION_DATA = {}

ALL_PROVINCES = sorted(list(LOCATION_DATA.keys()))



init_db()

# --- 3. UI/UX Aesthetics (Premium Glassmorphism & Modern Color Palette) ---
st.set_page_config(page_title="CRM Smart Pro", layout="wide", initial_sidebar_state="expanded")

if 'theme' not in st.session_state:
    st.session_state.theme = 'Light'

def toggle_theme():
    st.session_state.theme = 'Dark' if st.session_state.theme == 'Light' else 'Light'

# Unified Design System
if st.session_state.theme == 'Dark':
    bg_color = "#0f172a"
    card_bg = "rgba(30, 41, 59, 0.7)"
    text_color = "#f8fafc"
    border_color = "rgba(255, 255, 255, 0.1)"
    accent_color = "#38bdf8" # Sky Blue
else:
    bg_color = "#f1f5f9"
    card_bg = "rgba(255, 255, 255, 0.8)"
    text_color = "#1e293b"
    border_color = "rgba(0, 0, 0, 0.05)"
    accent_color = "#0ea5e9" # Blue

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Kanit:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Outfit', 'Kanit', sans-serif;
    }}

    .stApp {{
        background-color: {bg_color};
    }}

    /* Premium Metric Cards */
    [data-testid="stMetric"] {{
        background: {card_bg};
        backdrop-filter: blur(10px);
        border: 1px solid {border_color};
        padding: 20px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        transition: transform 0.2s ease-in-out;
    }}
    
    [data-testid="stMetric"]:hover {{
        transform: translateY(-5px);
        border-color: {accent_color};
    }}

    .stMetricValue {{
        font-size: 2rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, {accent_color}, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background-color: {bg_color} !important;
        border-right: 1px solid {border_color};
    }}

    /* Tables & DataFrames */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid {border_color};
    }}

    /* Custom Headers */
    h1, h2, h3 {{
        color: {text_color} !important;
        letter-spacing: -0.025em;
    }}

    /* Modern Buttons */
    div.stButton > button {{
        border-radius: 10px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        transition: all 0.2s;
    }}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 CRM System")
    
    # Theme Toggle Button
    theme_icon = "🌞" if st.session_state.theme == "Light" else "🌙"
    st.button(f"{theme_icon} Switch to { 'Dark' if st.session_state.theme == 'Light' else 'Light' } Mode", 
              on_click=toggle_theme, use_container_width=True)
    
    st.markdown("---")
    
    if 'menu_option' not in st.session_state: st.session_state.menu_option = "📊 Dashboard"
    def set_menu(option): st.session_state.menu_option = option
    st.button("📊 Dashboard", on_click=set_menu, args=("📊 Dashboard",), use_container_width=True)
    st.button("💰 บันทึกการขาย", on_click=set_menu, args=("💰 บันทึกการขาย",), use_container_width=True)
    st.button("👥 จัดการลูกค้า", on_click=set_menu, args=("👥 จัดการลูกค้า",), use_container_width=True)
    st.button("👔 จัดการพนักงาน", on_click=set_menu, args=("👔 จัดการพนักงาน",), use_container_width=True)
    st.button("📦 จัดการสินค้า", on_click=set_menu, args=("📦 จัดการสินค้า",), use_container_width=True)
    st.button("🎁 ตั้งค่าแพ็กเกจ", on_click=set_menu, args=("🎁 ตั้งค่าแพ็กเกจ",), use_container_width=True)
    
    st.markdown("---")
    st.subheader("📈 Marketing Tools")
    st.button("🏆 ABC Analysis", on_click=set_menu, args=("🏆 ABC Analysis",), use_container_width=True)
    st.button("💵 P&L Dashboard", on_click=set_menu, args=("💵 P&L Dashboard",), use_container_width=True)
    st.button("📊 Lead Funnel", on_click=set_menu, args=("📊 Lead Funnel",), use_container_width=True)
    st.button("🔔 Follow-up System", on_click=set_menu, args=("🔔 Follow-up System",), use_container_width=True)
    st.button("💰 Channel ROI", on_click=set_menu, args=("💰 Channel ROI",), use_container_width=True)
    st.button("🎯 Campaign Tracker", on_click=set_menu, args=("🎯 Campaign Tracker",), use_container_width=True)
    st.button("🧩 Customer Segments", on_click=set_menu, args=("🧩 Customer Segments",), use_container_width=True)
    st.button("📅 Event Calendar", on_click=set_menu, args=("📅 Event Calendar",), use_container_width=True)
    
    st.markdown("---")
    st.subheader("💸 Refund & Approval")
    st.button("💸 ขอรีฟันเงิน", on_click=set_menu, args=("💸 ขอรีฟันเงิน",), use_container_width=True)
    st.button("✅ อนุมัติรีฟัน", on_click=set_menu, args=("✅ อนุมัติรีฟัน",), use_container_width=True)
    
    st.markdown("---")
    st.button("⚙️ ตั้งค่าระบบ", on_click=set_menu, args=("⚙️ ตั้งค่าระบบ",), use_container_width=True)

choice = st.session_state.menu_option

# --- 3. ส่วนการทำงานแต่ละเมนู ---

# --- 📊 Dashboard ---
# --- 📊 Redesigned Dashboard ---
if choice == "📊 Dashboard":
    st.title("📊 สรุปภาพรวมระบบ (Dashboard)")
    
    # 1. Main Revenue Query (Bills ONLY - for accurate totals)
    df_bills = run_query("SELECT sale_date, final_amount FROM bills")
    if not df_bills.empty:
        df_bills['sale_date'] = pd.to_datetime(df_bills['sale_date'])
        df_bills['date'] = df_bills['sale_date'].dt.date
    else:
        df_bills = pd.DataFrame(columns=['sale_date', 'final_amount', 'date'])

    # 2. Item-level Query (For Product Mix / Pie Charts)
    df_items = run_query("""
        SELECT b.sale_date, bi.subtotal as total, p.product_name, cat.cat_name
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.bill_id
        LEFT JOIN products p ON bi.product_id = p.product_id
        LEFT JOIN categories cat ON p.cat_id = cat.cat_id
    """)
    if not df_items.empty:
        df_items['sale_date'] = pd.to_datetime(df_items['sale_date'])
        df_items['date'] = df_items['sale_date'].dt.date

    # --- Calculations ---
    now = datetime.now()
    today = now.date()
    
    # ⚠️ Pending Refund Notification
    pending_refunds = run_query("SELECT COUNT(*) as cnt FROM refund_requests WHERE status = 'pending'")
    if not pending_refunds.empty and pending_refunds['cnt'][0] > 0:
        cnt = pending_refunds['cnt'][0]
        st.warning(f"⚠️ **มีคำขอรีฟันรออนุมัติ {cnt} รายการ** → [ไปหน้าอนุมัติ](#) (กดเมนู '✅ อนุมัติรีฟัน')")
    
    # Revenue Metrcis
    sales_today = df_bills[df_bills['date'] == today]['final_amount'].sum() if not df_bills.empty else 0
    sales_month = df_bills[(df_bills['sale_date'].dt.month == now.month) & (df_bills['sale_date'].dt.year == now.year)]['final_amount'].sum() if not df_bills.empty else 0
    sales_year = df_bills[df_bills['sale_date'].dt.year == now.year]['final_amount'].sum() if not df_bills.empty else 0
    
    # Revenue Overview Section
    st.markdown("### 💰 สรุปรายได้ (Revenue Summary)")
    m1, m2, m3 = st.columns(3)
    m1.metric("ยอดขายวันนี้", f"฿{sales_today:,.2f}")
    m2.metric("ยอดขายเดือนนี้", f"฿{sales_month:,.2f}")
    m3.metric("ยอดขายปีนี้", f"฿{sales_year:,.2f}")
    
    st.write("---")
    
    # --- Sales Trend & Pie Charts ---
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### 📈 แนวโน้มยอดขาย (เดือนนี้)")
        if not df_bills.empty:
            df_trend = df_bills[(df_bills['sale_date'].dt.month == now.month) & (df_bills['sale_date'].dt.year == now.year)].copy()
            daily_trend = df_trend.groupby('date')['final_amount'].sum().reset_index()
            st.area_chart(daily_trend.set_index('date'), use_container_width=True, color="#38bdf8")
        else:
            st.info("ไม่มีข้อมูลยอดขายเดือนนี้")

    with col_right:
        st.markdown("### 🥧 สัดส่วนสินค้า (Product Mix)")
        
        # Tabs for Daily / Weekly / Monthly
        t_d, t_w, t_m = st.tabs(["รายวัน", "รายสัปดาห์", "รายเดือน"])
        
        def plot_pie(df_source, title):
            if df_source.empty:
                st.caption(f"ไม่มีข้อมูล {title}")
                return
            
            # Group by Product
            mix = df_source.groupby('product_name')['total'].sum().reset_index()
            mix = mix.sort_values('total', ascending=False).head(10) # Top 10
            
            import altair as alt
            base = alt.Chart(mix).encode(theta=alt.Theta("total", stack=True))
            pie = base.mark_arc(outerRadius=120, innerRadius=60).encode(
                color=alt.Color("product_name"),
                order=alt.Order("total", sort="descending"),
                tooltip=["product_name", alt.Tooltip("total", format=",.0f")]
            )
            text = base.mark_text(radius=140).encode(
                text=alt.Text("total", format=",.0f"),
                order=alt.Order("total", sort="descending"),
                color=alt.value(text_color) 
            )
            st.altair_chart(pie + text, use_container_width=True)

        with t_d:
            if not df_items.empty:
                df_d = df_items[df_items['date'] == today]
                plot_pie(df_d, "วันนี้")
        
        with t_w:
            if not df_items.empty:
                # Last 7 days
                week_ago = today - timedelta(days=7)
                df_w = df_items[df_items['date'] >= week_ago]
                plot_pie(df_w, "7 วันล่าสุด")

        with t_m:
            if not df_items.empty:
                df_m = df_items[(df_items['sale_date'].dt.month == now.month) & (df_items['sale_date'].dt.year == now.year)]
                plot_pie(df_m, "เดือนนี้")

    st.write("---")
    
    # Recent Bills Table
    st.markdown("### 📜 รายการขายล่าสุด")
    df_recent = run_query("""
        SELECT b.bill_id, b.sale_date, c.full_name as customer, b.final_amount, b.payment_method
        FROM bills b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        ORDER BY b.sale_date DESC
        LIMIT 10
    """)
    st.dataframe(df_recent, use_container_width=True, hide_index=True,
                 column_config={
                     "bill_id": "เลขที่บิล",
                     "sale_date": st.column_config.DatetimeColumn("วันที่-เวลา", format="DD/MM/YYYY HH:mm"),
                     "final_amount": st.column_config.NumberColumn("ยอดรวม", format="฿%,.2f"),
                     "customer": "ลูกค้า",
                     "payment_method": "วิธีชำระเงิน"
                 })

# --- 🎁 ตั้งค่าแพ็กเกจ (Package Management) ---
elif choice == "🎁 ตั้งค่าแพ็กเกจ":
    st.title("🎁 จัดการแพ็กเกจสินค้า (Package Settings)")
    st.markdown("ใช้สำหรับกำหนดหลักสูตรเหมาจ่ายที่ประกอบไปด้วยหลายคอร์สเรียน")
    
    # 1. Add/Edit Package Form
    with st.expander("➕ สร้างหรือแก้ไขแพ็กเกจ", expanded=True):
        df_all_p = run_query("SELECT product_id, product_name, price FROM products")
        
        # Check for Edit Mode
        all_pkgs = run_query("SELECT * FROM packages")
        pkg_opts = ["-- สร้างแพ็กเกจใหม่ --"] + [f"{r['package_id']} | {r['package_name']}" for _, r in all_pkgs.iterrows()]
        sel_pkg = st.selectbox("เลือกแพ็กเกจเพื่อแก้ไข", pkg_opts)
        
        edit_mode = sel_pkg != "-- สร้างแพ็กเกจใหม่ --"
        edit_id = int(sel_pkg.split(" | ")[0]) if edit_mode else None
        
        curr_pkg_data = all_pkgs[all_pkgs['package_id'] == edit_id].iloc[0] if edit_mode else None
        
        with st.form("pkg_form"):
            name = st.text_input("ชื่อแพ็กเกจ/หลักสูตร", value=curr_pkg_data['package_name'] if edit_mode else "")
            col1, col2 = st.columns(2)
            base_p = col1.number_input("ราคารวมปกติ (Base Price)", value=float(curr_pkg_data['base_price']) if edit_mode else 0.0)
            disc_p = col2.number_input("ราคาขายพิเศษ (Discounted Price)", value=float(curr_pkg_data['discounted_price']) if edit_mode else 0.0)
            note = st.text_area("หมายเหตุ/เงื่อนไข", value=curr_pkg_data['note'] if edit_mode else "")
            
            # Multi-select for default courses
            current_items = []
            if edit_mode:
                df_cur_items = run_query("SELECT product_id FROM package_products WHERE package_id = :id", {"id": edit_id})
                current_items = df_cur_items['product_id'].tolist()
            
            p_opts = {f"{r['product_id']} | {r['product_name']}": r['product_id'] for _, r in df_all_p.iterrows()}
            sel_items_str = st.multiselect("เลือกคอร์สเรียนที่รวมในแพ็กเกจ", options=list(p_opts.keys()), 
                                           default=[k for k, v in p_opts.items() if v in current_items])
            
            sub1, sub2 = st.columns(2)
            if sub1.form_submit_button("💾 บันทึกแพ็กเกจ", use_container_width=True):
                if name:
                    if edit_mode:
                        run_query("UPDATE packages SET package_name=:n, base_price=:bp, discounted_price=:dp, note=:nt WHERE package_id=:id",
                                  {"n": name, "bp": base_p, "dp": disc_p, "nt": note, "id": edit_id})
                        # Update products: delete and re-insert
                        run_query("DELETE FROM package_products WHERE package_id=:id", {"id": edit_id})
                    else:
                        run_query("INSERT INTO packages (package_name, base_price, discounted_price, note) VALUES (:n, :bp, :dp, :nt)",
                                  {"n": name, "bp": base_p, "dp": disc_p, "nt": note})
                        res = run_query("SELECT package_id FROM packages WHERE package_name=:n ORDER BY package_id DESC LIMIT 1", {"n": name})
                        edit_id = int(res['package_id'][0])
                    
                    for s in sel_items_str:
                        pid = p_opts[s]
                        run_query("INSERT INTO package_products (package_id, product_id) VALUES (:pkg, :pid)", {"pkg": edit_id, "pid": pid})
                    
                    st.success("บันทึกข้อมูลเรียบร้อย!")
                    st.rerun()
            
            if edit_mode and sub2.form_submit_button("🗑️ ลบแพ็กเกจ", use_container_width=True):
                run_query("DELETE FROM packages WHERE package_id=:id", {"id": edit_id})
                run_query("DELETE FROM package_products WHERE package_id=:id", {"id": edit_id})
                st.success("ลบข้อมูลเรียบร้อย!")
                st.rerun()

    st.divider()
    st.subheader("📋 รายการแพ็กเกจทั้งหมด")
    df_pkgs_list = run_query("""
        SELECT p.package_id, p.package_name, p.discounted_price, 
               (SELECT COUNT(*) FROM package_products pp WHERE pp.package_id = p.package_id) as items_count
        FROM packages p
    """)
    if not df_pkgs_list.empty:
        st.dataframe(df_pkgs_list, hide_index=True, use_container_width=True,
                     column_config={
                         "package_id": "ID",
                         "package_name": "ชื่อหลักสูตร",
                         "discounted_price": st.column_config.NumberColumn("ราคาขาย", format="฿%,.2f"),
                         "items_count": "จำนวนคอร์ส"
                     })
    else:
        st.info("ยังไม่มีข้อมูลแพ็กเกจ")

# --- 🏆 ABC Analysis ---
elif choice == "🏆 ABC Analysis":
    st.header("🏆 วิเคราะห์ลำดับความสำคัญสินค้า (ABC Analysis)")
    st.markdown("""
        แบ่งกลุ่มสินค้าตามสัดส่วนรายได้ (**หลักการ 80/20**):
        - **A (High Value)**: สินค้าทำเงินหลัก (สะสม 0-80%)
        - **B (Medium Value)**: สินค้าทำเงินรอง (สะสม 81-95%)
        - **C (Low Value)**: สินค้าทำเงินน้อย (สะสม 96-100%)
    """)
    
    df_abc = run_query("""
        SELECT p.product_name as "สินค้า", SUM(s.amount) as "ยอดขายรวม", cat.cat_name as "หมวดหมู่"
        FROM sales_history s
        JOIN products p ON s.product_id = p.product_id
        LEFT JOIN categories cat ON p.cat_id = cat.cat_id
        GROUP BY p.product_name, cat.cat_name
        ORDER BY "ยอดขายรวม" DESC
    """)
    
    if not df_abc.empty:
        total_rev = df_abc['ยอดขายรวม'].sum()
        df_abc['สัดส่วน (%)'] = (df_abc['ยอดขายรวม'] / total_rev * 100).round(2)
        df_abc['% สะสม'] = df_abc['สัดส่วน (%)'].cumsum()
        
        def assign_abc(x):
            if x <= 80: return "A"
            elif x <= 95: return "B"
            return "C"
        
        df_abc['Grade'] = df_abc['% สะสม'].apply(assign_abc)
        
        # Color Coding
        def color_abc(val):
            color = "#28a745" if val == "A" else "#ffc107" if val == "B" else "#dc3545"
            return f'color: {color}; font-weight: bold'
        
        c1, c2, c3 = st.columns(3)
        c1.metric("สินค้ากลุ่ม A (ตัวทำเงิน)", f"{len(df_abc[df_abc['Grade']=='A'])} รายการ")
        c2.metric("สินค้ากลุ่ม B (ปานกลาง)", f"{len(df_abc[df_abc['Grade']=='B'])} รายการ")
        c3.metric("สินค้ากลุ่ม C (สินค้านิ่ง)", f"{len(df_abc[df_abc['Grade']=='C'])} รายการ")
        
        st.dataframe(df_abc.style.applymap(color_abc, subset=['Grade']), use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อมูลเพียงพอสำหรับการวิเคราะห์")

# --- 💵 P&L Dashboard ---
elif choice == "💵 P&L Dashboard":
    st.header("💵 รายงานสรุปกำไร-ขาดทุน (P&L)")
    
    # ดึงยอดขายและส่วนลดจากตาราง bills (ข้อมูลจริงจากระบบใหม่)
    df_pl = run_query("""
        SELECT bill_id, total_amount, discount, final_amount, sale_date
        FROM bills
    """)
    
    if not df_pl.empty:
        df_pl['sale_date'] = pd.to_datetime(df_pl['sale_date']).dt.date
        
        # ตัวเลือกช่วงเวลา
        st.subheader("📊 วิเคราะห์กระแสรายได้")
        total_sales = df_pl['total_amount'].sum()
        total_disc = df_pl['discount'].sum()
        net_revenue = df_pl['final_amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("ยอดขายเบื้องต้น (Gross)", f"฿{total_sales:,.2f}")
        c2.metric("ส่วนลดที่ให้ลูกค้า", f"-฿{total_disc:,.2f}")
        c3.metric("รายได้สุทธิ (Net)", f"฿{net_revenue:,.2f}", delta=f"-{total_disc/total_sales*100:.1f}% Discount")
        
        st.divider()
        st.subheader("📝 รายละเอียดบิลรายวัน")
        st.dataframe(df_pl.sort_values('sale_date', ascending=False), hide_index=True, use_container_width=True)
    else:
        st.info("ระบบ P&L จะเริ่มแสดงผลเมื่อมีการสั่งซื้อผ่านระบบ 'บันทึกการขาย' ใหม่ครับ")

# --- 💰 บันทึกการขาย ---
elif choice == "💰 บันทึกการขาย":
    st.header("🛒 ระบบบันทึกการขาย (ตระกร้าสินค้า)")
    
    # Initialize Cart
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    
    df_p = run_query("SELECT p.product_id, p.product_name, p.price, p.cat_id, c.cat_name FROM products p LEFT JOIN categories c ON p.cat_id = c.cat_id")
    df_e = run_query("SELECT emp_id, emp_name, emp_nickname FROM employees")
    df_all_c = run_query("SELECT customer_id, full_name, nickname FROM customers")
    df_cat = run_query("SELECT * FROM categories")

    if df_all_c.empty or df_p.empty or df_e.empty:
        st.warning("⚠️ ข้อมูลไม่ครบ: กรุณาเพิ่ม ลูกค้า สินค้า และพนักงานก่อน")
    else:
        # 1. Customer & Seller Selection
        c1, c2 = st.columns(2)
        with c1:
            df_all_c['search_display'] = df_all_c.apply(lambda x: f"{x['customer_id']} | {x['full_name']} ({x['nickname'] or '-'})", axis=1)
            sel_cust = st.selectbox("👤 เลือกลูกค้า", ["-- เลือกรายชื่อลูกค้า --"] + df_all_c['search_display'].tolist(), key="sale_cust")
        with c2:
            df_e['disp'] = df_e['emp_nickname'].fillna(df_e['emp_name'])
            sel_emp = st.selectbox("👔 พนักงานผู้ขาย", ["-- เลือกพนักงาน --"] + df_e['disp'].tolist(), key="sale_emp")
        
        st.divider()
        
        # 2. Package Selector
        df_pkg = run_query("SELECT * FROM packages")
        if not df_pkg.empty:
            with st.expander("🎁 เลือกจากหลักสูตร/แพ็กเกจ (Bundles)", expanded=False):
                pkg_opts = ["-- เลือกแพ็กเกจ --"] + [f"{r['package_id']} | {r['package_name']} ({r['discounted_price']:,.0f} บ.)" for _, r in df_pkg.iterrows()]
                sel_pkg_sale = st.selectbox("เลือกหลักสูตรที่ต้องการขาย", pkg_opts)
                if sel_pkg_sale != "-- เลือกแพ็กเกจ --":
                    if st.button("🚀 โหลดรายการแพ็กเกจลงตระกร้า", use_container_width=True):
                        pid = int(sel_pkg_sale.split(" | ")[0])
                        pkg_info = df_pkg[df_pkg['package_id'] == pid].iloc[0]
                        # Fetch items
                        df_pkg_items = run_query("""
                            SELECT p.product_id, p.product_name, p.price 
                            FROM package_products pp
                            JOIN products p ON pp.product_id = p.product_id
                            WHERE pp.package_id = :id
                        """, {"id": pid})
                        
                        # Clear and load
                        st.session_state.cart = []
                        it_total = 0
                        for _, pit in df_pkg_items.iterrows():
                            st.session_state.cart.append({
                                "id": int(pit['product_id']),
                                "name": pit['product_name'],
                                "price": float(pit['price']),
                                "qty": 1,
                                "total": float(pit['price']),
                                "is_course": True
                            })
                            it_total += pit['price']
                        
                        # Add adjustment to reach discounted price
                        adj = float(pkg_info['discounted_price']) - it_total
                        st.session_state.cart.append({
                            "id": 0, # Virtual ID
                            "name": f"ส่วนลดแพ็กเกจ: {pkg_info['package_name']}",
                            "price": adj,
                            "qty": 1,
                            "total": adj,
                            "is_course": False
                        })
                        st.rerun()

        # 3. Add to Cart Section
        with st.expander("➕ เพิ่มสินค้าลงตระกร้า", expanded=True):
            # Category filter first (Mandatory)
            cat_list = ["-- เลือกหมวดหมู่สินค้า --"] + sorted(df_cat['cat_name'].tolist())
            sel_cat_sale = st.selectbox("📂 ขั้นตอนที่ 1: เลือกหมวดหมู่สินค้า", cat_list)
            
            if sel_cat_sale != "-- เลือกหมวดหมู่สินค้า --":
                df_p_filtered = df_p[df_p['cat_name'] == sel_cat_sale].copy()
                
                if not df_p_filtered.empty:
                    # Create a searchable display string: [ID: 101] Product Name - 500.00 บ.
                    df_p_filtered['search_str'] = df_p_filtered.apply(lambda x: f"[ID: {x['product_id']}] {x['product_name']} - {x['price']:,.2f} บ.", axis=1)
                    
                    ac1, ac2, ac3 = st.columns([3, 1, 1])
                    prod_sel_str = ac1.selectbox("📂 ขั้นตอนที่ 2: เลือกสินค้า (ค้นหาได้จากชื่อ หรือ ID)", 
                                                 ["-- ค้นหาและเลือกสินค้า --"] + df_p_filtered['search_str'].tolist())
                    
                    if prod_sel_str != "-- ค้นหาและเลือกสินค้า --":
                        qty_to_add = ac2.number_input("จำนวน", min_value=1, value=1)
                        if ac3.button("➕ เพิ่มลงตระกร้า", use_container_width=True, type="secondary"):
                            # Find the info back from the selected search string
                            p_info = df_p_filtered[df_p_filtered['search_str'] == prod_sel_str].iloc[0]
                            st.session_state.cart.append({
                                "id": int(p_info['product_id']),
                                "name": p_info['product_name'],
                                "price": float(p_info['price']),
                                "qty": qty_to_add,
                                "total": float(p_info['price'] * qty_to_add),
                                "is_course": True # Courses by default
                            })
                            st.rerun()
                else:
                    st.info("❌ ไม่พบสินค้าในหมวดหมู่นี้")
            else:
                st.info("💡 โปรดเลือกหมวดหมู่สินค้าด้านบนเพื่อดูรายการสินค้า")

        # 3. Cart Display
        if st.session_state.cart:
            st.subheader("📋 รายการในตระกร้า")
            df_cart = pd.DataFrame(st.session_state.cart)
            
            # Display items with remove buttons
            for i, item in enumerate(st.session_state.cart):
                cols = st.columns([3, 1, 1, 1, 0.5])
                cols[0].write(item['name'])
                cols[1].write(f"{item['price']:,.2f}")
                cols[2].write(f"x {item['qty']}")
                cols[3].write(f"**{item['total']:,.2f}**")
                # cols[4].checkbox("🎓", value=item.get('is_course', False), key=f"cr_{i}") # Credit toggle?
                if cols[4].button("❌", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            subtotal = sum(item['total'] for item in st.session_state.cart)
            
            st.divider()
            
            # 4. Checkout
            cc1, cc2, cc3 = st.columns(3)
            discount_pct = cc1.number_input("📉 ส่วนลด (%)", min_value=0.0, max_value=100.0, value=0.0)
            pay_method = cc2.selectbox("💳 วิธีชำระเงิน", ["โอนเงิน", "เงินสด"])
            
            # Updated to match Marketing Channels
            mkt_channels = ["Facebook Ads", "Google Ads", "TikTok Ads", "Line OA", "Openhouse", "โรงเรียนอนุบาล", "ลูกค้าเก่า/Re-sale", "อื่นๆ"]
            sel_mkt_channel = cc3.selectbox("📡 ช่องทางที่มา", mkt_channels)
            
            discount_amt = (subtotal * discount_pct) / 100
            final_total = subtotal - discount_amt
            
            if discount_pct > 0:
                st.markdown(f"💰 ส่วนลดที่ได้รับ ({discount_pct}%): **-{discount_amt:,.2f}** บาท")
            
            st.markdown(f"### ยอดรวมสุทธิ: :red[{final_total:,.2f}] บาท")
            
            if st.button("🏁 ยืนยันการสั่งซื้อและออกบิล", use_container_width=True, type="primary"):
                if sel_cust != "-- เลือกรายชื่อลูกค้า --" and sel_emp != "-- เลือกพนักงาน --":
                    # Generate Bill ID: B-YYYYMMDD-XXXX
                    now = datetime.now()
                    prefix = f"B-{now.strftime('%Y%m%d')}"
                    last_bill = run_query("SELECT bill_id FROM bills WHERE bill_id LIKE :pref ORDER BY bill_id DESC LIMIT 1", {"pref": f"{prefix}%"})
                    if not last_bill.empty:
                        last_num = int(last_bill['bill_id'][0].split('-')[-1])
                        new_bill_id = f"{prefix}-{str(last_num + 1).zfill(4)}"
                    else:
                        new_bill_id = f"{prefix}-0001"
                    
                    c_id = int(sel_cust.split(" | ")[0])
                    e_id = int(df_e[df_e['disp'] == sel_emp]['emp_id'].values[0])
                    
                    # Save Bill header (Including sale_channel)
                    run_query("""
                        INSERT INTO bills (bill_id, customer_id, seller_id, total_amount, discount, final_amount, payment_method, sale_channel)
                        VALUES (:bid, :cid, :sid, :total, :disc, :final, :pay, :chan)
                    """, {"bid": new_bill_id, "cid": c_id, "sid": e_id, "total": subtotal, "disc": discount_amt, "final": final_total, "pay": pay_method, "chan": sel_mkt_channel})
                    
                    # Save Bill items
                    for item in st.session_state.cart:
                        run_query("""
                            INSERT INTO bill_items (bill_id, product_id, product_name, qty, unit_price, subtotal)
                            VALUES (:bid, :pid, :pname, :qty, :uprice, :sub)
                        """, {"bid": new_bill_id, "pid": item['id'], "pname": item['name'], "qty": item['qty'], "uprice": item['price'], "sub": item['total']})
                        
                        # If it's a course item, generate Course Credits
                        if item.get('is_course') and item['id'] > 0:
                            import datetime as dt
                            exp_date = (datetime.now() + dt.timedelta(days=730)).date() # 2 Years approx
                            for _ in range(item['qty']):
                                run_query("""
                                    INSERT INTO course_credits (customer_id, bill_id, product_id, expiry_date)
                                    VALUES (:cid, :bid, :pid, :exp)
                                """, {"cid": c_id, "bid": new_bill_id, "pid": item['id'], "exp": exp_date})

                        # Legacy support
                        run_query("""
                            INSERT INTO sales_history (customer_id, product_id, amount, payment_method, sale_channel, closed_by_emp_id, sale_date)
                            VALUES (:cid, :pid, :amt, :pay, :ch, :eid, :dt)
                        """, {"cid": c_id, "pid": item['id'], "amt": item['total'], "pay": pay_method, "ch": sel_mkt_channel, "eid": e_id, "dt": now.date()})
                    
                    st.success(f"✅ บันทึกบิล {new_bill_id} สำเร็จ!")
                    
                    # --- Receipt Generation ---
                    c_name = sel_cust.split(" | ")[1]
                    s_name = sel_emp
                    
                    receipt_html = f"""
                    <div style="font-family: 'Courier New', Courier, monospace; border: 1px solid #ccc; padding: 20px; width: 300px; margin: auto; background: white; color: black;" id="receipt">
                        <h3 style="text-align: center; margin-bottom: 5px;">RECEIPT</h3>
                        <p style="text-align: center; font-size: 12px; margin-top: 0;">CRM Smart Pro System</p>
                        <hr>
                        <p style="font-size: 14px;"><b>Bill ID:</b> {new_bill_id}<br>
                        <b>Date:</b> {now.strftime('%d/%m/%Y %H:%M')}<br>
                        <b>Customer:</b> {c_name}<br>
                        <b>Seller:</b> {s_name}</p>
                        <hr>
                        <table style="width: 100%; font-size: 14px;">
                    """
                    for item in st.session_state.cart:
                        receipt_html += f"<tr><td>{item['name']} x{item['qty']}</td><td style='text-align: right;'>{item['total']:,.2f}</td></tr>"
                    
                    receipt_html += f"""
                        </table>
                        <hr>
                        <table style="width: 100%; font-size: 14px;">
                            <tr><td>Subtotal:</td><td style='text-align: right;'>{subtotal:,.2f}</td></tr>
                            <tr><td>Discount ({discount_pct}%):</td><td style='text-align: right;'>-{discount_amt:,.2f}</td></tr>
                            <tr style='font-weight: bold;'><td>TOTAL:</td><td style='text-align: right;'>{final_total:,.2f}</td></tr>
                        </table>
                        <p style="font-size: 14px;"><b>Method:</b> {pay_method}</p>
                        <hr>
                        <p style="text-align: center; font-size: 12px;">Thank you for your business!</p>
                    </div>
                    <br>
                    <script>
                        function printDiv() {{
                            var content = document.getElementById('receipt').outerHTML;
                            var win = window.open('', '', 'height=500,width=500');
                            win.document.write('<html><head><title>Print Receipt</title></head><body>');
                            win.document.write(content);
                            win.document.write('</body></html>');
                            win.document.close();
                            win.print();
                        }}
                    </script>
                    """
                    
                    st.markdown(receipt_html, unsafe_allow_html=True)
                    if st.button("🖨️ พิมพ์ใบเสร็จ (Print)"):
                        st.write("กรุณากด Ctrl+P เพื่อพิมพ์หน้าจอนี้ (หรือส่งข้อมูลไปที่เครื่องพิมพ์)")

                    st.session_state.cart = [] # Clear cart after success
                    if st.button("🔄 เริ่มบันทึกบิลใหม่"):
                        st.rerun()

                else:
                    st.error("⚠️ กรุณาเลือกทั้งลูกค้าและพนักงาน")
        else:
            st.info("🛒 ตระกร้าว่างเปล่า: กรุณาเพิ่มสินค้าเพื่อเริ่มบันทึกการขาย")

# --- 👥 จัดการลูกค้า (Customer 360) ---
elif choice == "👥 จัดการลูกค้า":
    st.header("👥 Customer Management 360°")
    
    df_all_c = run_query("SELECT * FROM customers")
    
    # 1. Selection State
    if not df_all_c.empty:
        c_opts = ["➕ ลงทะเบียนลูกค้าใหม่"] + [f"{r['customer_id']} | {r['full_name']}" for _, r in df_all_c.iterrows()]
        sel_c_idx = 0
        if 'last_selected_cust' in st.session_state and st.session_state.last_selected_cust in c_opts:
            sel_c_idx = c_opts.index(st.session_state.last_selected_cust)
        
        sel_edit_c = st.selectbox("🔍 ค้นหาและเลือกลูกค้า", c_opts, index=sel_c_idx, key="cust_selector")
        st.session_state.last_selected_cust = sel_edit_c
    else:
        st.info("ยังไม่มีข้อมูลลูกค้า")
        sel_edit_c = "➕ ลงทะเบียนลูกค้าใหม่"

    # --- Mode: New Customer ---
    if sel_edit_c == "➕ ลงทะเบียนลูกค้าใหม่":
        st.subheader("📝 ลงทะเบียนลูกค้าใหม่")
        with st.form("new_cust_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("ชื่อ-นามสกุลจริง *")
            nick = c2.text_input("ชื่อเล่น")
            phone = c1.text_input("เบอร์โทรศัพท์")
            line = c2.text_input("LINE ID")
            birth = c1.date_input("วันเกิด (Birth Date)", value=None, min_value=datetime(1950, 1, 1), max_value=datetime.now())
            gender = c2.selectbox("เพศ", ["ชาย", "หญิง", "อื่นๆ", "ไม่ระบุ"])
            
            addr = st.text_area("ที่อยู่จัดส่ง")
            prov = st.selectbox("จังหวัด", ["-- โปรดเลือก --"] + sorted(list(LOCATION_DATA.keys())))
            
            sub_btn = st.form_submit_button("💾 บันทึกข้อมูลลูกค้าใหม่", use_container_width=True, type="primary")
            if sub_btn and name:
                check = run_query("SELECT COUNT(*) as cnt FROM customers WHERE full_name = :name", {"name": name})
                if check['cnt'][0] == 0:
                    run_query("""
                        INSERT INTO customers (full_name, nickname, phone, line_id, birth_date, gender, address_detail, province)
                        VALUES (:name, :nick, :phone, :line, :birth, :gender, :addr, :prov)
                    """, {"name": name, "nick": nick, "phone": phone, "line": line, "birth": birth, "gender": gender, "addr": addr, "prov": prov})
                    st.success("บันทึกเรียบร้อย!")
                    st.rerun()
                else:
                    st.error("ชื่อซ้ำในระบบ")

    # --- Mode: Existing Customer (360 View) ---
    else:
        cid = int(sel_edit_c.split(" | ")[0])
        cust = df_all_c[df_all_c['customer_id'] == cid].iloc[0]
        
        # Calculate Age
        age_str = "-"
        if pd.notnull(cust['birth_date']):
            # If it's a string, try parse
            if isinstance(cust['birth_date'], str):
                bdate = datetime.strptime(cust['birth_date'], "%Y-%m-%d").date()
            else:
                bdate = cust['birth_date']
            today = datetime.now().date()
            age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
            age_str = f"{age} ปี"

        # Calculate Financial Metrics
        fin_stats = run_query("""
            SELECT 
                COUNT(bill_id) as total_bills,
                SUM(final_amount) as total_spend,
                MAX(sale_date) as last_purchase
            FROM bills WHERE customer_id = :cid
        """, {"cid": cid})
        
        total_spend = fin_stats['total_spend'][0] or 0.0
        total_bills = fin_stats['total_bills'][0] or 0
        last_date = fin_stats['last_purchase'][0]
        
        # Monthly Spend
        now = datetime.now()
        cur_month_spend = run_query("""
            SELECT SUM(final_amount) as m_spend FROM bills 
            WHERE customer_id = :cid AND EXTRACT(MONTH FROM sale_date) = :m AND EXTRACT(YEAR FROM sale_date) = :y
        """, {"cid": cid, "m": now.month, "y": now.year})['m_spend'][0] or 0.0

        # --- Tab Layout ---
        t_profile, t_history, t_edit = st.tabs(["👤 โปรไฟล์ & ภาพรวม", "🎒 ประวัติ & สิทธิ์เรียน", "⚙️ แก้ไขข้อมูล"])
        
        with t_profile:
            # Header Info
            h1, h2, h3, h4 = st.columns(4)
            h1.metric("ชื่อลูกค้า", f"{cust['full_name']} ({cust['nickname'] or '-'})")
            h2.metric("อายุ", age_str)
            h3.metric("จังหวัด", cust['province'] or "-")
            h4.metric("สถานะสมาชิก", "Active", delta="Verified")
            
            st.divider()
            
            # Financial Metrics Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 ยอดใช้จ่ายรวม (LTV)", f"฿{total_spend:,.0f}")
            m2.metric("💸 ยอดเดือนนี้", f"฿{cur_month_spend:,.0f}")
            m3.metric("🛍️ จำนวนบิลซื้อ", f"{total_bills} ครั้ง")
            m4.metric("📅 ซื้อล่าสุดเมื่อ", last_date.strftime("%d/%m/%Y") if pd.notnull(last_date) else "-")
            
            st.info(f"📝 **หมายเหตุ:** {cust['cust_note'] or '-'}")

        with t_history:
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("🎓 คอร์สเรียนคงเหลือ")
                df_credits = run_query("""
                    SELECT cc.credit_id, p.product_name, cc.expiry_date, cc.status
                    FROM course_credits cc
                    JOIN products p ON cc.product_id = p.product_id
                    WHERE cc.customer_id = :cid
                    ORDER BY cc.status, cc.expiry_date
                """, {"cid": cid})
                
                if not df_credits.empty:
                    for _, row in df_credits.iterrows():
                        with st.container(border=True):
                            sc1, sc2 = st.columns([3, 1])
                            sc1.markdown(f"**{row['product_name']}**")
                            sc1.caption(f"หมดอายุ: {row['expiry_date']}")
                            if row['status'] == 'Available':
                                if sc2.button("เช็กอิน", key=f"chk_{row['credit_id']}"):
                                    run_query("UPDATE course_credits SET status='Used' WHERE credit_id=:id", {"id": row['credit_id']})
                                    st.success("Check-in!")
                                    st.rerun()
                            else:
                                sc2.success("ใช้แล้ว")
                else:
                    st.info("ไม่มีคอร์สค้างในระบบ")

            with c2:
                st.subheader("📜 ประวัติการสั่งซื้อ")
                df_hist = run_query("SELECT bill_id, sale_date, final_amount, payment_method FROM bills WHERE customer_id=:cid ORDER BY sale_date DESC", {"cid": cid})
                st.dataframe(df_hist, hide_index=True, use_container_width=True, 
                             column_config={"final_amount": st.column_config.NumberColumn("ยอดเงิน", format="฿%,.2f"), "sale_date": st.column_config.DatetimeColumn("วันที่", format="DD/MM/YYYY")})

        with t_edit:
            with st.form("edit_cust_form"):
                ec1, ec2 = st.columns(2)
                
                # Left Column: Contact & Personal
                ename = ec1.text_input("ชื่อจริง", value=cust['full_name'])
                enick = ec2.text_input("ชื่อเล่น", value=cust['nickname'] or "")
                
                # Prepare Date Value
                b_val = None
                if pd.notnull(cust['birth_date']):
                    if isinstance(cust['birth_date'], str):
                        try:
                            b_val = datetime.strptime(cust['birth_date'], "%Y-%m-%d")
                        except ValueError:
                            b_val = None
                    else:
                        b_val = cust['birth_date']

                ebirth = ec1.date_input("วันเกิด", value=b_val)
                egender = ec2.selectbox("เพศ", ["ชาย", "หญิง", "อื่นๆ"], index=["ชาย", "หญิง", "อื่นๆ"].index(cust['gender']) if cust['gender'] in ["ชาย", "หญิง", "อื่นๆ"] else 0)
                
                ephone = ec1.text_input("เบอร์โทร", value=cust['phone'] or "")
                eline = ec2.text_input("Line ID", value=cust['line_id'] or "")
                
                efb = ec1.text_input("Facebook", value=cust['facebook'] or "")
                eig = ec2.text_input("Instagram", value=cust['instagram'] or "")

                # Address Section
                eaddr = st.text_area("ที่อยู่", value=cust['address_detail'] or "")
                eprov = st.selectbox("จังหวัด", ["--"] + sorted(list(LOCATION_DATA.keys())), index=(sorted(list(LOCATION_DATA.keys())).index(cust['province']) + 1) if cust['province'] in LOCATION_DATA else 0)
                
                # Family & Status
                st.divider()
                fc1, fc2 = st.columns(2)
                emarital = fc1.selectbox("สถานะภาพ", ["โสด", "แต่งงานแล้ว", "หย่าร้าง"], index=["โสด", "แต่งงานแล้ว", "หย่าร้าง"].index(cust['marital_status']) if cust['marital_status'] in ["โสด", "แต่งงานแล้ว", "หย่าร้าง"] else 0)
                echildren = fc2.selectbox("มีบุตร", ["ไม่มี", "มีแล้ว"], index=["ไม่มี", "มีแล้ว"].index(cust['has_children']) if cust['has_children'] in ["ไม่มี", "มีแล้ว"] else 0)
                
                enote = st.text_area("Note", value=cust['cust_note'] or "")
                
                if st.form_submit_button("💾 บันทึกการแก้ไข", type="primary"):
                    run_query("""
                        UPDATE customers SET 
                        full_name=:n, nickname=:nn, birth_date=:b, gender=:g, 
                        phone=:p, line_id=:l, facebook=:fb, instagram=:ig,
                        address_detail=:a, province=:pv, marital_status=:m, has_children=:c,
                        cust_note=:nt 
                        WHERE customer_id=:cid
                    """,
                    {"n": ename, "nn": enick, "b": ebirth, "g": egender, 
                     "p": ephone, "l": eline, "fb": efb, "ig": eig,
                     "a": eaddr, "pv": eprov, "m": emarital, "c": echildren,
                     "nt": enote, "cid": cid})
                    st.success("บันทึกข้อมูลเรียบร้อย!")
                    st.rerun()
                
                st.divider()
                if st.form_submit_button("🗑️ ลบข้อมูลลูกค้านี้"):
                    run_query("DELETE FROM customers WHERE customer_id=:id", {"id": cid})
                    st.session_state.last_selected_cust = None
                    st.warning("ลบข้อมูลแล้ว")
                    st.rerun()


# --- 👔 จัดการพนักงาน ---
# --- 👔 จัดการพนักงาน ---
elif choice == "👔 จัดการพนักงาน":
    st.header("👔 การจัดการพนักงาน")
    
    tab_list, tab_kpi, tab_new = st.tabs(["📋 รายชื่อพนักงาน", "🏆 Performance (KPI)", "➕ เพิ่มพนักงานใหม่"])
    
    # Tab 1: List (Existing Logic)
    with tab_list:
        st.subheader("📋 รายชื่อพนักงานทั้งหมด")
        search_e = st.text_input("🔍 ค้นหาพนักงาน", placeholder="พิมพ์ชื่อพนักงานที่นี่...")
        
        df_e = run_query("SELECT * FROM employees")
        if not df_e.empty:
            if search_e:
                df_fe = df_e[df_e['emp_name'].str.contains(search_e, case=False, na=False) | 
                             df_e['emp_nickname'].str.contains(search_e, case=False, na=False)]
            else:
                df_fe = df_e
            
            st.dataframe(df_fe[["emp_id", "emp_name", "emp_nickname", "position"]], 
                         hide_index=True, use_container_width=True,
                         column_config={"emp_id": "ID", "emp_name": "ชื่อจริง", "emp_nickname": "ชื่อเล่น", "position": "ตำแหน่ง"})
            
            # Simple Edit/Delete (Keep existing hidden or simple for now as requested focus is KPI)
            with st.expander("🛠️ แก้ไข/ลบ พนักงาน"):
                esel = st.selectbox("เลือกพนักงาน", [f"{r['emp_id']} | {r['emp_nickname']}" for _, r in df_fe.iterrows()])
                if esel:
                    eid_sel = int(esel.split(" | ")[0])
                    if st.button("🗑️ ลบพนักงานคนนี้", key="del_emp"):
                        run_query("DELETE FROM employees WHERE emp_id=:id", {"id": eid_sel})
                        st.success("Deleted")
                        st.rerun()

    # Tab 2: KPI Dashboard (New Feature)
    with tab_kpi:
        st.subheader("🏆 Employee Performance Dashboard")
        
        # 1. Date Filter
        k_period = st.radio("ช่วงเวลา:", ["วันนี้ (Today)", "สัปดาห์นี้ (This Week)", "เดือนนี้ (This Month)"], horizontal=True)
        
        now = datetime.now()
        start_date = now.date()
        
        if "สัปดาห์" in k_period:
            start_date = now.date() - timedelta(days=now.weekday()) # Monday
        elif "เดือน" in k_period:
            start_date = now.date().replace(day=1)
            
        st.info(f"📊 แสดงข้อมูลตั้งแต่วันที่: **{start_date.strftime('%d/%m/%Y')} - ปัจจุบัน**")
        
        # 2. Query Data
        kpi_sql = """
            SELECT e.emp_name, e.emp_nickname, SUM(b.final_amount) as total_sales, COUNT(b.bill_id) as bill_count
            FROM bills b
            JOIN employees e ON b.emp_name = e.emp_nickname -- Focusing on nickname as stored in bills
            WHERE b.sale_date >= :sd
            GROUP BY e.emp_name, e.emp_nickname
            ORDER BY total_sales DESC
        """
        # Note: In bills table we stored 'Seller Name' which comes from session state (nickname). 
        # Ideally should join by ID but current system uses nickname string.
        
        # Fallback to string matching if ID not stored in bills (legacy check)
        # Checking schema: bills has no emp_id column in current view, it stores seller_name in text? 
        # Looking at receipt generation: s_name = sel_emp (which is nickname usually).
        # Let's verify bills schema or data. Assuming 'sale_channel' or similar. 
        # Actually in `bills` table creation earlier: 
        # CREATE TABLE IF NOT EXISTS bills (..., emp_name TEXT, ...) -> yes, stores name.
        
        # 2. Query Data
        
        # Correct Query: Join bills with employees using seller_id
        df_kpi = run_query(f"""
            SELECT e.emp_name, COUNT(b.bill_id) as bills, SUM(b.final_amount) as sales 
            FROM bills b
            JOIN employees e ON b.seller_id = e.emp_id
            WHERE date(b.sale_date) >= '{start_date}'
            GROUP BY e.emp_name
            ORDER BY sales DESC
        """)
        
        if not df_kpi.empty:
            # 3. Leaderboard Chart
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("#### 🥇 Sales Leaderboard")
                st.bar_chart(df_kpi.set_index('emp_name')['sales'], color="#F59E0B", use_container_width=True)
            
            with c2:
                st.markdown("#### 🔢 Statistics")
                df_kpi['AVG Ticket'] = df_kpi['sales'] / df_kpi['bills']
                st.dataframe(df_kpi, hide_index=True, 
                             column_config={
                                 "emp_name": "พนักงาน",
                                 "sales": st.column_config.NumberColumn("ยอดขายรวม", format="฿%,.0f"),
                                 "bills": "บิล",
                                 "AVG Ticket": st.column_config.NumberColumn("เฉลี่ย/บิล", format="฿%,.0f")
                             })

            st.divider()
            
            # 4. Top 3 Products per Employee
            st.subheader("📦 Top 3 Best Selling Products by Employee")
            
            # Get details
            df_prods = run_query(f"""
                SELECT e.emp_name, p.product_name, SUM(bi.subtotal) as p_total
                FROM bill_items bi
                JOIN bills b ON bi.bill_id = b.bill_id
                JOIN employees e ON b.seller_id = e.emp_id
                JOIN products p ON bi.product_id = p.product_id
                WHERE date(b.sale_date) >= '{start_date}'
                GROUP BY e.emp_name, p.product_name
                ORDER BY e.emp_name, p_total DESC
            """)
            
            if not df_prods.empty:
                # Group and display
                emps = df_prods['emp_name'].unique()
                cols = st.columns(3)
                for i, emp in enumerate(emps):
                    with cols[i % 3]:
                        with st.container(border=True):
                            st.markdown(f"**🧑‍💼 {emp}**")
                            top3 = df_prods[df_prods['emp_name'] == emp].head(3)
                            for _, r in top3.iterrows():
                                st.write(f"- {r['product_name']} (฿{r['p_total']:,.0f})")
            else:
                st.info("ไม่มีข้อมูลสินค้า")
        else:
            st.warning("ไม่มีข้อมูลการขายในช่วงเวลานี้")

    # Tab 3: Add New (Placeholder for future)
    with tab_new:
        st.info("ฟีเจอร์เพิ่มพนักงานใหม่อยู่ที่หน้านี้ (ยังไม่ได้ย้ายมาจากเวอร์ชั่นเก่า - ใช้ SQL Insert ชั่วคราวได้)")
        # We can add simple add form here if desired, but user focused on KPI.
        with st.form("add_emp"):
             n = st.text_input("ชื่อจริง (Full Name)")
             nn = st.text_input("ชื่อเล่น (Nickname)")
             pos = st.text_input("ตำแหน่ง")
             if st.form_submit_button("เพิ่มพนักงาน"):
                 run_query("INSERT INTO employees (emp_name, emp_nickname, position) VALUES (:n, :nn, :p)", {"n": n, "nn": nn, "p": pos})
                 st.success("Added")
                 st.rerun()

        

# --- 📦 จัดการสินค้า ---
elif choice == "📦 จัดการสินค้า":
    st.header("📦 คลังสินค้า")
    
    df_p = run_query("SELECT p.product_id, p.product_name, c.cat_name, p.price, p.cat_id FROM products p LEFT JOIN categories c ON p.cat_id = c.cat_id")
    
    if not df_p.empty:
        p_opts = ["➕ เพิ่มสินค้าใหม่"] + [f"{r['product_id']} | {r['product_name']}" for _, r in df_p.iterrows()]
        sel_edit_p = st.selectbox("📝 เลือกสินค้าเพื่อ แก้ไข หรือ ลบข้อมูล", p_opts)
    else:
        st.info("ยังไม่มีข้อมูลสินค้า")
        sel_edit_p = "➕ เพิ่มสินค้าใหม่"

    edit_mode = False
    edit_id = None
    curr_data = {}
    
    if sel_edit_p != "➕ เพิ่มสินค้าใหม่":
        edit_mode = True
        edit_id = int(sel_edit_p.split(" | ")[0])
        curr_data = df_p[df_p['product_id'] == edit_id].iloc[0].to_dict()

    with st.expander("📝 ฟอร์มข้อมูลสินค้า", expanded=True):
        c1, c2, c3 = st.columns(3)
        form_key_suffix = str(edit_id) if edit_mode else "new"
        pn = c1.text_input("ชื่อสินค้า", value=curr_data.get('product_name', "") or "", key=f"p_name_{form_key_suffix}")
        
        df_cat = run_query("SELECT * FROM categories")
        cat_list = df_cat['cat_name'].tolist() if not df_cat.empty else ["-"]
        cat_idx = 0
        if edit_mode and curr_data.get('cat_name') in cat_list:
            cat_idx = cat_list.index(curr_data.get('cat_name'))
            
        pc = c2.selectbox("หมวดหมู่", cat_list, index=cat_idx, key=f"p_cat_{form_key_suffix}")
        pr = c3.number_input("ราคา", min_value=0.0, value=float(curr_data.get('price', 0.0) or 0.0), key=f"p_price_{form_key_suffix}")
        
        btn_label = "💾 บันทึกการแก้ไข" if edit_mode else "💾 บันทึกสินค้าใหม่"
        bc1, bc2 = st.columns([1, 1])
        
        if bc1.button(btn_label, use_container_width=True, type="primary"):
            if pn and not df_cat.empty:
                try:
                    cat_id = int(df_cat[df_cat['cat_name'] == pc]['cat_id'].values[0])
                    if edit_mode:
                        run_query("UPDATE products SET product_name=:name, cat_id=:cat, price=:price WHERE product_id=:id", 
                                  {"name": pn, "cat": cat_id, "price": pr, "id": edit_id})
                        st.success(f"✅ อัปเดต {pn} สำเร็จ!")
                    else:
                        run_query("INSERT INTO products (product_name, cat_id, price) VALUES (:name, :cat, :price)", 
                                  {"name": pn, "cat": cat_id, "price": pr})
                        st.success(f"✅ เพิ่ม {pn} สำเร็จ!")
                    st.rerun()
                except Exception: st.error("❌ เกิดข้อผิดพลาด (อาจมีชื่อซ้ำ)")
        
        if edit_mode:
            if bc2.button("🗑️ ลบสินค้านี้", use_container_width=True):
                run_query("DELETE FROM products WHERE product_id = :id", {"id": edit_id})
                st.warning(f"ลบสินค้า {pn} เรียบร้อย")
                st.rerun()

    st.divider()
    st.subheader("📋 รายการสินค้าทั้งหมด")
    search_p = st.text_input("🔍 ค้นหาสินค้า", placeholder="พิมพ์ชื่อสินค้าที่นี่...")
    if not df_p.empty:
        if search_p:
            df_fp = df_p[df_p['product_name'].str.contains(search_p, case=False, na=False)]
        else:
            df_fp = df_p
        
        st.dataframe(df_fp[["product_id", "product_name", "cat_name", "price"]], 
                     hide_index=True, use_container_width=True,
                     column_config={"product_id": "ID", "product_name": "ชื่อสินค้า", "cat_name": "หมวดหมู่", "price": "ราคา"})

# --- ⚙️ ตั้งค่าระบบ ---
elif choice == "⚙️ ตั้งค่าระบบ":
    st.header("⚙️ ตั้งค่าระบบและตัวเลือกพื้นฐาน")
    
    t1, t2 = st.tabs(["📁 หมวดหมู่สินค้า", "👔 ตำแหน่งพนักงาน"])
    with t1:
        df_c = run_query("SELECT * FROM categories")
        cat_opts = ["➕ เพิ่มหมวดหมู่ใหม่"] + [f"{r['cat_id']} | {r['cat_name']}" for _, r in df_c.iterrows()]
        sel_cat = st.selectbox("🔍 เลือกหมวดหมู่ที่ต้องการแก้ไข", cat_opts)
        
        edit_c_mode = False
        edit_c_id = None
        curr_cat_name = ""
        if sel_cat != "➕ เพิ่มหมวดหมู่ใหม่":
            edit_c_mode = True
            edit_c_id = int(sel_cat.split(" | ")[0])
            row = df_c[df_c['cat_id'] == edit_c_id].iloc[0]
            curr_cat_name = row['cat_name']
            curr_grp_name = row['group_name']
            
        with st.form("cat_form", clear_on_submit=True):
            nc = st.text_input("ชื่อหมวดหมู่", value=curr_cat_name)
            ng = st.selectbox("กลุ่ม (Group)", ["Cooking Course", "Service", "Other"], 
                             index=["Cooking Course", "Service", "Other"].index(curr_grp_name) if edit_c_mode and curr_grp_name in ["Cooking Course", "Service", "Other"] else 2)
            cb1, cb2 = st.columns([1, 1])
            if cb1.form_submit_button("💾 บันทึก"):
                if nc:
                    if edit_c_mode:
                        run_query("UPDATE categories SET cat_name=:name, group_name=:grp WHERE cat_id=:id", {"name": nc, "grp": ng, "id": edit_c_id})
                    else:
                        run_query("INSERT INTO categories (cat_name, group_name) VALUES (:name, :grp)", {"name": nc, "grp": ng})
                    st.rerun()
            if edit_c_mode:
                if cb2.form_submit_button("🗑️ ลบ"):
                    run_query("DELETE FROM categories WHERE cat_id = :id", {"id": edit_c_id})
                    st.rerun()
        
        st.divider()
        st.subheader("📋 หมวดหมู่ทั้งหมด")
        if not df_c.empty:
            st.dataframe(df_c[["cat_id", "cat_name", "group_name"]], hide_index=True, use_container_width=True, 
                         column_config={"cat_id": "ID", "cat_name": "ชื่อหมวดหมู่", "group_name": "กลุ่ม"})
        else:
            st.info("ยังไม่มีหมวดหมู่")
    with t2:
        df_pos_set = run_query("SELECT * FROM job_positions")
        pos_opts = ["➕ เพิ่มตำแหน่งงานใหม่"] + [f"{r['pos_id']} | {r['pos_name']}" for _, r in df_pos_set.iterrows()]
        sel_pos = st.selectbox("🔍 เลือกตำแหน่งที่ต้องการแก้ไข", pos_opts)
        edit_p_mode = False
        edit_p_id = None
        curr_pos_name = ""
        if sel_pos != "➕ เพิ่มตำแหน่งงานใหม่":
            edit_p_mode = True
            edit_p_id = int(sel_pos.split(" | ")[0])
            curr_pos_name = df_pos_set[df_pos_set['pos_id'] == edit_p_id].iloc[0]['pos_name']
            
        with st.form("pos_form", clear_on_submit=True):
            np = st.text_input("ชื่อตำแหน่งงาน", value=curr_pos_name)
            pb1, pb2 = st.columns([1, 1])
            if pb1.form_submit_button("💾 บันทึก"):
                if np:
                    if edit_p_mode:
                        run_query("UPDATE job_positions SET pos_name=:name WHERE pos_id=:id", {"name": np, "id": edit_p_id})
                    else:
                        run_query("INSERT INTO job_positions (pos_name) VALUES (:name)", {"name": np})
                    st.rerun()
            if edit_p_mode:
                if pb2.form_submit_button("🗑️ ลบ"):
                    run_query("DELETE FROM job_positions WHERE pos_id = :id", {"id": edit_p_id})
                    st.rerun()
        
        st.divider()
        st.subheader("📋 ตำแหน่งงานทั้งหมด")
        if not df_pos_set.empty:
            st.dataframe(df_pos_set[["pos_id", "pos_name"]], hide_index=True, use_container_width=True, column_config={"pos_id": "ID", "pos_name": "ชื่อตำแหน่ง"})
        else:
            st.info("ยังไม่มีตำแหน่งงาน")


# --- 📊 Lead Funnel Dashboard (Mock) ---
elif choice == "📊 Lead Funnel":
    st.header("📊 Lead Funnel Dashboard")
    st.caption("🚧 ตัวอย่างข้อมูล (Mock Data) สำหรับการพรีเซ้นต์")
    
    # Sample Funnel Data
    funnel_data = pd.DataFrame({
        "ขั้นตอน": ["Lead ทั้งหมด", "สนใจ (Interested)", "ลงทะเบียน (Registered)", "จ่ายเงิน (Paid)"],
        "จำนวน": [500, 320, 150, 85],
        "อัตรา (%)": [100, 64, 30, 17]
    })
    
    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📥 Lead ทั้งหมด", "500 คน", "+12%")
    m2.metric("📝 ลงทะเบียน", "150 คน", "+8%")
    m3.metric("💰 ปิดการขาย", "85 คน", "+15%")
    m4.metric("📈 Conversion Rate", "17%", "+3%")
    
    st.divider()
    
    # Funnel Visualization
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📈 Funnel Chart")
        st.bar_chart(funnel_data.set_index("ขั้นตอน")["จำนวน"], color="#6366F1")
    
    with c2:
        st.subheader("📊 Conversion by Channel")
        channel_conv = pd.DataFrame({
            "Channel": ["Facebook Ads", "TikTok Ads", "Line OA", "Google Ads"],
            "Leads": [200, 150, 100, 50],
            "Paid": [40, 25, 15, 5],
            "Conv %": ["20%", "17%", "15%", "10%"]
        })
        st.dataframe(channel_conv, hide_index=True, use_container_width=True)


# --- 🔔 Follow-up System (Mock) ---
elif choice == "🔔 Follow-up System":
    st.header("🔔 Customer Follow-up System")
    st.caption("🚧 ตัวอย่างข้อมูล (Mock Data) สำหรับการพรีเซ้นต์")
    
    # Alert Summary
    a1, a2, a3 = st.columns(3)
    a1.metric("⏰ คอร์สใกล้หมดอายุ", "12 คน", delta="-3 จากสัปดาห์ก่อน")
    a2.metric("🔕 ลูกค้าห่างหาย (>60 วัน)", "28 คน", delta="+5")
    a3.metric("📞 รอติดตาม", "15 รายการ")
    
    st.divider()
    
    # Sample Alerts
    t1, t2 = st.tabs(["⏰ Course Credit Alert", "🔕 Churn Risk Alert"])
    
    with t1:
        credit_alerts = pd.DataFrame({
            "ลูกค้า": ["คุณสมศรี", "คุณวิชัย", "คุณแพร", "คุณเบล"],
            "คอร์ส": ["V-School Dance", "V-School Sing", "V-School Art", "V-School Music"],
            "หมดอายุ": ["2026-02-15", "2026-02-20", "2026-02-28", "2026-03-05"],
            "เหลืออีก": ["14 วัน", "19 วัน", "27 วัน", "32 วัน"],
            "สถานะ": ["🔴 เร่งด่วน", "🟡 เตือน", "🟢 ปกติ", "🟢 ปกติ"]
        })
        st.dataframe(credit_alerts, hide_index=True, use_container_width=True)
    
    with t2:
        churn_alerts = pd.DataFrame({
            "ลูกค้า": ["คุณมานี", "คุณปิติ", "คุณชูใจ"],
            "ซื้อล่าสุด": ["2025-11-15", "2025-10-20", "2025-09-01"],
            "ห่างหาย": ["78 วัน", "103 วัน", "153 วัน"],
            "ยอดใช้จ่ายรวม": ["฿45,000", "฿28,000", "฿120,000"],
            "ความเสี่ยง": ["🟡 ปานกลาง", "🔴 สูง", "🔴 สูงมาก"]
        })
        st.dataframe(churn_alerts, hide_index=True, use_container_width=True)
    
    st.divider()
    st.subheader("✅ To-Do List (Sales)")
    todos = pd.DataFrame({
        "งาน": ["โทรติดตาม คุณสมศรี", "ส่ง LINE คุณมานี", "เสนอโปรใหม่ คุณชูใจ"],
        "ประเภท": ["Credit Expiry", "Churn Risk", "Upsell"],
        "กำหนด": ["วันนี้", "พรุ่งนี้", "03/02/2026"],
        "พนักงาน": ["พี่หนิง", "พี่หนิง", "พี่บอส"]
    })
    st.dataframe(todos, hide_index=True, use_container_width=True)


# --- 💰 Channel ROI Tracker (Mock) ---
elif choice == "💰 Channel ROI":
    st.header("💰 Channel ROI Tracker")
    st.caption("🚧 ตัวอย่างข้อมูล (Mock Data) สำหรับการพรีเซ้นต์")
    
    # ROI Summary
    roi_data = pd.DataFrame({
        "Channel": ["Facebook Ads", "TikTok Ads", "Google Ads", "Line OA"],
        "ค่าโฆษณา": [50000, 30000, 20000, 10000],
        "ยอดขาย": [180000, 95000, 45000, 65000],
        "ROAS": [3.6, 3.17, 2.25, 6.5],
        "กำไร": [130000, 65000, 25000, 55000]
    })
    
    # Metrics
    total_spend = roi_data["ค่าโฆษณา"].sum()
    total_revenue = roi_data["ยอดขาย"].sum()
    total_roas = total_revenue / total_spend
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💵 ค่าโฆษณารวม", f"฿{total_spend:,.0f}")
    m2.metric("💰 ยอดขายรวม", f"฿{total_revenue:,.0f}")
    m3.metric("📈 ROAS เฉลี่ย", f"{total_roas:.2f}x")
    m4.metric("🏆 Channel ดีสุด", "Line OA", delta="6.5x ROAS")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 ROAS by Channel")
        st.bar_chart(roi_data.set_index("Channel")["ROAS"], color="#10B981")
    
    with c2:
        st.subheader("💵 Revenue vs Ad Spend")
        st.dataframe(roi_data, hide_index=True, use_container_width=True,
                     column_config={
                         "ค่าโฆษณา": st.column_config.NumberColumn(format="฿%,.0f"),
                         "ยอดขาย": st.column_config.NumberColumn(format="฿%,.0f"),
                         "กำไร": st.column_config.NumberColumn(format="฿%,.0f"),
                         "ROAS": st.column_config.NumberColumn(format="%.2fx")
                     })


# --- 🎯 Campaign Tracker (Mock) ---
elif choice == "🎯 Campaign Tracker":
    st.header("🎯 Campaign Tracker")
    st.caption("🚧 ตัวอย่างข้อมูล (Mock Data) สำหรับการพรีเซ้นต์")
    
    # Campaign Summary
    m1, m2, m3 = st.columns(3)
    m1.metric("🏷️ แคมเปญที่กำลังรัน", "3 แคมเปญ")
    m2.metric("💰 ยอดขายจากแคมเปญ", "฿385,000", "+22%")
    m3.metric("🎯 แคมเปญดีสุด", "Summer Sale 2026")
    
    st.divider()
    
    # Campaign Table
    st.subheader("📋 รายการแคมเปญ")
    campaigns = pd.DataFrame({
        "แคมเปญ": ["☀️ Summer Sale 2026", "🎒 Back to School", "🎄 New Year Promo", "💝 Valentine Special"],
        "สถานะ": ["🟢 Active", "🟢 Active", "⚫ Ended", "🟡 Scheduled"],
        "ระยะเวลา": ["01-28 Feb 2026", "15 Jan - 15 Feb", "15-31 Dec 2025", "10-14 Feb 2026"],
        "ยอดขาย": [185000, 120000, 280000, 0],
        "Leads": [89, 56, 120, 0],
        "Conversion": ["21%", "18%", "25%", "-"]
    })
    st.dataframe(campaigns, hide_index=True, use_container_width=True,
                 column_config={"ยอดขาย": st.column_config.NumberColumn(format="฿%,.0f")})
    
    st.divider()
    st.subheader("📊 A/B Comparison: Summer vs Back to School")
    comp_c1, comp_c2 = st.columns(2)
    with comp_c1:
        st.metric("☀️ Summer Sale", "฿185,000", "21% Conv")
    with comp_c2:
        st.metric("🎒 Back to School", "฿120,000", "18% Conv")
    st.success("✅ **Summer Sale** ทำผลได้ดีกว่า 54%")


# --- 🧩 Customer Segments (RFM) (Mock) ---
elif choice == "🧩 Customer Segments":
    st.header("🧩 Customer Segmentation (RFM)")
    st.caption("🚧 ตัวอย่างข้อมูล (Mock Data) สำหรับการพรีเซ้นต์")
    
    # Segment Summary
    segments = pd.DataFrame({
        "Segment": ["👑 VIP", "🔄 Loyal", "⚠️ At Risk", "🆕 New", "😴 Hibernating"],
        "จำนวน": [25, 85, 45, 120, 65],
        "% ของทั้งหมด": ["7%", "25%", "13%", "35%", "19%"],
        "ยอดใช้จ่ายเฉลี่ย": [95000, 45000, 28000, 8500, 15000],
        "แนะนำ Action": ["Exclusive Rewards", "Loyalty Program", "Win-back Campaign", "Onboarding Offer", "Re-engagement"]
    })
    
    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👑 VIP Customers", "25 คน", "7% of total")
    m2.metric("⚠️ At Risk", "45 คน", delta="-8 จากเดือนก่อน", delta_color="inverse")
    m3.metric("🆕 New Customers", "120 คน", "+15%")
    m4.metric("📊 Total Customers", "340 คน")
    
    st.divider()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📊 Segment Distribution")
        st.bar_chart(segments.set_index("Segment")["จำนวน"], color="#8B5CF6", horizontal=True)
    
    with c2:
        st.subheader("📋 Segment Details")
        st.dataframe(segments, hide_index=True, use_container_width=True,
                     column_config={"ยอดใช้จ่ายเฉลี่ย": st.column_config.NumberColumn(format="฿%,.0f")})


# --- 📅 Event Calendar (Mock) ---
elif choice == "📅 Event Calendar":
    st.header("📅 Event / Openhouse Calendar")
    st.caption("🚧 ตัวอย่างข้อมูล (Mock Data) สำหรับการพรีเซ้นต์")
    
    # Summary
    m1, m2, m3 = st.columns(3)
    m1.metric("📅 งานในเดือนนี้", "3 งาน")
    m2.metric("👥 Lead จากงาน", "89 คน", "+25%")
    m3.metric("💰 ยอดขายจากงาน", "฿245,000")
    
    st.divider()
    
    # Upcoming Events
    st.subheader("📆 กิจกรรมที่กำลังจะมาถึง")
    events = pd.DataFrame({
        "งาน": ["🏫 Openhouse โรงเรียนอนุบาลสวนเด็ก", "🎪 V-School Fair 2026", "🤝 พบผู้ปกครอง Q1"],
        "วันที่": ["08 Feb 2026", "15 Feb 2026", "28 Feb 2026"],
        "สถานที่": ["โรงเรียนอนุบาลสวนเด็ก", "V-School สาขาใหญ่", "ห้องประชุม A"],
        "สถานะ": ["🟢 Confirmed", "🟡 Preparing", "🔵 Planned"],
        "Lead คาดการณ์": [35, 80, 25]
    })
    st.dataframe(events, hide_index=True, use_container_width=True)
    
    st.divider()
    
    # Past Event Performance
    st.subheader("📊 ผลงานกิจกรรมที่ผ่านมา")
    past_events = pd.DataFrame({
        "งาน": ["🎄 Christmas Fair", "🎃 Halloween Party", "🏫 Openhouse อนุบาลแสนสุข"],
        "วันที่": ["20 Dec 2025", "31 Oct 2025", "15 Oct 2025"],
        "Leads": [65, 45, 38],
        "ลงทะเบียน": [28, 18, 22],
        "ปิดการขาย": [15, 8, 12],
        "ยอดขาย": [125000, 68000, 95000]
    })
    st.dataframe(past_events, hide_index=True, use_container_width=True,
                 column_config={"ยอดขาย": st.column_config.NumberColumn(format="฿%,.0f")})


# --- 💸 ขอรีฟันเงิน (Sales) ---
elif choice == "💸 ขอรีฟันเงิน":
    st.header("💸 ขอรีฟันเงินลูกค้า")
    st.caption("Sales สามารถส่งเรื่องขอรีฟันพร้อมรายงานเพื่อให้ผู้จัดการอนุมัติ")
    
    # Fetch data
    df_bills = run_query("""
        SELECT b.bill_id, b.sale_date, c.full_name, b.final_amount 
        FROM bills b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        ORDER BY b.sale_date DESC
        LIMIT 100
    """)
    df_emp = run_query("SELECT emp_id, emp_nickname FROM employees")
    
    if df_bills.empty:
        st.warning("ไม่พบข้อมูลบิล")
    else:
        with st.form("refund_request_form"):
            st.subheader("📝 ฟอร์มขอรีฟัน")
            
            # Bill Selection
            bill_opts = [f"{r['bill_id']} | {r['full_name']} | ฿{r['final_amount']:,.0f}" for _, r in df_bills.iterrows()]
            sel_bill = st.selectbox("🧾 เลือกบิลที่ต้องการขอรีฟัน", bill_opts)
            
            # Extract info
            sel_bill_id = sel_bill.split(" | ")[0]
            bill_info = df_bills[df_bills['bill_id'] == sel_bill_id].iloc[0]
            
            c1, c2 = st.columns(2)
            refund_amt = c1.number_input("💰 จำนวนเงินที่ขอรีฟัน (บาท)", 
                                          min_value=0.0, 
                                          max_value=float(bill_info['final_amount']),
                                          value=float(bill_info['final_amount']))
            
            # Requester (Sales)
            emp_opts = [f"{r['emp_id']} | {r['emp_nickname']}" for _, r in df_emp.iterrows()]
            sel_emp = c2.selectbox("👔 พนักงานผู้ขอ", emp_opts)
            
            reason = st.text_area("📄 รายงานสรุปเหตุผลการขอรีฟัน", 
                                  placeholder="เช่น: ลูกค้าไม่พอใจบริการ, สินค้าไม่ตรงตามที่สั่ง, ต้องการยกเลิกคอร์ส...",
                                  height=150)
            
            if st.form_submit_button("📤 ส่งเรื่องขอรีฟัน", type="primary", use_container_width=True):
                if reason.strip():
                    emp_id = int(sel_emp.split(" | ")[0])
                    cust_id = df_bills[df_bills['bill_id'] == sel_bill_id].iloc[0].get('customer_id', None)
                    
                    run_query("""
                        INSERT INTO refund_requests (bill_id, customer_id, requested_by, refund_amount, reason)
                        VALUES (:bid, :cid, :eid, :amt, :reason)
                    """, {"bid": sel_bill_id, "cid": cust_id, "eid": emp_id, "amt": refund_amt, "reason": reason})
                    
                    st.success("✅ ส่งเรื่องขอรีฟันสำเร็จ! รอผู้จัดการอนุมัติ")
                    st.balloons()
                else:
                    st.error("❌ กรุณากรอกเหตุผลการขอรีฟัน")
    
    st.divider()
    
    # Show My Requests
    st.subheader("📋 รายการที่ส่งไปแล้ว (ของฉัน)")
    df_my = run_query("""
        SELECT r.request_id, r.bill_id, r.refund_amount, r.status, r.created_at, r.manager_note
        FROM refund_requests r
        ORDER BY r.created_at DESC
        LIMIT 20
    """)
    if not df_my.empty:
        df_my['status_display'] = df_my['status'].map({
            'pending': '🟡 รออนุมัติ',
            'approved': '🟢 อนุมัติแล้ว',
            'rejected': '🔴 ไม่อนุมัติ'
        })
        st.dataframe(df_my[['request_id', 'bill_id', 'refund_amount', 'status_display', 'created_at', 'manager_note']], 
                     hide_index=True, use_container_width=True,
                     column_config={
                         "request_id": "ID",
                         "bill_id": "บิล",
                         "refund_amount": st.column_config.NumberColumn("ยอดรีฟัน", format="฿%,.0f"),
                         "status_display": "สถานะ",
                         "created_at": "วันที่ส่ง",
                         "manager_note": "หมายเหตุจาก Manager"
                     })
    else:
        st.info("ยังไม่มีรายการขอรีฟัน")


# --- ✅ อนุมัติรีฟัน (Manager) ---
elif choice == "✅ อนุมัติรีฟัน":
    st.header("✅ อนุมัติรีฟัน (Manager)")
    st.caption("ผู้จัดการสามารถอนุมัติหรือปฏิเสธคำขอรีฟันได้ที่นี่")
    
    # Pending Requests
    df_pending = run_query("""
        SELECT r.request_id, r.bill_id, c.full_name as customer, e.emp_nickname as requested_by,
               r.refund_amount, r.reason, r.created_at
        FROM refund_requests r
        LEFT JOIN customers c ON r.customer_id = c.customer_id
        LEFT JOIN employees e ON r.requested_by = e.emp_id
        WHERE r.status = 'pending'
        ORDER BY r.created_at ASC
    """)
    
    pending_count = len(df_pending)
    st.metric("📬 รายการรออนุมัติ", f"{pending_count} รายการ")
    
    if not df_pending.empty:
        for _, req in df_pending.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**🧾 บิล:** {req['bill_id']}")
                c1.markdown(f"**👤 ลูกค้า:** {req['customer']}")
                c2.metric("💰 ยอดรีฟัน", f"฿{req['refund_amount']:,.0f}")
                c3.caption(f"👔 ขอโดย: {req['requested_by']}")
                c3.caption(f"📅 {req['created_at']}")
                
                st.markdown(f"**📄 เหตุผล:** {req['reason']}")
                
                # Approval Actions
                ac1, ac2, ac3 = st.columns([2, 1, 1])
                mgr_note = ac1.text_input("หมายเหตุ (ถ้ามี)", key=f"note_{req['request_id']}")
                
                if ac2.button("✅ อนุมัติ", key=f"approve_{req['request_id']}", type="primary"):
                    run_query("""
                        UPDATE refund_requests 
                        SET status='approved', manager_note=:note, updated_at=CURRENT_TIMESTAMP
                        WHERE request_id=:id
                    """, {"id": req['request_id'], "note": mgr_note})
                    st.success("✅ อนุมัติแล้ว!")
                    st.rerun()
                
                if ac3.button("❌ ไม่อนุมัติ", key=f"reject_{req['request_id']}"):
                    run_query("""
                        UPDATE refund_requests 
                        SET status='rejected', manager_note=:note, updated_at=CURRENT_TIMESTAMP
                        WHERE request_id=:id
                    """, {"id": req['request_id'], "note": mgr_note})
                    st.warning("❌ ปฏิเสธคำขอแล้ว")
                    st.rerun()
                
                st.divider()
    else:
        st.success("✅ ไม่มีรายการรออนุมัติ")
    
    # History
    st.subheader("📜 ประวัติการอนุมัติ")
    df_history = run_query("""
        SELECT r.request_id, r.bill_id, r.refund_amount, r.status, r.manager_note, r.updated_at
        FROM refund_requests r
        WHERE r.status != 'pending'
        ORDER BY r.updated_at DESC
        LIMIT 20
    """)
    if not df_history.empty:
        df_history['status_display'] = df_history['status'].map({
            'approved': '🟢 อนุมัติ',
            'rejected': '🔴 ไม่อนุมัติ'
        })
        st.dataframe(df_history, hide_index=True, use_container_width=True,
                     column_config={"refund_amount": st.column_config.NumberColumn(format="฿%,.0f")})
