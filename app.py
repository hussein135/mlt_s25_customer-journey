import streamlit as st
from pathlib import Path
import pandas as pd

from src.system import CustomerJourneySystem
from src.weights import DEFAULT_BASE_WEIGHTS

# -------------------------------------------------
# إعدادات الصفحة (يجب أن تكون أول أوامر Streamlit)
# -------------------------------------------------
st.set_page_config(page_title="نظام رحلة العميل", layout="wide")

st.title("نظام رحلة العميل")
st.write("واجهة تفاعلية لعرض أفضل 4 إجراءات مقترحة حسب الدولة والحل، مع تحديث الأوزان ديناميكياً.")

PROCESSED_DIR = Path("data/processed")

# -------------------------------------------------
# تحقق من وجود البيانات
# -------------------------------------------------
if not PROCESSED_DIR.exists():
    st.error("المجلد data/processed غير موجود داخل المستودع. تأكد من رفعه على GitHub.")
    st.stop()

# -------------------------------------------------
# تحميل قوائم القيم المتاحة من ملفات processed (لتجنب إدخال قيم غير موجودة)
# -------------------------------------------------
@st.cache_data
def load_available_values(processed_dir: Path):
    f_country = processed_dir / "top4_next_actions_by_country.csv"
    f_solution = processed_dir / "top4_next_actions_by_solution.csv"
    f_cs = processed_dir / "top4_next_actions_by_country_solution.csv"

    # نقرأ ما هو موجود فقط
    countries = []
    solutions = []

    if f_country.exists():
        df_c = pd.read_csv(f_country)
        if "Country" in df_c.columns:
            countries = sorted(set(df_c["Country"].astype(str).str.strip().str.upper()))

    if f_solution.exists():
        df_s = pd.read_csv(f_solution)
        if "solution" in df_s.columns:
            solutions = sorted(set(df_s["solution"].astype(str).str.strip().str.upper()))

    # إذا ملف country_solution موجود قد يحتوي حلول/دول إضافية
    if f_cs.exists():
        df_cs = pd.read_csv(f_cs)
        if "Country" in df_cs.columns:
            cs_countries = set(df_cs["Country"].astype(str).str.strip().str.upper())
            countries = sorted(set(countries) | cs_countries)
        if "solution" in df_cs.columns:
            cs_solutions = set(df_cs["solution"].astype(str).str.strip().str.upper())
            solutions = sorted(set(solutions) | cs_solutions)

    return countries, solutions

countries_list, solutions_list = load_available_values(PROCESSED_DIR)

# -------------------------------------------------
# تهيئة النظام في session_state
# -------------------------------------------------
if "cjs" not in st.session_state:
    st.session_state.cjs = CustomerJourneySystem(processed_dir=PROCESSED_DIR)

cjs = st.session_state.cjs

# -------------------------------------------------
# اختيار العملية من الشريط الجانبي (عربي بالكامل)
# -------------------------------------------------
العملية = st.sidebar.radio(
    "اختر العملية:",
    ["إضافة حساب جديد", "إضافة إجراء لحساب"]
)

# -------------------------------------------------
# واجهة إدخال موحدة (قائمة بدل نص)
# -------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.write("ملاحظة: يتم عرض الدول/الحلول المتاحة من ملفات data/processed لتجنب إدخال قيم غير موجودة.")

# -------------------------------------------------
# 1) إضافة حساب جديد
# -------------------------------------------------
if العملية == "إضافة حساب جديد":
    st.header("إضافة حساب جديد")

    with st.form("نموذج_إضافة_حساب"):
        account_id = st.text_input("معرّف الحساب", value="A001")

        if countries_list:
            country = st.selectbox("الدولة", options=countries_list, index=0)
        else:
            country = st.text_input("الدولة (لم يتم العثور على قائمة دول في البيانات)")

        if solutions_list:
            solution = st.selectbox("الحل", options=solutions_list, index=0)
        else:
            solution = st.text_input("الحل (لم يتم العثور على قائمة حلول في البيانات)")

        تنفيذ = st.form_submit_button("تنفيذ")

    if تنفيذ:
        account_id = (account_id or "").strip()
        country = (country or "").strip().upper()
        solution = (solution or "").strip().upper()

        if not account_id or not country or not solution:
            st.error("يرجى تعبئة جميع الحقول قبل التنفيذ.")
            st.stop()

        result = cjs.add_account(account_id=account_id, country=country, solution=solution)

        st.subheader("النتائج")

        # Country
        st.write("أفضل 4 إجراءات حسب الدولة")
        if result.get("top4_by_country"):
            st.dataframe(pd.DataFrame(result["top4_by_country"]), use_container_width=True)
        else:
            st.warning("لا توجد نتائج لهذه الدولة ضمن البيانات.")

        # Solution
        st.write("أفضل 4 إجراءات حسب الحل")
        if result.get("top4_by_solution"):
            st.dataframe(pd.DataFrame(result["top4_by_solution"]), use_container_width=True)
        else:
            st.warning(
                "لا توجد نتائج لهذا الحل ضمن البيانات. "
                "السبب غالباً أن قيمة الحل غير موجودة في ملفات processed."
            )

        # Country + Solution
        st.write("أفضل 4 إجراءات حسب الدولة والحل")
        if result.get("top4_by_country_solution"):
            st.dataframe(pd.DataFrame(result["top4_by_country_solution"]), use_container_width=True)
        else:
            st.warning(
                "لا توجد نتائج لهذا الجمع (الدولة + الحل) ضمن البيانات. "
                "جرّب اختيار حل مختلف أو تأكد من وجوده في ملف top4_next_actions_by_country_solution.csv."
            )

# -------------------------------------------------
# 2) إضافة إجراء لحساب (add_action)
# -------------------------------------------------
else:
    st.header("إضافة إجراء وتحديث الأوزان")

    with st.form("نموذج_إضافة_إجراء"):
        account_id = st.text_input("معرّف الحساب", value="A001")

        if countries_list:
            country = st.selectbox("الدولة", options=countries_list, index=0)
        else:
            country = st.text_input("الدولة (لم يتم العثور على قائمة دول في البيانات)")

        if solutions_list:
            solution = st.selectbox("الحل", options=solutions_list, index=0)
        else:
            solution = st.text_input("الحل (لم يتم العثور على قائمة حلول في البيانات)")

        action_type = st.selectbox("نوع الإجراء", options=list(DEFAULT_BASE_WEIGHTS.keys()))
        تنفيذ = st.form_submit_button("تنفيذ")

    if تنفيذ:
        account_id = (account_id or "").strip()
        country = (country or "").strip().upper()
        solution = (solution or "").strip().upper()

        if not account_id or not country or not solution:
            st.error("يرجى تعبئة جميع الحقول قبل التنفيذ.")
            st.stop()

        result = cjs.add_action(
            account_id=account_id,
            country=country,
            solution=solution,
            action_type=action_type,
        )

        st.subheader("النتائج")
        st.write(f"معرّف الحساب: {result.get('account_id','')}")
        st.write(f"الإجراء المضاف: {result.get('added_action','')}")
        st.write(f"الوزن المعدّل: {result.get('adjusted_weight','')}")

        st.write("أفضل 4 إجراءات حسب الدولة (بعد التحديث)")
        st.dataframe(pd.DataFrame(result.get("top4_by_country", [])), use_container_width=True)

        st.write("أفضل 4 إجراءات حسب الحل (بعد التحديث)")
        if result.get("top4_by_solution"):
            st.dataframe(pd.DataFrame(result["top4_by_solution"]), use_container_width=True)
        else:
            st.warning("لا توجد نتائج لهذا الحل ضمن البيانات، لذلك لا يمكن عرض Top 4 حسب الحل.")

        st.write("أفضل 4 إجراءات حسب الدولة والحل (بعد التحديث)")
        if result.get("top4_by_country_solution"):
            st.dataframe(pd.DataFrame(result["top4_by_country_solution"]), use_container_width=True)
        else:
            st.warning("لا توجد نتائج لهذا الجمع (الدولة + الحل) ضمن البيانات.")
