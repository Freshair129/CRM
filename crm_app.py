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
                marital_status TEXT,
                has_children TEXT,
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
            )'''
        ]
        for q in queries:
            run_query(q)
        
        # Add columns to 'customers' if they don't exist
        try:
            run_query("ALTER TABLE customers ADD COLUMN IF NOT EXISTS gender TEXT")
            run_query("ALTER TABLE customers ADD COLUMN IF NOT EXISTS marital_status TEXT")
            run_query("ALTER TABLE customers ADD COLUMN IF NOT EXISTS has_children TEXT")
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
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN products p ON s.product_id = p.product_id
    """)
    if not df_sales.empty:
        df_sales['ลูกค้า'] = df_sales['ลูกค้า'].fillna("❌ ข้อมูลถูกลบ")
        df_sales['สินค้า'] = df_sales['สินค้า'].fillna("❌ ข้อมูลถูกลบ")
        c1, c2 = st.columns(2)
        c1.metric("ยอดขายรวม", f"{df_sales['ยอดเงิน'].sum():,.2f} บาท")
        c2.metric("จำนวนบิล", f"{len(df_sales)} รายการ")
        st.dataframe(df_sales.sort_values('วันที่', ascending=False), use_container_width=True)
    else: st.info("ยังไม่มีข้อมูลการขายในระบบ")

# --- 💰 บันทึกการขาย ---
elif choice == "💰 บันทึกการขาย":
    st.header("🛒 ระบบบันทึกการขาย (ตระกร้าสินค้า)")
    
    # Initialize Cart
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    
    df_p = run_query("SELECT product_id, product_name, price FROM products")
    df_e = run_query("SELECT emp_id, emp_name, emp_nickname FROM employees")
    df_all_c = run_query("SELECT customer_id, full_name, nickname FROM customers")

    if df_all_c.empty or df_p.empty or df_e.empty:
        st.warning("⚠️ ข้อมูลไม่ครบ: กรุณาเพิ่ม ลูกค้า สินค้า และพนักงานก่อน")
    else:
        # 1. Customer & Seller Selection
        c1, c2 = st.columns(2)
        with c1:
            df_all_c['search_display'] = df_all_c.apply(lambda x: f"{x['customer_id']} | {x['full_name']} ({x['nickname'] or '-'})", axis=1)
            sel_cust = st.selectbox("👤 เลือกลูกค้า", ["-- เลือกรายชื่อลูกค้า --"] + df_all_c['search_display'].tolist())
        with c2:
            df_e['disp'] = df_e['emp_nickname'].fillna(df_e['emp_name'])
            sel_emp = st.selectbox("👔 พนักงานผู้ขาย", ["-- เลือกพนักงาน --"] + df_e['disp'].tolist())
        
        st.divider()
        
        # 2. Add to Cart Section
        with st.expander("➕ เพิ่มสินค้าลงตระกร้า", expanded=True):
            ac1, ac2, ac3 = st.columns([3, 1, 1])
            prod_to_add = ac1.selectbox("เลือกสินค้า", df_p['product_name'].tolist())
            qty_to_add = ac2.number_input("จำนวน", min_value=1, value=1)
            if ac3.button("➕ เพิ่มลงตระกร้า", use_container_width=True, type="secondary"):
                p_info = df_p[df_p['product_name'] == prod_to_add].iloc[0]
                st.session_state.cart.append({
                    "id": int(p_info['product_id']),
                    "name": p_info['product_name'],
                    "price": float(p_info['price']),
                    "qty": qty_to_add,
                    "total": float(p_info['price'] * qty_to_add)
                })
                st.rerun()

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
                if cols[4].button("❌", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            subtotal = sum(item['total'] for item in st.session_state.cart)
            
            st.divider()
            
            # 4. Checkout
            cc1, cc2, cc3 = st.columns(3)
            discount_pct = cc1.number_input("📉 ส่วนลด (%)", min_value=0.0, max_value=100.0, value=0.0)
            pay_method = cc2.selectbox("💳 วิธีชำระเงิน", ["โอนเงิน", "เงินสด"])
            channel = cc3.radio("📡 ช่องทาง", ["ออนไลน์", "ออนไซต์"], horizontal=True)
            
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
                    
                    # Save Bill header
                    run_query("""
                        INSERT INTO bills (bill_id, customer_id, seller_id, total_amount, discount, final_amount, payment_method)
                        VALUES (:bid, :cid, :sid, :total, :disc, :final, :pay)
                    """, {"bid": new_bill_id, "cid": c_id, "sid": e_id, "total": subtotal, "disc": discount_amt, "final": final_total, "pay": pay_method})
                    
                    # Save Bill items
                    for item in st.session_state.cart:
                        run_query("""
                            INSERT INTO bill_items (bill_id, product_id, product_name, qty, unit_price, subtotal)
                            VALUES (:bid, :pid, :pname, :qty, :uprice, :sub)
                        """, {"bid": new_bill_id, "pid": item['id'], "pname": item['name'], "qty": item['qty'], "uprice": item['price'], "sub": item['total']})
                        
                        # Legacy support: also save to sales_history for old dashboard/reports
                        run_query("""
                            INSERT INTO sales_history (customer_id, product_id, amount, payment_method, sale_channel, closed_by_emp_id, sale_date)
                            VALUES (:cid, :pid, :amt, :pay, :ch, :eid, :dt)
                        """, {"cid": c_id, "pid": item['id'], "amt": item['total'], "pay": pay_method, "ch": channel, "eid": e_id, "dt": now.date()})
                    
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

# --- 👥 จัดการลูกค้า ---
if choice == "👥 จัดการลูกค้า":
    st.header("👥 จัดการฐานข้อมูลลูกค้า")
    
    df_all_c = run_query("SELECT * FROM customers")
    
    if not df_all_c.empty:
        c_opts = ["➕ ลงทะเบียนลูกค้าใหม่"] + [f"{r['customer_id']} | {r['full_name']}" for _, r in df_all_c.iterrows()]
        sel_edit_c = st.selectbox("📝 เลือกรายชื่อเพื่อ แกไข หรือ ลบข้อมูล", c_opts)
    else:
        st.info("ยังไม่มีข้อมูลลูกค้า")
        sel_edit_c = "➕ ลงทะเบียนลูกค้าใหม่"

    edit_mode = False
    edit_id = None
    curr_data = {}
    
    if sel_edit_c != "➕ ลงทะเบียนลูกค้าใหม่":
        edit_mode = True
        edit_id = int(sel_edit_c.split(" | ")[0])
        curr_data = df_all_c[df_all_c['customer_id'] == edit_id].iloc[0].to_dict()

    with st.expander("📝 ฟอร์มข้อมูลลูกค้า", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            form_key_suffix = str(edit_id) if edit_mode else "new"
            name = st.text_input("ชื่อ-นามสกุลจริง *", value=curr_data.get('full_name', ""), key=f"c_name_{form_key_suffix}")
            phone = st.text_input("เบอร์โทร", value=curr_data.get('phone', "") or "", key=f"c_phone_{form_key_suffix}")
            line = st.text_input("LINE ID", value=curr_data.get('line_id', "") or "", key=f"c_line_{form_key_suffix}")
            addr_detail = st.text_area("รายละเอียดที่อยู่", value=curr_data.get('address_detail', "") or "", key=f"c_addr_{form_key_suffix}")
            
            prov_list = sorted(list(LOCATION_DATA.keys()))
            p_idx = 0
            if edit_mode and curr_data.get('province') in prov_list:
                p_idx = prov_list.index(curr_data.get('province')) + 1
            
            sel_prov = st.selectbox("เลือกจังหวัด", ["-- โปรดเลือกจังหวัด --"] + prov_list, index=p_idx, key=f"c_prov_{form_key_suffix}")
            
            sel_dist = ""
            zip_code = ""
            if sel_prov != "-- โปรดเลือกจังหวัด --":
                dist_list = sorted(list(LOCATION_DATA[sel_prov].keys()))
                d_idx = 0
                if edit_mode and curr_data.get('district') in dist_list:
                    d_idx = dist_list.index(curr_data.get('district'))
                
                sel_dist = st.selectbox("เลือกอำเภอ/เขต", dist_list, index=d_idx, key=f"c_dist_{form_key_suffix}")
                zip_code = LOCATION_DATA[sel_prov][sel_dist]
                st.info(f"📍 รหัสไปรษณีย์: {zip_code}")
            else:
                st.selectbox("เลือกอำเภอ/เขต", ["-- กรุณาเลือกจังหวัดก่อน --"], disabled=True, key=f"c_dist_dis_{form_key_suffix}")

        with c2:
            nick = st.text_input("ชื่อเล่น", value=curr_data.get('nickname', "") or "", key=f"c_nick_{form_key_suffix}")
            fb = st.text_input("Facebook", value=curr_data.get('facebook', "") or "", key=f"c_fb_{form_key_suffix}")
            ig = st.text_input("Instagram", value=curr_data.get('instagram', "") or "", key=f"c_ig_{form_key_suffix}")
            
            df_emp = run_query("SELECT emp_id, emp_name, emp_nickname FROM employees")
            if not df_emp.empty:
                df_emp['display_name'] = df_emp['emp_nickname'].apply(lambda x: x if x and str(x).strip() != "" else None).fillna(df_emp['emp_name'])
                e_names = df_emp['display_name'].tolist()
            else:
                e_names = []
                
            e_idx = 0
            if edit_mode and not df_emp.empty:
                curr_eid = curr_data.get('assigned_sales_id')
                if curr_eid:
                    match = df_emp[df_emp['emp_id'] == curr_eid]
                    if not match.empty:
                        e_idx = e_names.index(match['display_name'].values[0]) + 1
            
            emp_l = st.selectbox("พนักงานผู้ดูแล", ["-- ไม่ระบุ --"] + e_names, index=e_idx, key=f"c_emp_{form_key_suffix}")
            
            st.divider()
            st.write("📋 **ข้อมูลส่วนตัวเพิ่มเติม**")
            g_opts = ["-- ระบุเพศ --", "ชาย", "หญิง", "อื่นๆ"]
            g_idx = 0
            if edit_mode and curr_data.get('gender') in g_opts:
                g_idx = g_opts.index(curr_data.get('gender'))
            gender = st.selectbox("เพศ", g_opts, index=g_idx, key=f"c_gender_{form_key_suffix}")
            
            m_opts = ["-- สถานะภาพ --", "โสด", "แต่งงานแล้ว", "หย่าร้าง / หม้าย"]
            m_idx = 0
            if edit_mode and curr_data.get('marital_status') in m_opts:
                m_idx = m_opts.index(curr_data.get('marital_status'))
            marital = st.selectbox("สถานะภาพ", m_opts, index=m_idx, key=f"c_marital_{form_key_suffix}")
            
            c_opts = ["-- ข้อมูลบุตร --", "ยังไม่มีบุตร", "มีบุตรแล้ว"]
            c_idx = 0
            if edit_mode and curr_data.get('has_children') in c_opts:
                c_idx = c_opts.index(curr_data.get('has_children'))
            children = st.selectbox("การมีบุตร", c_opts, index=c_idx, key=f"c_children_{form_key_suffix}")

            note = st.text_area("หมายเหตุเพิ่มเติม", value=curr_data.get('cust_note', "") or "", key=f"c_note_{form_key_suffix}")
            

        btn_label = "💾 บันทึกการแก้ไข" if edit_mode else "💾 ลงทะเบียนลูกค้าใหม่"
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
                        address_detail=:addr, province=:prov, district=:dist, zipcode=:zip, cust_note=:note, 
                        assigned_sales_id=:eid, gender=:gender, marital_status=:marital, has_children=:children
                        WHERE customer_id=:cid
                    """, {"name": name, "nick": nick, "phone": phone, "line": line, "fb": fb, "ig": ig, 
                          "addr": addr_detail, "prov": sel_prov, "dist": sel_dist, "zip": zip_code, "note": note, 
                          "eid": e_id, "cid": edit_id, "gender": gender, "marital": marital, "children": children})
                    st.success(f"✅ อัปเดตข้อมูลคุณ {name} สำเร็จ!")
                else:
                    check = run_query("SELECT COUNT(*) as cnt FROM customers WHERE full_name = :name", {"name": name})
                    if check['cnt'][0] == 0:
                        run_query("""
                            INSERT INTO customers 
                            (full_name, nickname, phone, line_id, facebook, instagram, address_detail, province, district, zipcode, cust_note, assigned_sales_id, gender, marital_status, has_children) 
                            VALUES (:name, :nick, :phone, :line, :fb, :ig, :addr, :prov, :dist, :zip, :note, :eid, :gender, :marital, :children)
                        """, {"name": name, "nick": nick, "phone": phone, "line": line, "fb": fb, "ig": ig, 
                              "addr": addr_detail, "prov": sel_prov, "dist": sel_dist, "zip": zip_code, "note": note, 
                              "eid": e_id, "gender": gender, "marital": marital, "children": children})
                        st.success(f"✅ บันทึกคุณ {name} สำเร็จ!")
                    else:
                        st.error("❌ ชื่อนี้มีอยู่ในระบบแล้ว")
                st.rerun()
            else:
                st.warning("⚠️ กรุณากรอกชื่อและเลือกจังหวัดให้ครบถ้วน")
        
        if edit_mode:
            if bc2.button("🗑️ ลบรายชื่อลูกค้านี้", use_container_width=True):
                run_query("DELETE FROM customers WHERE customer_id = :id", {"id": edit_id})
                st.warning(f"ลบคุณ {name} เรียบร้อย")
                st.rerun()

    st.divider()
    st.subheader("📋 รายชื่อลูกค้าทั้งหมด")
    search_q = st.text_input("🔍 ค้นหา (ชื่อ หรือ เบอร์โทร)", placeholder="พิมพ์ค้นหาที่นี่...")
    
    if not df_all_c.empty:
        if search_q:
            df_filtered = df_all_c[df_all_c['full_name'].str.contains(search_q, case=False, na=False) | 
                                   df_all_c['phone'].str.contains(search_q, case=False, na=False)]
        else:
            df_filtered = df_all_c
        
        st.dataframe(df_filtered[["customer_id", "full_name", "nickname", "phone", "province"]], 
                     hide_index=True, use_container_width=True,
                     column_config={"customer_id": "ID", "full_name": "ชื่อ-นามสกุล", "nickname": "ชื่อเล่น", "phone": "เบอร์โทร", "province": "จังหวัด"})


# --- 👔 จัดการพนักงาน ---
elif choice == "👔 จัดการพนักงาน":
    st.header("👔 การจัดการพนักงาน")
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

        e_opts = ["➕ เพิ่มพนักงานใหม่"] + [f"{r['emp_id']} | {r['emp_name']} ({r['emp_nickname'] or '-'})" for _, r in df_e.iterrows()]
        sel_edit_e = st.selectbox("📝 เลือกพนักงานเพื่อ แก้ไข หรือ ลบข้อมูล", e_opts)
    else:
        st.info("ยังไม่มีข้อมูลพนักงาน")
        sel_edit_e = "➕ เพิ่มพนักงานใหม่"

    edit_mode = False
    edit_id = None
    curr_data = {}
    
    if sel_edit_e != "➕ เพิ่มพนักงานใหม่":
        edit_mode = True
        edit_id = int(sel_edit_e.split(" | ")[0])
        curr_data = df_e[df_e['emp_id'] == edit_id].iloc[0].to_dict()

    with st.expander("📝 ฟอร์มข้อมูลพนักงาน", expanded=True):
        c1, c2, c3 = st.columns(3)
        form_key_suffix = str(edit_id) if edit_mode else "new"
        en = c1.text_input("ชื่อจริง", value=curr_data.get('emp_name', "") or "", key=f"e_name_{form_key_suffix}")
        eni = c2.text_input("ชื่อเล่น", value=curr_data.get('emp_nickname', "") or "", key=f"e_nick_{form_key_suffix}")
        
        df_pos = run_query("SELECT pos_name FROM job_positions")
        pos_list = df_pos['pos_name'].tolist() if not df_pos.empty else ["-"]
        p_idx = 0
        if edit_mode and curr_data.get('position') in pos_list:
            p_idx = pos_list.index(curr_data.get('position'))
        
        ep = c3.selectbox("ตำแหน่ง", pos_list, index=p_idx, key=f"e_pos_{form_key_suffix}")
        
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
                except Exception: st.error("❌ เกิดข้อผิดพลาด (อาจมีชื่อซ้ำ)")
        
        if edit_mode:
            if bc2.button("🗑️ ลบพนักงานท่านนี้", use_container_width=True):
                run_query("DELETE FROM employees WHERE emp_id = :id", {"id": edit_id})
                st.warning(f"ลบพนักงาน {en} เรียบร้อย")
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

