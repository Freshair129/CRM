import streamlit as st
import pandas as pd
from datetime import datetime
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
                cat_name TEXT UNIQUE NOT NULL
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
                cust_note TEXT, 
                assigned_sales_id INTEGER
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
            )'''
        ]
        for q in queries:
            run_query(q)
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

# --- 3. Sidebar Menu ---
st.set_page_config(page_title="CRM Smart Pro", layout="wide")
with st.sidebar:
    st.title("🚀 CRM System")
    if 'menu_option' not in st.session_state: st.session_state.menu_option = "📊 Dashboard"
    def set_menu(option): st.session_state.menu_option = option
    st.button("📊 Dashboard", on_click=set_menu, args=("📊 Dashboard",), use_container_width=True)
    st.button("💰 บันทึกการขาย", on_click=set_menu, args=("💰 บันทึกการขาย",), use_container_width=True)
    st.button("👥 จัดการลูกค้า", on_click=set_menu, args=("👥 จัดการลูกค้า",), use_container_width=True)
    st.button("👔 จัดการพนักงาน", on_click=set_menu, args=("👔 จัดการพนักงาน",), use_container_width=True)
    st.button("📦 จัดการสินค้า", on_click=set_menu, args=("📦 จัดการสินค้า",), use_container_width=True)
    st.button("⚙️ ตั้งค่าระบบ", on_click=set_menu, args=("⚙️ ตั้งค่าระบบ",), use_container_width=True)

choice = st.session_state.menu_option

# --- 3. ส่วนการทำงานแต่ละเมนู ---

# --- 📊 Dashboard ---
if choice == "📊 Dashboard":
    st.header("📊 รายงานสรุปภาพรวม")
    df_sales = run_query("""
        SELECT s.sale_date as "วันที่", c.full_name as "ลูกค้า", p.product_name as "สินค้า", 
               s.amount as "ยอดเงิน", s.sale_channel as "ช่องทาง"
        FROM sales_history s
        JOIN customers c ON s.customer_id = c.customer_id
        JOIN products p ON s.product_id = p.product_id
    """)
    if not df_sales.empty:
        c1, c2 = st.columns(2)
        c1.metric("ยอดขายรวม", f"{df_sales['ยอดเงิน'].sum():,.2f} บาท")
        c2.metric("จำนวนบิล", f"{len(df_sales)} รายการ")
        st.dataframe(df_sales.sort_values('วันที่', ascending=False), use_container_width=True)
    else: st.info("ยังไม่มีข้อมูลการขายในระบบ")

# --- 💰 บันทึกการขาย ---
elif choice == "💰 บันทึกการขาย":
    st.header("💰 บันทึกรายการขายใหม่")
    df_p = run_query("SELECT product_id, product_name, price FROM products")
    df_e = run_query("SELECT emp_id, emp_name, emp_nickname FROM employees")
    df_all_c = run_query("SELECT customer_id, full_name, nickname FROM customers")

    if df_all_c.empty or df_p.empty or df_e.empty:
        st.warning("⚠️ ข้อมูลไม่ครบ: กรุณาเพิ่ม ลูกค้า สินค้า และพนักงานก่อน")
    else:
        df_all_c['search_display'] = df_all_c.apply(
            lambda x: f"{x['customer_id']} | {x['full_name']} ({x['nickname'] or '-'})", axis=1
        )
        
        with st.form("sales_form_smart", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                target_cust = st.selectbox("ค้นหาลูกค้า (พิมพ์ ID/ชื่อ/ชื่อเล่น)", ["-- เลือกรายชื่อลูกค้า --"] + df_all_c['search_display'].tolist())
                sel_prod = st.selectbox("เลือกสินค้า", ["-- เลือกสินค้า --"] + df_p['product_name'].tolist())
                channel = st.radio("ช่องทาง", ["ออนไลน์", "ออนไซต์"], horizontal=True)
            with col2:
                df_e['disp'] = df_e['emp_nickname'].fillna(df_e['emp_name'])
                sel_emp = st.selectbox("พนักงานผู้ขาย", ["-- เลือกพนักงาน --"] + df_e['disp'].tolist())
                qty = st.number_input("จำนวน", min_value=1, value=1)
                pay_method = st.selectbox("วิธีชำระ", ["โอนเงิน", "เงินสด"])
            
            note = st.text_area("หมายเหตุการขาย")
            
            if sel_prod != "-- เลือกสินค้า --":
                unit_price = df_p[df_p['product_name'] == sel_prod]['price'].values[0]
                st.markdown(f"### ยอดรวม: :red[{unit_price * qty:,.2f}] บาท")
            else:
                unit_price = 0
                st.markdown("### ยอดรวม: :grey[0.00] บาท")

            if st.form_submit_button("✅ บันทึกการขาย"):
                if target_cust != "-- เลือกรายชื่อลูกค้า --" and sel_prod != "-- เลือกสินค้า --" and sel_emp != "-- เลือกพนักงาน --":
                    c_id = int(target_cust.split(" | ")[0])
                    p_id = int(df_p[df_p['product_name'] == sel_prod]['product_id'].values[0])
                    e_id = int(df_e[df_e['disp'] == sel_emp]['emp_id'].values[0])
                    run_query("""
                        INSERT INTO sales_history (customer_id, product_id, amount, payment_method, sale_channel, sale_note, closed_by_emp_id, sale_date) 
                        VALUES (:cid, :pid, :amt, :pay, :ch, :note, :eid, :dt)
                    """, {"cid": c_id, "pid": p_id, "amt": unit_price * qty, "pay": pay_method, "ch": channel, "note": note, "eid": e_id, "dt": datetime.now().date()})
                    st.success("✅ บันทึกการขายเรียบร้อย!")
                    st.rerun()
                else:
                    st.error("⚠️ กรุณาเลือกข้อมูลให้ครบถ้วน (ลูกค้า, สินค้า, พนักงาน)")

# --- 👥 จัดการลูกค้า ---
if choice == "👥 จัดการลูกค้า":
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    
    df_emp = run_query("SELECT emp_id, emp_name, emp_nickname FROM employees")
    if not df_emp.empty:
        df_emp['display_name'] = df_emp['emp_nickname'].apply(lambda x: x if x and str(x).strip() != "" else None).fillna(df_emp['emp_name'])
    else:
        df_emp = pd.DataFrame(columns=['emp_id', 'emp_name', 'emp_nickname', 'display_name'])
    
    df_all_c = run_query("SELECT customer_id, full_name FROM customers")

    # --- ส่วนเลือกเพื่อแก้ไข ---
    c_opts = ["➕ เพิ่มลูกค้าใหม่"] + [f"{r['customer_id']} | {r['full_name']}" for _, r in df_all_c.iterrows()]
    sel_edit_c = st.selectbox("🔍 เลือกรายชื่อลูกค้าที่ต้องการแก้ไข", c_opts)
    
    edit_mode = False
    edit_id = None
    curr_data = {}
    
    if sel_edit_c != "➕ เพิ่มลูกค้าใหม่":
        edit_mode = True
        edit_id = int(sel_edit_c.split(" | ")[0])
        curr_data = run_query("SELECT * FROM customers WHERE customer_id = :id", {"id": edit_id}).iloc[0].to_dict()

    with st.expander("📝 ฟอร์มข้อมูลลูกค้า", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("ชื่อ-นามสกุลจริง *", value=curr_data.get('full_name', ""))
            phone = st.text_input("เบอร์โทร", value=curr_data.get('phone', "") or "")
            line = st.text_input("LINE ID", value=curr_data.get('line_id', "") or "")
            addr_detail = st.text_area("รายละเอียดที่อยู่", value=curr_data.get('address_detail', "") or "")
            
            prov_list = sorted(list(LOCATION_DATA.keys()))
            p_idx = 0
            if edit_mode and curr_data.get('province') in prov_list:
                p_idx = prov_list.index(curr_data.get('province')) + 1
            
            sel_prov = st.selectbox("เลือกจังหวัด", ["-- โปรดเลือกจังหวัด --"] + prov_list, index=p_idx)
            
            sel_dist = ""
            zip_code = ""
            if sel_prov != "-- โปรดเลือกจังหวัด --":
                dist_list = sorted(list(LOCATION_DATA[sel_prov].keys()))
                d_idx = 0
                if edit_mode and curr_data.get('district') in dist_list:
                    d_idx = dist_list.index(curr_data.get('district'))
                
                sel_dist = st.selectbox("เลือกอำเภอ/เขต", dist_list, index=d_idx)
                zip_code = LOCATION_DATA[sel_prov][sel_dist]
                st.info(f"📍 รหัสไปรษณีย์: {zip_code}")
            else:
                st.selectbox("เลือกอำเภอ/เขต", ["-- กรุณาเลือกจังหวัดก่อน --"], disabled=True)

        with c2:
            nick = st.text_input("ชื่อเล่น", value=curr_data.get('nickname', "") or "")
            fb = st.text_input("Facebook", value=curr_data.get('facebook', "") or "")
            ig = st.text_input("Instagram", value=curr_data.get('instagram', "") or "")
            
            e_names = df_emp['display_name'].tolist() if not df_emp.empty else []
            e_idx = 0
            if edit_mode and not df_emp.empty:
                curr_eid = curr_data.get('assigned_sales_id')
                if curr_eid:
                    match = df_emp[df_emp['emp_id'] == curr_eid]
                    if not match.empty:
                        e_idx = e_names.index(match['display_name'].values[0]) + 1
            
            emp_l = st.selectbox("พนักงานผู้ดูแล", ["-- ไม่ระบุ --"] + e_names, index=e_idx)
            note = st.text_area("หมายเหตุเพิ่มเติม", value=curr_data.get('cust_note', "") or "")

        btn_label = "💾 บันทึกการแก้ไข" if edit_mode else "💾 บันทึกรายชื่อลูกค้าใหม่"
        bc1, bc2 = st.columns([1, 1])
        
        if bc1.button(btn_label, use_container_width=True, type="primary"):
            if name and sel_prov != "-- โปรดเลือกจังหวัด --":
                e_id = 0
                if emp_l != "-- ไม่ระบุ --" and not df_emp.empty:
                    e_id = int(df_emp[df_emp['display_name'] == emp_l]['emp_id'].values[0])
                
                if edit_mode:
                    run_query("""
                        UPDATE customers SET 
                        full_name=:name, nickname=:nick, phone=:phone, line_id=:line, facebook=:fb, instagram=:ig, 
                        address_detail=:addr, province=:prov, district=:dist, zipcode=:zip, cust_note=:note, assigned_sales_id=:eid
                        WHERE customer_id=:cid
                    """, {"name": name, "nick": nick, "phone": phone, "line": line, "fb": fb, "ig": ig, 
                          "addr": addr_detail, "prov": sel_prov, "dist": sel_dist, "zip": zip_code, "note": note, "eid": e_id, "cid": edit_id})
                    st.success(f"✅ อัปเดตข้อมูลคุณ {name} สำเร็จ!")
                else:
                    check = run_query("SELECT COUNT(*) as cnt FROM customers WHERE full_name = :name", {"name": name})
                    if check['cnt'][0] == 0:
                        run_query("""
                            INSERT INTO customers 
                            (full_name, nickname, phone, line_id, facebook, instagram, address_detail, province, district, zipcode, cust_note, assigned_sales_id) 
                            VALUES (:name, :nick, :phone, :line, :fb, :ig, :addr, :prov, :dist, :zip, :note, :eid)
                        """, {"name": name, "nick": nick, "phone": phone, "line": line, "fb": fb, "ig": ig, 
                              "addr": addr_detail, "prov": sel_prov, "dist": sel_dist, "zip": zip_code, "note": note, "eid": e_id})
                        st.success(f"✅ บันทึกคุณ {name} สำเร็จ!")
                    else:
                        st.error("❌ ชื่อนี้มีอยู่ในระบบแล้ว")
                st.rerun()
            else:
                st.warning("⚠️ กรุณากรอกชื่อและเลือกจังหวัดให้ครบถ้วน")
        
        if edit_mode:
            if bc2.button("🗑️ ลบรายชื่อนี้", use_container_width=True):
                run_query("DELETE FROM customers WHERE customer_id = :id", {"id": edit_id})
                st.warning(f"ลบคุณ {name} เรียบร้อย")
                st.rerun()

    st.divider()
    st.subheader("📋 รายชื่อลูกค้าทั้งหมด")
    df_list = run_query("SELECT customer_id as ID, full_name as ชื่อ, nickname as ชื่อเล่น, phone as เบอร์โทร, province as จังหวัด FROM customers")
    
    if not df_list.empty:
        st.dataframe(df_list, hide_index=True, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลลูกค้า")


# --- 👔 จัดการพนักงาน ---
elif choice == "👔 จัดการพนักงาน":
    st.header("👔 การจัดการพนักงาน")
    df_pos = run_query("SELECT pos_name FROM job_positions")
    df_e = run_query("SELECT * FROM employees")
    
    e_opts = ["➕ เพิ่มพนักงานใหม่"] + [f"{r['emp_id']} | {r['emp_name']} ({r['emp_nickname'] or '-'})" for _, r in df_e.iterrows()]
    sel_edit_e = st.selectbox("🔍 เลือกพนักงานที่ต้องการแก้ไข", e_opts)
    
    edit_mode = False
    edit_id = None
    curr_data = {}
    
    if sel_edit_e != "➕ เพิ่มพนักงานใหม่":
        edit_mode = True
        edit_id = int(sel_edit_e.split(" | ")[0])
        curr_data = df_e[df_e['emp_id'] == edit_id].iloc[0].to_dict()

    with st.expander("📝 ฟอร์มข้อมูลพนักงาน", expanded=True):
        c1, c2, c3 = st.columns(3)
        en = c1.text_input("ชื่อจริง", value=curr_data.get('emp_name', "") or "")
        eni = c2.text_input("ชื่อเล่น", value=curr_data.get('emp_nickname', "") or "")
        
        pos_list = df_pos['pos_name'].tolist() if not df_pos.empty else ["-"]
        p_idx = 0
        if edit_mode and curr_data.get('position') in pos_list:
            p_idx = pos_list.index(curr_data.get('position'))
        
        ep = c3.selectbox("ตำแหน่ง", pos_list, index=p_idx)
        
        btn_label = "💾 บันทึกการแก้ไข" if edit_mode else "💾 บันทึกพนักงานใหม่"
        bc1, bc2 = st.columns([1, 1])
        
        if bc1.button(btn_label, use_container_width=True, type="primary"):
            if en:
                try:
                    if edit_mode:
                        run_query("UPDATE employees SET emp_name=:name, emp_nickname=:nick, position=:pos WHERE emp_id=:id", 
                                  {"name": en, "nick": eni, "pos": ep, "id": edit_id})
                        st.success(f"✅ อัปเดตคุณ {en} สำเร็จ!")
                    else:
                        run_query("INSERT INTO employees (emp_name, emp_nickname, position) VALUES (:name, :nick, :pos)", 
                                  {"name": en, "nick": eni, "pos": ep})
                        st.success(f"✅ เพิ่มคุณ {en} สำเร็จ!")
                    st.rerun()
                except: st.error("❌ เกิดข้อผิดพลาด (อาจมีชื่อซ้ำ)")
        
        if edit_mode:
            if bc2.button("🗑️ ลบพนักงานท่านนี้", use_container_width=True):
                run_query("DELETE FROM employees WHERE emp_id = :id", {"id": edit_id})
                st.warning(f"ลบพนักงาน {en} เรียบร้อย")
                st.rerun()

    st.divider()
    if not df_e.empty:
        st.subheader("📋 รายชื่อพนักงานทั้งหมด")
        st.dataframe(df_e[["emp_id", "emp_name", "emp_nickname", "position"]], hide_index=True, use_container_width=True)

# --- 📦 จัดการสินค้า ---
elif choice == "📦 จัดการสินค้า":
    st.header("📦 คลังสินค้า")
    df_cat = run_query("SELECT * FROM categories")
    df_p = run_query("SELECT p.product_id, p.product_name, c.cat_name, p.price, p.cat_id FROM products p JOIN categories c ON p.cat_id = c.cat_id")
    
    p_opts = ["➕ เพิ่มสินค้าใหม่"] + [f"{r['product_id']} | {r['product_name']}" for _, r in df_p.iterrows()]
    sel_edit_p = st.selectbox("🔍 เลือกสินค้าที่ต้องการแก้ไข", p_opts)
    
    edit_mode = False
    edit_id = None
    curr_data = {}
    
    if sel_edit_p != "➕ เพิ่มสินค้าใหม่":
        edit_mode = True
        edit_id = int(sel_edit_p.split(" | ")[0])
        curr_data = df_p[df_p['product_id'] == edit_id].iloc[0].to_dict()

    with st.expander("📝 ฟอร์มข้อมูลสินค้า", expanded=True):
        c1, c2, c3 = st.columns(3)
        pn = c1.text_input("ชื่อสินค้า", value=curr_data.get('product_name', "") or "")
        
        cat_list = df_cat['cat_name'].tolist() if not df_cat.empty else ["-"]
        cat_idx = 0
        if edit_mode and curr_data.get('cat_name') in cat_list:
            cat_idx = cat_list.index(curr_data.get('cat_name'))
            
        pc = c2.selectbox("หมวดหมู่", cat_list, index=cat_idx)
        pr = c3.number_input("ราคา", min_value=0.0, value=float(curr_data.get('price', 0.0) or 0.0))
        
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
                except: st.error("❌ เกิดข้อผิดพลาด (อาจมีชื่อซ้ำ)")
        
        if edit_mode:
            if bc2.button("🗑️ ลบสินค้านี้", use_container_width=True):
                run_query("DELETE FROM products WHERE product_id = :id", {"id": edit_id})
                st.warning(f"ลบสินค้า {pn} เรียบร้อย")
                st.rerun()

    st.divider()
    if not df_p.empty:
        st.subheader("📋 รายการสินค้าทั้งหมด")
        st.dataframe(df_p[["product_id", "product_name", "cat_name", "price"]], hide_index=True, use_container_width=True)

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
            curr_cat_name = df_c[df_c['cat_id'] == edit_c_id].iloc[0]['cat_name']
            
        with st.form("cat_form", clear_on_submit=True):
            nc = st.text_input("ชื่อหมวดหมู่", value=curr_cat_name)
            cb1, cb2 = st.columns([1, 1])
            if cb1.form_submit_button("💾 บันทึก"):
                if nc:
                    if edit_c_mode:
                        run_query("UPDATE categories SET cat_name=:name WHERE cat_id=:id", {"name": nc, "id": edit_c_id})
                    else:
                        run_query("INSERT INTO categories (cat_name) VALUES (:name)", {"name": nc})
                    st.rerun()
            if edit_c_mode:
                if cb2.form_submit_button("🗑️ ลบ"):
                    run_query("DELETE FROM categories WHERE cat_id = :id", {"id": edit_c_id})
                    st.rerun()
        
        st.divider()
        st.subheader("📋 หมวดหมู่ทั้งหมด")
        if not df_c.empty:
            st.dataframe(df_c[["cat_id", "cat_name"]], hide_index=True, use_container_width=True, column_config={"cat_id": "ID", "cat_name": "ชื่อหมวดหมู่"})
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

