import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import io

# --- CẤU HÌNH ---
st.set_page_config(page_title="Tài chính Cloud - Canhnho", layout="centered", page_icon="☁️")

# CSS để App trông "xịn" hơn trên điện thoại
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #00b4d8;
        color: white;
        border: none;
        font-weight: bold;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div[data-testid="stExpander"] {
        border-radius: 15px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        background-color: white;
    }
    /* Ẩn header mặc định của Streamlit */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# URL file Google Sheets của sếp
url_sheet = "https://docs.google.com/spreadsheets/d/1zZR62bWmpGSR8Js-grYHL97GzJYBAQBUwf-fm7bh8n0/edit"

# --- KẾT NỐI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Đọc dữ liệu hiện có (Tắt cache để luôn lấy dữ liệu mới nhất)
df_existing = conn.read(spreadsheet=url_sheet, worksheet=0, ttl=0)

# Xử lý số dư và tiền thực tế
if not df_existing.empty:
    # Chuyển đổi ngày an toàn hơn, bỏ qua các dòng lỗi định dạng ngày
    df_existing['Ngay'] = pd.to_datetime(df_existing['Ngay'], errors='coerce')
    
    # Bỏ các dòng không thể nhận diện ngày (ví dụ dòng trống hoặc sai định dạng)
    invalid_dates = df_existing['Ngay'].isna().sum()
    if invalid_dates > 0:
        st.sidebar.warning(f"⚠️ Có {invalid_dates} dòng dữ liệu sai định dạng ngày và đã được bỏ qua.")
    df_existing = df_existing.dropna(subset=['Ngay'])
    
    # Tiếp tục tính toán
    df_existing['so_tien_plus'] = df_existing.apply(
        lambda x: x['so tien'] if x['Loai'] == 'Thu nhập' else -x['so tien'], axis=1
    )
    df_existing['Số dư sau GD'] = df_existing['so_tien_plus'].cumsum()
    tong_so_du = df_existing['so_tien_plus'].sum()
else:
    tong_so_du = 0

# --- APP NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["🏠 Trang chủ", "💸 Nhập liệu", "📊 Lịch sử"])

# ==========================================
# TAB 1: TRANG CHỦ (DASHBOARD)
# ==========================================
with tab1:
    st.markdown(f"### Chào sếp Canhnho! 👋")
    
    # Hiển thị số dư chính
    st.metric("Số dư hiện tại", f"{tong_so_du:,.0f} VNĐ".replace(",", "."), delta=None)
    
    if not df_existing.empty:
        col_in, col_out = st.columns(2)
        with col_in:
            tong_thu = df_existing[df_existing['Loai'] == 'Thu nhập']['so tien'].sum()
            st.metric("Tổng Thu", f"{tong_thu:,.0f}".replace(",", "."), delta_color="normal")
        with col_out:
            tong_chi = df_existing[df_existing['Loai'] == 'Chi tiêu']['so tien'].sum()
            st.metric("Tổng Chi", f"-{tong_chi:,.0f}".replace(",", "."), delta_color="inverse")

        st.subheader("📈 Xu hướng gần đây")
        # Chuẩn bị dữ liệu cho biểu đồ (Gộp theo ngày)
        chart_data = df_existing.groupby(['Ngay', 'Loai'])['so tien'].sum().unstack(fill_value=0)
        
        # Định nghĩa màu sắc: Thu nhập (Xanh), Chi tiêu (Đỏ)
        color_map = {"Thu nhập": "#2ecc71", "Chi tiêu": "#e74c3c"}
        
        # Hiển thị biểu đồ với màu tùy chỉnh
        st.bar_chart(chart_data, color=[color_map.get(col, "#bdbdbd") for col in chart_data.columns])
    else:
        st.info("Chưa có dữ liệu để hiển thị biểu đồ sếp ơi!")

# ==========================================
# TAB 2: NHẬP LIỆU
# ==========================================
with tab2:
    st.subheader("📝 Thêm giao dịch mới")
    
    if 'so_tien_formatted' not in st.session_state:
        st.session_state['so_tien_formatted'] = "0"

    def format_amount_callback():
        raw = st.session_state.so_tien_formatted.replace(".", "").replace(",", "").strip()
        if raw.isdigit():
            formatted = f"{int(raw):,}".replace(",", ".")
            st.session_state.so_tien_formatted = formatted
        elif raw == "":
            st.session_state.so_tien_formatted = "0"

    with st.container():
        ngay = st.date_input("Ngày:", datetime.now())
        loai = st.selectbox("Loại giao dịch:", ["Chi tiêu", "Thu nhập"])
        
        st.text_input(
            "Số tiền (VNĐ):", 
            key="so_tien_formatted", 
            on_change=format_amount_callback,
            help="Sếp nhập số xong em tự thêm dấu chấm nhé!"
        )
        
        so_tien_clean = st.session_state.so_tien_formatted.replace(".", "")
        so_tien = int(so_tien_clean) if so_tien_clean.isdigit() else 0
        
        ghi_chu = st.text_input("Ghi chú / Nội dung:")
        
        if st.button("Lưu lên Cloud ☁️", use_container_width=True):
            if so_tien <= 0:
                st.error("Dạ sếp, tiền phải lớn hơn 0 mới được ạ! ❌")
            else:
                new_data = pd.DataFrame([{
                    "Ngay": ngay.strftime("%Y-%m-%d"),
                    "Loai": loai,
                    "so tien": so_tien,
                    "Ghi chu": ghi_chu
                }])
                updated_df = pd.concat([df_existing.drop(columns=['so_tien_plus', 'Số dư sau GD', 'Month_Year'], errors='ignore'), new_data], ignore_index=True)
                conn.update(spreadsheet=url_sheet, worksheet=0, data=updated_df)
                st.success("Đã đồng bộ thành công! ✅")
                st.toast("Đã hoàn thành cập nhật! ☁️", icon="✅")
                st.rerun()

# ==========================================
# TAB 3: LỊCH SỬ & SAO KÊ
# ==========================================
with tab3:
    if not df_existing.empty:
        st.subheader("🔍 Bộ lọc & Xuất file")
        
        filter_type = st.radio("Lọc theo:", ["Tất cả", "Tháng", "Khoảng ngày"], horizontal=True)
        df_filtered = df_existing.copy()

        if filter_type == "Tháng":
            df_existing['Month_Year'] = df_existing['Ngay'].dt.strftime('%m/%Y')
            month_list = sorted(df_existing['Month_Year'].unique().tolist(), reverse=True)
            selected_month = st.selectbox("Chọn tháng:", month_list)
            df_filtered = df_existing[df_existing['Month_Year'] == selected_month]
        
        elif filter_type == "Khoảng ngày":
            col1, col2 = st.columns(2)
            with col1:
                d1 = st.date_input("Từ ngày:", df_existing['Ngay'].min())
            with col2:
                d2 = st.date_input("Đến ngày:", datetime.now())
            df_filtered = df_existing[(df_existing['Ngay'] >= pd.to_datetime(d1)) & (df_existing['Ngay'] <= pd.to_datetime(d2))]

        # --- NÚT XUẤT EXCEL ---
        if not df_filtered.empty:
            # Tạo file excel trong bộ nhớ
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Chỉ xuất các cột cần thiết
                df_export = df_filtered[["Ngay", "Loai", "so tien", "Ghi chu", "Số dư sau GD"]].copy()
                df_export['Ngay'] = df_export['Ngay'].dt.strftime('%d/%m/%Y')
                df_export.to_excel(writer, index=False, sheet_name='SaoKe')
            
            processed_data = output.getvalue()
            
            st.download_button(
                label="📥 Tải file Excel sao kê",
                data=processed_data,
                file_name=f"SaoKe_TaiChinh_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Hiển thị bảng
            st.markdown("---")
            df_display = df_filtered.copy()
            df_display.insert(0, 'STT', range(1, len(df_display) + 1))
            df_display['Ngay'] = df_display['Ngay'].dt.strftime('%d/%m/%Y')
            df_display["Tiền"] = df_display["so tien"].apply(lambda x: f"{x:,.0f}".replace(",", "."))
            df_display["Số dư"] = df_display["Số dư sau GD"].apply(lambda x: f"{x:,.0f}".replace(",", "."))
            
            st.dataframe(
                df_display[["STT", "Ngay", "Loai", "Tiền", "Ghi chu", "Số dư"]], 
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("Không tìm thấy dữ liệu phù hợp!")
    else:
        st.warning("Chưa có dữ liệu nào sếp ơi!")
