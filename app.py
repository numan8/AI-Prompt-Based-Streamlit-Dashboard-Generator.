import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

st.set_page_config(
    page_title="AI Dashboard Generator",
    page_icon="📊",
    layout="wide"
)

# ---------- Styling ----------
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
.card {
    background: white;
    padding: 22px;
    border-radius: 18px;
    box-shadow: 0px 4px 18px rgba(0,0,0,0.07);
}
.metric-card {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    color: white;
    padding: 22px;
    border-radius: 18px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ---------- OpenAI ----------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ---------- Header ----------
st.markdown('<div class="main-title">📊 AI Dashboard Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Upload your data, write a prompt, and generate dashboard insights instantly.</div>', unsafe_allow_html=True)

st.divider()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Dashboard Settings")
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
    chart_type = st.selectbox(
        "Select Chart Type",
        ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Box Plot"]
    )

# ---------- Load Data ----------
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📁 Data Preview")
    st.dataframe(df.head(), use_container_width=True)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()

    # ---------- Metrics ----------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{df.shape[0]}</h3>
            <p>Total Rows</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{df.shape[1]}</h3>
            <p>Total Columns</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(numeric_cols)}</h3>
            <p>Numeric Columns</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{df.isnull().sum().sum()}</h3>
            <p>Missing Values</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ---------- Prompt ----------
    st.subheader("💬 Write Your Dashboard Prompt")

    user_prompt = st.text_area(
        "Example: Create sales dashboard by region and explain key trends",
        height=120
    )

    col_x, col_y = st.columns(2)

    with col_x:
        x_axis = st.selectbox("Select X-axis", all_cols)

    with col_y:
        y_axis = st.selectbox("Select Y-axis", numeric_cols if numeric_cols else all_cols)

    # ---------- Chart ----------
    if st.button("🚀 Generate Dashboard", use_container_width=True):
        st.subheader("📈 Generated Visualization")

        try:
            if chart_type == "Bar Chart":
                fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")

            elif chart_type == "Line Chart":
                fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} Trend by {x_axis}")

            elif chart_type == "Scatter Plot":
                fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")

            elif chart_type == "Pie Chart":
                fig = px.pie(df, names=x_axis, values=y_axis, title=f"{y_axis} Share by {x_axis}")

            elif chart_type == "Box Plot":
                fig = px.box(df, x=x_axis, y=y_axis, title=f"{y_axis} Distribution by {x_axis}")

            fig.update_layout(
                template="plotly_white",
                title_font_size=24,
                height=550
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Chart error: {e}")

        # ---------- AI Interpretation ----------
        st.subheader("🧠 AI Interpretation")

        sample_data = df.head(20).to_string()

        ai_prompt = f"""
        You are a business data analyst.

        User request:
        {user_prompt}

        Dataset columns:
        {list(df.columns)}

        Data sample:
        {sample_data}

        Selected chart:
        {chart_type}
        X-axis: {x_axis}
        Y-axis: {y_axis}

        Write a short professional dashboard interpretation.
        Include:
        1. Key insight
        2. Business meaning
        3. Suggested action

        Keep it concise.
        """

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a professional data analyst."},
                {"role": "user", "content": ai_prompt}
            ]
        )

        interpretation = response.choices[0].message.content
        st.success(interpretation)

else:
    st.info("👈 Upload a CSV or Excel file to start.")
