import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH ---
st.set_page_config(page_title="Tài chính Cloud - Canhnho", layout="centered")

# URL file Google Sheets của sếp (Thay link này bằng link file của sếp nhé)
url_sheet = "https://docs.google.com/spreadsheets/d/1zZR62bWmpGSR8Js-grYHL97GzJYBAQBUwf-fm7bh8n0/edit?gid=0#gid=0"

# --- KẾT NỐI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Đọc dữ liệu hiện có (Tắt cache để luôn lấy dữ liệu mới nhất)
df_existing = conn.read(spreadsheet=url_sheet, worksheet=0, ttl=0)

# --- XỬ LÝ SỐ DƯ ---
tong_so_du = 0
if not df_existing.empty:
    # Tính số tiền thực tế (Thu + , Chi -)
    df_existing['so_tien_plus'] = df_existing.apply(
        lambda x: x['so tien'] if x['Loai'] == 'Thu nhập' else -x['so tien'], axis=1
    )
    # Tính số dư lũy kế từng dòng
    df_existing['Số dư sau GD'] = df_existing['so_tien_plus'].cumsum()
    tong_so_du = df_existing['so_tien_plus'].sum()

formatted_balance = f"{tong_so_du:,.0f}".replace(",", ".")

# --- XỬ LÝ ĐỊNH DẠNG SỐ TIỀN NHẬP ---
if 'so_tien_formatted' not in st.session_state:
    st.session_state['so_tien_formatted'] = "0"

def format_amount_callback():
    # Lấy giá trị thô, xóa hết dấu chấm/phẩy
    raw = st.session_state.so_tien_formatted.replace(".", "").replace(",", "").strip()
    if raw.isdigit():
        # Định dạng lại với dấu chấm
        formatted = f"{int(raw):,}".replace(",", ".")
        st.session_state.so_tien_formatted = formatted
    elif raw == "":
        st.session_state.so_tien_formatted = "0"

# --- GIAO DIỆN ---
st.title("☁️ Quản lý Tài chính Cloud")

# Hiển thị số dư nổi bật ở trên cùng
col_user, col_balance = st.columns([1, 1])
with col_user:
    st.write(f"### Chào sếp Canhnho! 👋")
with col_balance:
    st.markdown(f"**Số dư hiện tại:**")
    st.markdown(f"<h1 style='color: #00b4d8; margin-top: -20px;'>{formatted_balance} VNĐ</h1>", unsafe_allow_html=True)

st.info("Dữ liệu này được lưu trực tiếp lên Google Sheets của sếp nên cực kỳ an toàn ạ!")

# --- NHẬP LIỆU ---
with st.expander("📝 Nhập Thu/Chi mới", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        ngay = st.date_input("Ngày chi tiêu:", datetime.now())
        loai = st.selectbox("Loại:", ["Thu nhập", "Chi tiêu"])
    with col2:
        # Ô nhập liệu tự động nhảy dấu chấm khi sếp nhập xong (ấn Enter hoặc Tab)
        st.text_input(
            "Số tiền (VNĐ):", 
            key="so_tien_formatted", 
            on_change=format_amount_callback,
            help="Sếp nhập số xong ấn Enter hoặc Tab để em tự thêm dấu chấm nhé!"
        )
        
        # Chuyển đổi giá trị hiển thị sang số thực để tính toán
        so_tien_clean = st.session_state.so_tien_formatted.replace(".", "")
        if not so_tien_clean.isdigit() and so_tien_clean != "":
            st.error("⚠️ Sếp ơi, ô này chỉ được nhập Số thôi ạ!")
            so_tien = 0
        else:
            so_tien = int(so_tien_clean) if so_tien_clean else 0
        
        ghi_chu = st.text_input("Ghi chú:")
    
    # Nút lưu (không dùng form để hỗ trợ định dạng trực tiếp)
    if st.button("Lưu lên Cloud ☁️", use_container_width=True):
        if so_tien <= 0:
            st.error("Dạ sếp, sếp vui lòng nhập số tiền lớn hơn 0 nhé! ❌")
        else:
            # Tạo dòng dữ liệu mới
            new_data = pd.DataFrame([{
                "Ngay": ngay.strftime("%Y-%m-%d"),
                "Loai": loai,
                "so tien": so_tien,
                "Ghi chu": ghi_chu
            }])
            
            # Gộp dữ liệu cũ và mới
            updated_df = pd.concat([df_existing, new_data], ignore_index=True)
            
            # Ghi đè lại lên Google Sheets
            conn.update(spreadsheet=url_sheet, worksheet=0, data=updated_df)
            st.success("Dạ sếp, em đã đồng bộ lên Google Sheets thành công rồi ạ! ✅")
            st.toast("Đã hoàn thành cập nhật lên Cloud! ☁️", icon="✅")
            st.rerun() # Tải lại trang để cập nhật biểu đồ

# --- LỊCH SỬ GIAO DỊCH ---
if not df_existing.empty:
    st.subheader("📊 Lịch sử giao dịch từ Cloud")
    
    # Tạo bản sao để hiển thị
    df_display = df_existing.copy()
    
    # Thêm cột STT (Số thứ tự) dựa trên vị trí thực tế trong file
    df_display.insert(0, 'STT', range(1, len(df_display) + 1))
    
    # Định dạng các cột số sang chuỗi có dấu chấm kiểu Việt Nam
    df_display["Số tiền (VNĐ)"] = df_display["so tien"].apply(lambda x: f"{x:,.0f}".replace(",", "."))
    df_display["Số dư sau GD"] = df_display["Số dư sau GD"].apply(lambda x: f"{x:,.0f}".replace(",", "."))
    
    # Chỉ lấy 10 dòng cuối để hiển thị cho gọn
    df_display = df_display.tail(10)
    
    # Sắp xếp lại thứ tự cột theo ý sếp: STT / Ngay / Loai / so tiền / ghi chu / số dư sau GD
    columns_order = ["STT", "Ngay", "Loai", "Số tiền (VNĐ)", "Ghi chu", "Số dư sau GD"]
    
    # Hiển thị bảng
    st.dataframe(
        df_display[columns_order], 
        use_container_width=True,
        hide_index=True # Ẩn index mặc định của pandas vì đã có STT
    )
else:
    st.warning("Chưa có dữ liệu trên Cloud, sếp nhập khoản đầu tiên nhé!")