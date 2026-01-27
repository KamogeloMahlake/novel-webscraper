import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Database connection
@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )

def fetch_process_logs():
    """Simulate process logs from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) as total_novels,
                   COUNT(CASE WHEN fanfic_id IS NOT NULL THEN 1 END) as fanficnet_novels,
                   COUNT(CASE WHEN last_chapter_scraped IS NOT NULL AND fanfic_id IS NULL THEN 1 END) as novelbin_novels,
                   COUNT(CASE WHEN fanfic_id IS NULL AND last_chapter_scraped IS NULL THEN 1 END) as ao3_novels
            FROM novel_novel
        """)
        stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) as total_chapters FROM novel_chapter
        """)
        chapters = cursor.fetchone()[0]
        
        cursor.close()
        return {
            'total_novels': stats[0],
            'fanficnet': stats[1],
            'novelbin': stats[2],
            'ao3': stats[3],
            'total_chapters': chapters
        }
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

st.set_page_config(page_title="Scraper Process Visualization", layout="wide")

st.title("🔄 Novel Scraper Process Flow")
st.markdown("Visualization of the scraping workflow and data processing pipeline")

# Get process statistics
process_stats = fetch_process_logs()

if process_stats:
    # Process flow diagram using Plotly Sankey
    st.subheader("Data Flow Pipeline")
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=[
                "User Input",
                "NovelBin",
                "FanFiction.net",
                "AO3",
                "Parse Metadata",
                "Extract Chapters",
                "Database Insert",
                "Image Download",
                "Novel Stored",
                "Chapter Stored"
            ],
            color=[
                "#FF6B6B",  # User Input
                "#4ECDC4",  # NovelBin
                "#45B7D1",  # FanFiction.net
                "#FFA07A",  # AO3
                "#98D8C8",  # Parse Metadata
                "#F7DC6F",  # Extract Chapters
                "#BB8FCE",  # Database Insert
                "#85C1E2",  # Image Download
                "#52C41A",  # Novel Stored
                "#1890FF"   # Chapter Stored
            ]
        ),
        link=dict(
            source=[0, 0, 0, 1, 2, 3, 4, 4, 5, 6, 6, 7, 8, 9],
            target=[1, 2, 3, 4, 4, 4, 5, 7, 6, 8, 9, 8, 9, 9],
            value=[process_stats['novelbin'], process_stats['fanficnet'], process_stats['ao3'], 
                   process_stats['total_novels'], process_stats['total_novels'], process_stats['total_novels'],
                   process_stats['total_chapters'], process_stats['total_novels'], process_stats['total_chapters'],
                   process_stats['total_novels'], process_stats['total_chapters'], process_stats['total_novels'],
                   process_stats['total_novels'], process_stats['total_chapters']]
        )
    )],
    layout=go.Layout(
        title="Data Processing Pipeline",
        font=dict(size=12),
        height=500
    ))
    
    st.plotly_chart(fig, use_container_width=True)

# Process stages visualization
st.divider()

st.subheader("Main Scraping Workflow Stages")

stages_data = {
    'Stage': [
        '1. User Selection',
        '2. Site Connection',
        '3. URL Input/Search',
        '4. Parse Content',
        '5. Extract Metadata',
        '6. Download Chapters',
        '7. Save to Database',
        '8. Download Images',
        '9. Completion'
    ],
    'Description': [
        'User chooses scraping source (NovelBin, FanFiction.net, AO3)',
        'Initialize scraper class for selected source',
        'User provides URL or search terms',
        'Scraper fetches and parses HTML content',
        'Extract title, author, description, image URL',
        'Extract all chapter titles and content',
        'Insert novel metadata and chapters into PostgreSQL',
        'Download cover images to ./media/novel-images/',
        'User can continue or return to main menu'
    ],
    'Status': ['Ready', 'Connected', 'Received', 'Processing', 'Extracted', 'Fetched', 'Stored', 'Downloaded', 'Complete']
}

stages_df = pd.DataFrame(stages_data)

# Create a timeline visualization
fig = go.Figure()

colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2', '#52C41A']

for idx, (stage, desc, status) in enumerate(zip(stages_df['Stage'], stages_df['Description'], stages_df['Status'])):
    fig.add_trace(go.Bar(
        y=[stage],
        x=[idx + 1],
        orientation='h',
        marker=dict(color=colors[idx], line=dict(color='white', width=2)),
        text=status,
        textposition='auto',
        hovertemplate=f"<b>{stage}</b><br>{desc}<extra></extra>",
        showlegend=False
    ))

fig.update_layout(
    title="Sequential Processing Steps",
    xaxis_title="Step Number",
    yaxis_title="Process Stage",
    height=500,
    barmode='overlay',
    xaxis=dict(type='linear', range=[0, 10]),
    hovermode='closest'
)

st.plotly_chart(fig, use_container_width=True)

# Process decision tree
st.divider()
st.subheader("Update & Maintenance Workflows")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Update Process")
    st.markdown("""
    **Path 1: Chapter Update**
    - Query novels with `last_chapter_scraped` URL
    - Use NovelBin scraper for updates
    - Fetch new chapters from that point
    - Insert new chapters to database
    
    **Path 2: Metadata Update**
    - Query novels with `fanfic_id`
    - Fetch updated metadata from FanFiction.net
    - Download new cover images
    - Update description in database
    """)
    
    # Update paths visualization
    update_data = {
        'Path': ['Chapter Update', 'Metadata Update'],
        'Novels': [
            process_stats['novelbin'],
            process_stats['fanficnet']
        ]
    }
    update_df = pd.DataFrame(update_data)
    
    fig_update = px.bar(update_df, x='Path', y='Novels', 
                        color='Path',
                        color_discrete_map={'Chapter Update': '#4ECDC4', 'Metadata Update': '#45B7D1'},
                        text='Novels')
    fig_update.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig_update, use_container_width=True)

with col2:
    st.markdown("### Data Statistics")
    
    if process_stats:
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("📖 Total Novels", process_stats['total_novels'])
        with col_stat2:
            st.metric("📄 Total Chapters", process_stats['total_chapters'])
        
        st.divider()
        
        col_stat3, col_stat4, col_stat5 = st.columns(3)
        with col_stat3:
            st.metric("🌐 FanFiction.net", process_stats['fanficnet'])
        with col_stat4:
            st.metric("📕 NovelBin", process_stats['novelbin'])
        with col_stat5:
            st.metric("🎨 AO3", process_stats['ao3'])

# Error handling flow
st.divider()
st.subheader("Error Handling & Edge Cases")

error_cases = pd.DataFrame({
    'Scenario': [
        'Duplicate Novel',
        'Image Download Failed',
        'Database Connection Error',
        'Invalid URL',
        'Network Timeout',
        'Keyboard Interrupt'
    ],
    'Handling': [
        'Skip insertion, retrieve existing ID',
        'Log error, continue without image',
        'Rollback transaction, show error',
        'Prompt for new input',
        'Retry request with timeout',
        'Graceful exit, close connection'
    ],
    'Recovery': [
        '✓ Automatic',
        '✓ Partial',
        '✗ Manual',
        '✓ Automatic',
        '✓ Automatic',
        '✓ Automatic'
    ]
})

st.dataframe(error_cases, use_container_width=True, hide_index=True)

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col2:
    st.caption(f"Dashboard updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
