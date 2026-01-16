import streamlit as st
from pathlib import Path

from src.system import CustomerJourneySystem
from src.weights import DEFAULT_BASE_WEIGHTS

# -------------------------------------------------
# إعدادات الصفحة (يفضل وضعها في الأعلى)
# -------------------------------------------------
st.set_page_config(
    page_title="نظام رحلة العميل",
    layout="wide"
)

st.title("نظام رحلة العميل")
st.write("واجهة تفاعلية لعرض أفضل 4 إجراءات مقترحة حسب الدولة والحل، مع تحديث الأوزان ديناميكياً.")

# -------------------------------------------------
# تهيئة النظام في session_state حتى لا يُعاد تحميله كل مرة
# -------------------------------------------------
if "cjs" not in st.session_state:
    processed_dir = Path("data/processed")  # تأكد أن هذا المسار موجود في المستودع
    st.session_state.cjs = CustomerJourneySystem(processed_dir=processed_dir)

cjs = st.session_state.cjs

# -------------------------------------------------
# اختيار العملية من الشريط الجانبي
# -------------------------------------------------
العملية = st.sidebar.radio(
    "اختر العملية:",
    ["إضافة حساب جديد", "إضافة إجراء لحساب"]
)

# -------------------------------------------------
# 1) إضافة حساب جديد
# -------------------------------------------------
if العملية == "إضافة حساب جديد":
    st.header("إضافة حساب جديد")

    with st.form("نموذج_إضافة_حساب"):
        account_id = st.text_input("معرّف الحساب", value="A001")
        country = st.text_input("الدولة (مثال: AT)")
        solution = st.text_input("الحل (مثال: MRS)")

        تنفيذ = st.form_submit_button("تنفيذ")

    if تنفيذ:
        # تنظيف المدخلات
        account_id = (account_id or "").strip()
        country = (country or "").strip().upper()
        solution = (solution or "").strip().upper()

        if not account_id or not country or not solution:
            st.error("يرجى تعبئة جميع الحقول قبل التنفيذ.")
        else:
            try:
                result = cjs.add_account(
                    account_id=account_id,
                    country=country,
                    solution=solution,
                )

                st.subheader("النتائج")

                st.write("أفضل 4 إجراءات حسب الدولة")
                st.table(result.get("top4_by_country", []))

                st.write("أفضل 4 إجراءات حسب الحل")
                st.table(result.get("top4_by_solution", []))

                st.write("أفضل 4 إجراءات حسب الدولة والحل")
                st.table(result.get("top4_by_country_solution", []))

            except Exception as e:
                st.error("حدث خطأ أثناء تنفيذ العملية.")
                st.exception(e)

# -------------------------------------------------
# 2) إضافة إجراء لحساب موجود
# -------------------------------------------------
elif العملية == "إضافة إجراء لحساب":
    st.header("إضافة إجراء وتحديث الأوزان")

    with st.form("نموذج_إضافة_إجراء"):
        account_id = st.text_input("معرّف الحساب", value="A001")
        country = st.text_input("الدولة (مثال: AT)")
        solution = st.text_input("الحل (مثال: MRS)")

        action_type = st.selectbox(
            "نوع الإجراء",
            options=list(DEFAULT_BASE_WEIGHTS.keys())
        )

        تنفيذ = st.form_submit_button("تنفيذ")

    if تنفيذ:
        # تنظيف المدخلات
        account_id = (account_id or "").strip()
        country = (country or "").strip().upper()
        solution = (solution or "").strip().upper()

        if not account_id or not country or not solution:
            st.error("يرجى تعبئة جميع الحقول قبل التنفيذ.")
        else:
            try:
                result = cjs.add_action(
                    account_id=account_id,
                    country=country,
                    solution=solution,
                    action_type=action_type,
                )

                st.subheader("النتائج")

                st.write(f"معرّف الحساب: {result.get('account_id', '')}")
                st.write(f"الإجراء المضاف: {result.get('added_action', '')}")
                st.write(f"الوزن المعدّل: {result.get('adjusted_weight', '')}")

                st.write("أفضل 4 إجراءات حسب الدولة (بعد التحديث)")
                st.table(result.get("top4_by_country", []))

                st.write("أفضل 4 إجراءات حسب الحل (بعد التحديث)")
                st.table(result.get("top4_by_solution", []))

                st.write("أفضل 4 إجراءات حسب الدولة والحل (بعد التحديث)")
                st.table(result.get("top4_by_country_solution", []))

            except Exception as e:
                st.error("حدث خطأ أثناء تنفيذ العملية.")
                st.exception(e)
