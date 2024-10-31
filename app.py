import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
import plotly.express as px
from PIL import Image
import requests


# -------------------- Page Configuration --------------------
st.set_page_config(
    page_title="Streamlit Feature Showcase",
    page_icon="✨",
    layout="wide",  # Can be "centered" or "wide"
    initial_sidebar_state="expanded",  # Can be "auto", "expanded", "collapsed"
)

css = """
<style>
.st-ay:hover {
    cursor: pointer !important;
    }

</style>
"""




# Apply the CSS
st.markdown(css, unsafe_allow_html=True)




# -------------------- Sidebar Navigation --------------------
st.sidebar.title("Navigation")
app_mode = st.sidebar.selectbox("Choose the section:", [
    "Introduction",
    "Layout",
    "Widgets",
    "Data Display",
    "Charts & Graphs",
    "Media",
    "Interactivity",
    "Caching",
    "Theming",
    "Advanced",
])

# -------------------- Introduction --------------------
if app_mode == "Introduction":
    st.title("✨ Streamlit Feature Showcase")
    st.markdown("""
    Welcome to the **Streamlit Feature Showcase**! This application demonstrates the various features that Streamlit offers to create interactive and dynamic web applications with ease.

    **Features Covered:**
    - Layout Management
    - Widgets
    - Data Display
    - Charts & Graphs
    - Media Handling
    - Interactivity
    - Caching
    - Theming
    - Advanced Features

    Navigate through the sidebar to explore each section in detail.
    """)

# -------------------- Layout --------------------
elif app_mode == "Layout":
    st.title("📐 Layout Management")

    st.header("Columns")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("Button 1")
    with col2:
        st.button("Button 2")
    with col3:
        st.button("Button 3")

    st.header("Expander")
    with st.expander("See explanation"):
        st.write("""
            The expander is useful for hiding content that can be revealed upon user interaction.
        """)

    st.header("Tabs")
    tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])
    with tab1:
        st.write("Content in Tab 1")
    with tab2:
        st.write("Content in Tab 2")
    with tab3:
        st.write("Content in Tab 3")

    st.header("Container")
    with st.container():
        st.write("This is inside a container.")
        st.slider("Slider inside container", 0, 100, 50)

# -------------------- Widgets --------------------
elif app_mode == "Widgets":
    st.title("🛠️ Widgets")

    st.header("Input Widgets")
    text_input = st.text_input("Enter some text:", "Hello Streamlit!")
    st.write("You entered:", text_input)

    number_input = st.number_input("Enter a number:", min_value=0, max_value=100, value=25)
    st.write("Number selected:", number_input)

    date_input = st.date_input("Select a date")
    st.write("Date selected:", date_input)

    st.header("Selection Widgets")
    option = st.selectbox("Choose an option:", ["Option 1", "Option 2", "Option 3"])
    st.write("You selected:", option)

    multiselect = st.multiselect("Select multiple options:", ["A", "B", "C", "D"])
    st.write("You selected:", multiselect)

    st.header("Boolean Widgets")
    checkbox = st.checkbox("Check me out")
    st.write("Checkbox is:", checkbox)

    radio = st.radio("Choose one:", ["Yes", "No"])
    st.write("Radio selection:", radio)

    st.header("Buttons")
    if st.button("Click me"):
        st.write("Button clicked!")

    st.header("File Uploader")
    uploaded_file = st.file_uploader("Upload a file")
    if uploaded_file is not None:
        st.write("Filename:", uploaded_file.name)

# -------------------- Data Display --------------------
elif app_mode == "Data Display":
    st.title("📊 Data Display")

    st.header("Displaying DataFrames")
    df_data_display = pd.DataFrame({
        'A': np.random.randn(10),
        'B': np.random.rand(10),
        'C': np.random.randint(0, 100, 10)
    })
    st.dataframe(df_data_display.style.highlight_max(axis=0))
    st.table(df_data_display)

    st.header("Code Display")
    code = """
    def hello():
        print("Hello, Streamlit!")
    """
    st.code(code, language='python')

    st.header("JSON Display")
    json_data = {
        "name": "Streamlit",
        "type": "Framework",
        "features": ["Widgets", "Layouts", "Charts", "Media", "Interactivity"]
    }
    st.json(json_data)

    st.header("LaTeX")
    st.latex(r'''
        a + ar + ar^2 + ar^3 + \cdots + ar^n =
        \sum_{k=0}^{n} ar^k
    ''')

# -------------------- Charts & Graphs --------------------
elif app_mode == "Charts & Graphs":
    st.title("📈 Charts & Graphs")

    st.header("Matplotlib Integration")
    fig, ax = plt.subplots()
    ax.plot(np.random.randn(100).cumsum())
    st.pyplot(fig)

    st.header("Altair Charts")
    df_altair = pd.DataFrame({
        'x': range(100),
        'y': np.random.randn(100).cumsum()
    })
    chart = alt.Chart(df_altair).mark_line().encode(
        x='x',
        y='y'
    )
    st.altair_chart(chart, use_container_width=True)

    st.header("Plotly Charts")
    df_plotly = px.data.iris()
    fig_plotly = px.scatter(df_plotly, x='sepal_width', y='sepal_length', color='species')
    st.plotly_chart(fig_plotly, use_container_width=True)

    st.header("Vega-Lite Charts")
    df_vega_lite = pd.DataFrame({
        'x': range(50),
        'y': np.random.randn(50).cumsum()
    })
    st.vega_lite_chart(df_vega_lite, {
        'mark': 'point',
        'encoding': {
            'x': 'x',
            'y': 'y'
        }
    })

# -------------------- Media --------------------
elif app_mode == "Media":
    st.title("🎥 Media Handling")

    st.header("Images")
    img_url = "https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png"
    try:
        response = requests.get(img_url, stream=True)
        response.raise_for_status()  # Check for request errors
        img = Image.open(response.raw)
        st.image(img, caption='Streamlit Logo', use_column_width=True)
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading image: {e}")

    st.header("Audio")
    audio_file = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
    st.audio(audio_file, format='audio/mp3')

    st.header("Video")
    video_file = 'https://www.w3schools.com/html/mov_bbb.mp4'
    st.video(video_file)

    st.header("Download Button")
    df_media = pd.DataFrame({
        'Column 1': [1, 2, 3, 4],
        'Column 2': ['A', 'B', 'C', 'D']
    })
    st.download_button(
        label="Download Sample CSV",
        data=df_media.to_csv(index=False).encode('utf-8'),
        file_name='sample_data.csv',
        mime='text/csv',
    )

# -------------------- Interactivity --------------------
elif app_mode == "Interactivity":
    st.title("🔄 Interactivity")

    st.header("Session State")
    if 'count' not in st.session_state:
        st.session_state.count = 0

    def increment():
        st.session_state.count += 1

    st.button("Increment", on_click=increment)
    st.write("Count =", st.session_state.count)

    st.header("Callbacks")
    def greet(name):
        st.write(f"Hello, {name}!")

    name_input = st.text_input("Enter your name:")
    if st.button("Greet"):
        greet(name_input)

# -------------------- Caching --------------------
elif app_mode == "Caching":
    st.title("⏳ Caching")

    st.header("@st.cache")
    @st.cache_data
    def expensive_computation(n):
        # Simulate an expensive computation
        import time
        time.sleep(3)
        return np.random.randn(n)

    n = st.slider("Select number of elements:", 100, 1000, 500)
    data = expensive_computation(n)
    st.write(f"Computed {n} random numbers:")
    st.line_chart(data)

# -------------------- Theming --------------------
elif app_mode == "Theming":
    st.title("🎨 Theming")

    st.markdown("""
    Streamlit allows you to customize the look and feel of your app using themes. You can configure themes in the `config.toml` file or directly in the Streamlit Cloud settings.

    **Current Theme Settings:**
    """)

    # Retrieve theme settings using st.get_option
    theme_primary_color = st.get_option("theme.primaryColor")
    theme_background_color = st.get_option("theme.backgroundColor")
    theme_secondary_background_color = st.get_option("theme.secondaryBackgroundColor")
    theme_text_color = st.get_option("theme.textColor")
    theme_font = st.get_option("theme.font")

    st.write(f"**Primary Color:** {theme_primary_color}")
    st.write(f"**Background Color:** {theme_background_color}")
    st.write(f"**Secondary Background Color:** {theme_secondary_background_color}")
    st.write(f"**Text Color:** {theme_text_color}")
    st.write(f"**Font:** {theme_font}")

    st.markdown("""
    To customize the theme, create a `.streamlit/config.toml` file in your project directory with the following content:

    ```toml
    [theme]
    primaryColor = "#1E90FF"
    backgroundColor = "#F0F2F6"
    secondaryBackgroundColor = "#FFFFFF"
    textColor = "#262730"
    font = "sans serif"
    ```

    You can adjust the colors and font as desired.
    """)

# -------------------- Advanced --------------------
elif app_mode == "Advanced":
    st.title("🚀 Advanced Features")

    st.header("Custom Components")
    st.markdown("""
    Streamlit supports custom components, allowing you to integrate JavaScript, HTML, and CSS into your apps. This is useful for adding functionalities not natively supported by Streamlit.

    **Example:** Embedding a custom map or interactive widget.

    For more information, visit the [Streamlit Components Documentation](https://docs.streamlit.io/library/components).
    """)

    st.header("Deployment")
    st.markdown("""
    Deploy your Streamlit app easily using Streamlit Cloud, Heroku, AWS, or other cloud providers.

    **Streamlit Cloud:**
    - Free tier available
    - Automatic deployments from GitHub
    - Custom domains

    **Steps to Deploy:**
    1. Push your code to a GitHub repository.
    2. Sign in to [Streamlit Cloud](https://streamlit.io/cloud).
    3. Click "New app" and select your repository.
    4. Configure settings and deploy.

    For more details, refer to the [Deployment Guide](https://docs.streamlit.io/cloud).
    """)

# -------------------- Footer --------------------
st.sidebar.markdown("---")
st.sidebar.markdown("Built with ❤️ using [Streamlit](https://streamlit.io/)")