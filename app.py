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
FILE_CS = PROCESSED_DIR / "top4_next_actions_by_country_solution.csv"
FILE_C = PROCESSED_DIR / "top4_next_actions_by_country.csv"
FILE_S = PROCESSED_DIR / "top4_next_actions_by_solution.csv"

# -------------------------------------------------
# تحقق من وجود البيانات
# -------------------------------------------------
if not PROCESSED_DIR.exists():
    st.error("المجلد data/processed غير موجود داخل المستودع. تأكد من رفعه على GitHub.")
    st.stop()

# -------------------------------------------------
# تحميل قائمة الدول والحلول المتاحة لكل دولة (Country -> [Solutions])
# -------------------------------------------------
@st.cache_data
def load_country_solution_map(path_cs: Path):
    if not path_cs.exists():
        return {}, []

    df = pd.read_csv(path_cs)

    # تأكد من أسماء الأعمدة المتوقعة
    if "Country" not in df.columns or "solution" not in df.columns:
        return {}, []

    df["Country"] = df["Country"].astype(str).str.strip().str.upper()
    df["solution"] = df["solution"].astype(str).str.strip().str.upper()

    mapping = (
        df.groupby("Country")["solution"]
          .apply(lambda s: sorted(set(s.tolist())))
          .to_dict()
    )
    countries = sorted(mapping.keys())
    return mapping, countries

country_to_solutions, countries_list = load_country_solution_map(FILE_CS)

# -------------------------------------------------
# تهيئة النظام في session_state
# -------------------------------------------------
if "cjs" not in st.session_state:
    st.session_state.cjs = CustomerJourneySystem(processed_dir=PROCESSED_DIR)

cjs = st.session_state.cjs

# -------------------------------------------------
# اختيار العملية من الشريط الجانبي
# -------------------------------------------------
العملية = st.sidebar.radio(
    "اختر العملية:",
    ["إضافة حساب جديد", "إضافة إجراء لحساب"]
)

# -------------------------------------------------
# دالة مساعدة لعرض الجداول أو التحذير
# -------------------------------------------------
def show_table(title: str, records: list, empty_msg: str):
    st.write(title)
    if records:
        st.dataframe(pd.DataFrame(records), use_container_width=True)
    else:
        st.warning(empty_msg)

# -------------------------------------------------
# إدخال موحد: الدولة ثم الحل (الحل مرتبط بالدولة)
# -------------------------------------------------
def country_solution_inputs():
    st.subheader("بيانات الحساب")

    account_id = st.text_input("معرّف الحساب", value="A001")

    if countries_list:
        country = st.selectbox("الدولة", options=countries_list, index=0)
        solutions_for_country = country_to_solutions.get(country, [])
        if solutions_for_country:
            solution = st.selectbox("الحل (متاح لهذه الدولة فقط)", options=solutions_for_country, index=0)
        else:
            solution = ""
            st.warning("لا توجد حلول متاحة لهذه الدولة ضمن ملف (الدولة + الحل).")
    else:
        # إذا لم نستطع تحميل mapping لأي سبب
        country = st.text_input("الدولة (لم يتم العثور على قائمة دول)")
        solution = st.text_input("الحل (لم يتم العثور على قائمة حلول)")

    # تنظيف
    account_id = (account_id or "").strip()
    country = (country or "").strip().upper()
    solution = (solution or "").strip().upper()

    return account_id, country, solution

# -------------------------------------------------
# 1) إضافة حساب جديد
# -------------------------------------------------
if العملية == "إضافة حساب جديد":
    st.header("إضافة حساب جديد")

    with st.form("نموذج_إضافة_حساب"):
        account_id, country, solution = country_solution_inputs()
        تنفيذ = st.form_submit_button("تنفيذ")

    if تنفيذ:
        if not account_id or not country or not solution:
            st.error("يرجى تعبئة جميع الحقول قبل التنفيذ.")
            st.stop()

        result = cjs.add_account(account_id=account_id, country=country, solution=solution)

        st.subheader("النتائج")

        show_table(
            "أفضل 4 إجراءات حسب الدولة",
            result.get("top4_by_country", []),
            "لا توجد نتائج لهذه الدولة ضمن البيانات."
        )

        show_table(
            "أفضل 4 إجراءات حسب الحل",
            result.get("top4_by_solution", []),
            "لا توجد نتائج لهذا الحل ضمن البيانات."
        )

        show_table(
            "أفضل 4 إجراءات حسب الدولة والحل",
            result.get("top4_by_country_solution", []),
            "لا توجد نتائج لهذه التركيبة (الدولة + الحل) ضمن البيانات."
        )

# -------------------------------------------------
# 2) إضافة إجراء لحساب
# -------------------------------------------------
else:
    st.header("إضافة إجراء وتحديث الأوزان")

    with st.form("نموذج_إضافة_إجراء"):
        account_id, country, solution = country_solution_inputs()
        action_type = st.selectbox("نوع الإجراء", options=list(DEFAULT_BASE_WEIGHTS.keys()))
        تنفيذ = st.form_submit_button("تنفيذ")

    if تنفيذ:
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

        show_table(
            "أفضل 4 إجراءات حسب الدولة (بعد التحديث)",
            result.get("top4_by_country", []),
            "لا توجد نتائج لهذه الدولة ضمن البيانات."
        )

        show_table(
            "أفضل 4 إجراءات حسب الحل (بعد التحديث)",
            result.get("top4_by_solution", []),
            "لا توجد نتائج لهذا الحل ضمن البيانات."
        )

        show_table(
            "أفضل 4 إجراءات حسب الدولة والحل (بعد التحديث)",
            result.get("top4_by_country_solution", []),
            "لا توجد نتائج لهذه التركيبة (الدولة + الحل) ضمن البيانات."
        )
