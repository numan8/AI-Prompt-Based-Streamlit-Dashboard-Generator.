import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

st.set_page_config(
    page_title="AI Dashboard Generator",
    page_icon="📊",
    layout="wide"
)

# ---------- Custom CSS ----------
st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: 800;
    color: #111827;
}
.sub-title {
    font-size: 18px;
    color: #6B7280;
}
.metric-card {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: white;
    padding: 22px;
    border-radius: 18px;
    text-align: center;
    box-shadow: 0px 4px 18px rgba(0,0,0,0.12);
}
.stButton > button {
    background-color: #4F46E5;
    color: white;
    border-radius: 12px;
    height: 48px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown('<div class="main-title">📊 AI Prompt-Based Dashboard Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Upload your data, enter a prompt, generate charts, and get AI interpretation.</div>',
    unsafe_allow_html=True
)

st.divider()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")

    api_key = st.text_input(
        "🔑 Enter OpenAI API Key",
        type="password",
        placeholder="sk-..."
    )

    uploaded_file = st.file_uploader(
        "📁 Upload CSV or Excel File",
        type=["csv", "xlsx"]
    )

    chart_type = st.selectbox(
        "📊 Select Chart Type",
        ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Box Plot"]
    )

# ---------- API Key Check ----------
if not api_key:
    st.warning("Please enter your OpenAI API key in the sidebar.")
    st.stop()

client = OpenAI(api_key=api_key)

# ---------- Load Data ----------
if uploaded_file is None:
    st.info("Please upload a CSV or Excel file from the sidebar.")
    st.stop()

try:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"File loading error: {e}")
    st.stop()

# ---------- Data Preview ----------
st.subheader("📁 Data Preview")
st.dataframe(df.head(10), use_container_width=True)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
all_cols = df.columns.tolist()

if len(all_cols) == 0:
    st.error("No columns found in the uploaded file.")
    st.stop()

# ---------- KPI Cards ----------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h2>{df.shape[0]}</h2>
        <p>Total Rows</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h2>{df.shape[1]}</h2>
        <p>Total Columns</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <h2>{len(numeric_cols)}</h2>
        <p>Numeric Columns</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <h2>{df.isnull().sum().sum()}</h2>
        <p>Missing Values</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ---------- Prompt Section ----------
st.subheader("💬 Dashboard Prompt")

user_prompt = st.text_area(
    "Write what kind of dashboard you want",
    placeholder="Example: Create a sales dashboard by region and explain important trends.",
    height=120
)

col_x, col_y = st.columns(2)

with col_x:
    x_axis = st.selectbox("Select X-axis", all_cols)

with col_y:
    if numeric_cols:
        y_axis = st.selectbox("Select Y-axis", numeric_cols)
    else:
        y_axis = st.selectbox("Select Y-axis", all_cols)

# ---------- Generate Dashboard ----------
if st.button("🚀 Generate Dashboard", use_container_width=True):

    if not user_prompt.strip():
        st.warning("Please write a dashboard prompt first.")
        st.stop()

    st.subheader("📈 Generated Dashboard")

    try:
        if chart_type == "Bar Chart":
            fig = px.bar(
                df,
                x=x_axis,
                y=y_axis,
                title=f"{y_axis} by {x_axis}"
            )

        elif chart_type == "Line Chart":
            fig = px.line(
                df,
                x=x_axis,
                y=y_axis,
                title=f"{y_axis} Trend by {x_axis}"
            )

        elif chart_type == "Scatter Plot":
            fig = px.scatter(
                df,
                x=x_axis,
                y=y_axis,
                title=f"{y_axis} vs {x_axis}"
            )

        elif chart_type == "Pie Chart":
            fig = px.pie(
                df,
                names=x_axis,
                values=y_axis,
                title=f"{y_axis} Share by {x_axis}"
            )

        elif chart_type == "Box Plot":
            fig = px.box(
                df,
                x=x_axis,
                y=y_axis,
                title=f"{y_axis} Distribution by {x_axis}"
            )

        fig.update_layout(
            template="plotly_white",
            title_font_size=24,
            height=550,
            margin=dict(l=30, r=30, t=70, b=30)
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Chart generation error: {e}")
        st.stop()

    # ---------- AI Interpretation ----------
    st.subheader("🧠 AI Interpretation")

    sample_data = df.head(20).to_string()

    ai_prompt = f"""
You are a professional Business Intelligence analyst.

User dashboard request:
{user_prompt}

Dataset columns:
{list(df.columns)}

Dataset shape:
Rows: {df.shape[0]}
Columns: {df.shape[1]}

Sample data:
{sample_data}

Selected chart:
{chart_type}

X-axis:
{x_axis}

Y-axis:
{y_axis}

Write a short dashboard interpretation.

Include:
1. Key insight
2. Business meaning
3. Suggested action

Keep the response clear, professional, and concise.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert BI dashboard analyst."
                },
                {
                    "role": "user",
                    "content": ai_prompt
                }
            ]
        )

        interpretation = response.choices[0].message.content
        st.info(interpretation)

    except Exception as e:
        st.error(f"OpenAI error: {e}")
else:
    st.info("Write a prompt, select chart settings, and click Generate Dashboard.")
