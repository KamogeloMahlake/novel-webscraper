import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Load environment variables
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

# Fetch data from database
def fetch_novels_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, creator, date, status, views, description 
        FROM novel_novel 
        ORDER BY date DESC
    """)
    data = cursor.fetchall()
    cursor.close()
    return pd.DataFrame(data, columns=['id', 'title', 'creator', 'date', 'status', 'views', 'description'])

def fetch_chapters_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nc.id, nc.novel_id, nc.title, nc.num, nc.date, nc.views, nn.title as novel_title
        FROM novel_chapter nc
        JOIN novel_novel nn ON nc.novel_id = nn.id
        ORDER BY nc.date DESC
    """)
    data = cursor.fetchall()
    cursor.close()
    return pd.DataFrame(data, columns=['id', 'novel_id', 'title', 'num', 'date', 'views', 'novel_title'])

def fetch_source_distribution():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN fanfic_id IS NOT NULL THEN 1 END) as fanficnet_count,
            COUNT(CASE WHEN last_chapter_scraped IS NOT NULL AND fanfic_id IS NULL THEN 1 END) as novelbin_count
        FROM novel_novel
    """)
    data = cursor.fetchone()
    cursor.close()
    return data

# Page configuration
st.set_page_config(page_title="Novel Scraper Dashboard", layout="wide", initial_sidebar_state="expanded")

# Title and description
st.title("📚 Novel Scraper Dashboard")
st.markdown("Real-time analytics and insights from your novel scraping database")

# Sidebar
st.sidebar.header("Dashboard Options")
refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 5, 300, 60)

# Load data
novels_df = fetch_novels_data()
chapters_df = fetch_chapters_data()
fanficnet_count, novelbin_count = fetch_source_distribution()

# Key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📖 Total Novels", len(novels_df))

with col2:
    st.metric("📄 Total Chapters", len(chapters_df))

with col3:
    total_views = novels_df['views'].sum()
    st.metric("👁️ Total Novel Views", f"{total_views:,}")

with col4:
    chapter_views = chapters_df['views'].sum()
    st.metric("👁️ Total Chapter Views", f"{chapter_views:,}")

st.divider()

# Row 1: Charts
row1_col1, row1_col2 = st.columns(2)

# Chapters per novel (top 10)
with row1_col1:
    st.subheader("Top 10 Novels by Chapter Count")
    chapters_per_novel = chapters_df.groupby('novel_title').size().nlargest(10).reset_index(name='count')
    fig = px.bar(chapters_per_novel, x='count', y='novel_title', orientation='h', 
                 color='count', color_continuous_scale='viridis')
    fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

# Source distribution
with row1_col2:
    st.subheader("Source Distribution")
    source_data = pd.DataFrame({
        'Source': ['FanFiction.net', 'NovelBin'],
        'Count': [fanficnet_count, novelbin_count]
    })
    fig = px.pie(source_data, values='Count', names='Source', hole=0.4,
                 color_discrete_sequence=['#FF6B6B', '#4ECDC4'])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Row 2: Time-based analytics
row2_col1, row2_col2 = st.columns(2)

# Novels added over time
with row2_col1:
    st.subheader("Novels Added Over Time")
    novels_df['date_only'] = pd.to_datetime(novels_df['date'], format='%d %B %Y %H:%M').dt.date
    novels_by_date = novels_df.groupby('date_only').size().reset_index(name='count')
    fig = px.line(novels_by_date, x='date_only', y='count', markers=True,
                  title='Cumulative Novels')
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Count")
    fig.update_layout(height=400, hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

# Top 10 authors
with row2_col2:
    st.subheader("Top 10 Most Prolific Authors")
    top_authors = novels_df['creator'].value_counts().head(10).reset_index()
    top_authors.columns = ['Author', 'Novels']
    fig = px.bar(top_authors, x='Novels', y='Author', orientation='h',
                 color='Novels', color_continuous_scale='blues')
    fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Row 3: Views analytics
row3_col1, row3_col2 = st.columns(2)

# Most viewed novels
with row3_col1:
    st.subheader("Top 10 Most Viewed Novels")
    top_novels = novels_df.nlargest(10, 'views')[['title', 'views']]
    fig = px.bar(top_novels, y='title', x='views', orientation='h',
                 color='views', color_continuous_scale='oranges')
    fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

# Most viewed chapters
with row3_col2:
    st.subheader("Top 10 Most Viewed Chapters")
    top_chapters = chapters_df.nlargest(10, 'views')[['title', 'views', 'novel_title']]
    top_chapters['display'] = top_chapters['title'].str[:30] + '...'
    fig = px.bar(top_chapters, y='display', x='views', orientation='h',
                 color='views', color_continuous_scale='greens')
    fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Detailed data table
st.subheader("Recent Novels")
novels_display = novels_df[['title', 'creator', 'date', 'views']].head(15)
novels_display.columns = ['Title', 'Author', 'Date Added', 'Views']
st.dataframe(novels_display, use_container_width=True, hide_index=True)

# Footer
col1, col2, col3 = st.columns(3)
with col2:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
