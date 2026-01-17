import streamlit as st
from pathlib import Path

from src.system import CustomerJourneySystem
from src.weights import DEFAULT_BASE_WEIGHTS

# -------------------------------------------------
# تهيئة النظام في session_state حتى لا يُعاد تحميله كل مرة
# -------------------------------------------------
if "cjs" not in st.session_state:
    processed_dir = Path("data/processed")  # عدل المسار إذا لزم
    st.session_state.cjs = CustomerJourneySystem(processed_dir=processed_dir)

cjs = st.session_state.cjs

st.set_page_config(
    page_title="Customer Journey System",
    layout="wide"
)

st.title("Customer Journey System")
st.write("واجهة تفاعلية لعرض أفضل الأفعال (Top 4 Actions) حسب الدولة والحل، مع تحديث الأوزان ديناميكياً.")

# -------------------------------------------------
# اختيار الوضع من الـ Sidebar
# -------------------------------------------------
mode = st.sidebar.radio(
    "اختر العملية:",
    ["إضافة حساب جديد (add_account)", "إضافة Action لحساب (add_action)"]
)

# -------------------------------------------------
# 1) إضافة حساب جديد
# -------------------------------------------------
if mode == "إضافة حساب جديد (add_account)":
    st.header("إضافة حساب جديد")

    with st.form("add_account_form"):
        account_id = st.text_input("Account ID", value="A001")
        country = st.text_input("Country (مثال: AT)")
        solution = st.text_input("Solution (مثال: MRS)")

        submitted = st.form_submit_button("تنفيذ add_account")

    if submitted:
        if not account_id or not country or not solution:
            st.error("الرجاء تعبئة جميع الحقول.")
        else:
            result = cjs.add_account(
                account_id=account_id,
                country=country,
                solution=solution,
            )

            st.subheader("النتائج")

            st.write("**Top 4 actions by Country**")
            st.table(result["top4_by_country"])

            st.write("**Top 4 actions by Solution**")
            st.table(result["top4_by_solution"])

            st.write("**Top 4 actions by Country & Solution**")
            st.table(result["top4_by_country_solution"])

# -------------------------------------------------
# 2) إضافة Action لحساب موجود
# -------------------------------------------------
elif mode == "إضافة Action لحساب (add_action)":
    st.header("إضافة Action وتحديث الأوزان")

    with st.form("add_action_form"):
        account_id = st.text_input("Account ID", value="A001")
        country = st.text_input("Country (مثال: AT)")
        solution = st.text_input("Solution (مثال: MRS)")

        # أنواع الأفعال من DEFAULT_BASE_WEIGHTS في weights.py
        action_type = st.selectbox(
            "نوع الـ Action",
            options=list(DEFAULT_BASE_WEIGHTS.keys())
        )

        submitted = st.form_submit_button("تنفيذ add_action")

    if submitted:
        if not account_id or not country or not solution:
            st.error("الرجاء تعبئة جميع الحقول.")
        else:
            result = cjs.add_action(
                account_id=account_id,
                country=country,
                solution=solution,
                action_type=action_type,
            )

            st.subheader("النتائج")

            st.write(f"**الحساب:** {result['account_id']}")
            st.write(f"**الـ Action المضافة:** {result['added_action']}")
            st.write(f"**الوزن المعدل (adjusted_weight):** {result['adjusted_weight']}")

            st.write("**Top 4 actions by Country (بعد التحديث)**")
            st.table(result["top4_by_country"])

            st.write("**Top 4 actions by Solution (بعد التحديث)**")
            st.table(result["top4_by_solution"])

            st.write("**Top 4 actions by Country & Solution (بعد التحديث)**")
            st.table(result["top4_by_country_solution"])
