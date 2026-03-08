import streamlit as st
import asyncio
import aiohttp
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.streamlit_app.components.defect_form import render_defect_form
from src.streamlit_app.components.results_viewer import render_results
from src.streamlit_app.components.charts import create_investigation_dashboard
from src.streamlit_app.utils.session_state import init_session_state
import logging

# Configure page
st.set_page_config(
    page_title="CAPA Autonomous Investigation System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        padding: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        padding: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .status-completed {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-in-progress {
        color: #FFC107;
        font-weight: bold;
    }
    .status-failed {
        color: #F44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
init_session_state()

# API endpoints
API_BASE_URL = "http://localhost:8000"
API_ENDPOINTS = {
    "submit_investigation": f"{API_BASE_URL}/api/v1/investigations",
    "get_investigation": f"{API_BASE_URL}/api/v1/investigations/{{id}}",
    "list_investigations": f"{API_BASE_URL}/api/v1/investigations",
    "get_metrics": f"{API_BASE_URL}/api/v1/metrics"
}

async def submit_investigation(defect_data: dict) -> dict:
    """Submit investigation request to API"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            API_ENDPOINTS["submit_investigation"],
            json=defect_data,
            headers={"Authorization": f"Bearer {st.session_state.auth_token}"}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                st.error(f"Failed to submit investigation: {await response.text()}")
                return None

async def get_investigation_status(investigation_id: str) -> dict:
    """Get investigation status from API"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            API_ENDPOINTS["get_investigation"].format(id=investigation_id),
            headers={"Authorization": f"Bearer {st.session_state.auth_token}"}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

async def get_all_investigations() -> list:
    """Get all investigations from API"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            API_ENDPOINTS["list_investigations"],
            headers={"Authorization": f"Bearer {st.session_state.auth_token}"}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return []

async def get_system_metrics() -> dict:
    """Get system metrics from API"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            API_ENDPOINTS["get_metrics"],
            headers={"Authorization": f"Bearer {st.session_state.auth_token}"}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {}

def main():
    """Main application"""
    
    # Header
    st.markdown('<h1 class="main-header">🔍 CAPA Autonomous Investigation System</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100?text=CAPA+AI", use_column_width=True)
        st.markdown("## Navigation")
        
        page = st.radio(
            "Select Page",
            ["New Investigation", "View Investigations", "Dashboard", "System Health"]
        )
        
        st.markdown("---")
        st.markdown("## User")
        st.write(f"**User:** {st.session_state.username}")
        st.write(f"**Role:** Quality Engineer")
        
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    
    # Main content based on selected page
    if page == "New Investigation":
        render_new_investigation()
    elif page == "View Investigations":
        asyncio.run(render_view_investigations())
    elif page == "Dashboard":
        asyncio.run(render_dashboard())
    elif page == "System Health":
        asyncio.run(render_system_health())

def render_new_investigation():
    """Render new investigation form"""
    st.markdown('<h2 class="sub-header">Submit New Defect Investigation</h2>', 
                unsafe_allow_html=True)
    
    # Render form
    defect_data = render_defect_form()
    
    if defect_data and st.button("Start Investigation", type="primary"):
        with st.spinner("Initiating autonomous investigation..."):
            # Submit investigation
            result = asyncio.run(submit_investigation(defect_data))
            
            if result:
                st.success(f"Investigation initiated successfully!")
                st.info(f"Investigation ID: {result['investigation_id']}")
                
                # Store in session
                st.session_state.current_investigation = result['investigation_id']
                
                # Show progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Poll for status
                import time
                for i in range(10):
                    time.sleep(2)  # Wait 2 seconds
                    status = asyncio.run(get_investigation_status(result['investigation_id']))
                    
                    if status:
                        progress = i * 10
                        progress_bar.progress(progress)
                        status_text.text(f"Status: {status.get('status', 'in_progress')}")
                        
                        if status.get('status') == 'completed':
                            st.balloons()
                            st.success("Investigation completed!")
                            break
                        elif status.get('status') == 'failed':
                            st.error(f"Investigation failed: {status.get('error', 'Unknown error')}")
                            break
                
                # Show results button
                if st.button("View Results"):
                    st.session_state.view_investigation = result['investigation_id']
                    st.rerun()

async def render_view_investigations():
    """Render investigations list and details"""
    st.markdown('<h2 class="sub-header">Investigation Results</h2>', 
                unsafe_allow_html=True)
    
    # Get all investigations
    investigations = await get_all_investigations()
    
    if not investigations:
        st.info("No investigations found. Start a new investigation to see results here.")
        return
    
    # Create DataFrame for display
    df = pd.DataFrame(investigations)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=df['status'].unique() if 'status' in df.columns else []
        )
    with col2:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now().date(), datetime.now().date())
        )
    
    # Apply filters
    if status_filter and 'status' in df.columns:
        df = df[df['status'].isin(status_filter)]
    
    # Display investigations
    for _, investigation in df.iterrows():
        with st.expander(
            f"🔍 {investigation.get('defect_report', {}).get('title', 'Untitled')} "
            f"({investigation.get('investigation_id', 'N/A')})"
        ):
            cols = st.columns(4)
            cols[0].metric("Status", investigation.get('status', 'N/A'))
            cols[1].metric("Severity", investigation.get('defect_report', {}).get('severity', 'N/A'))
            cols[2].metric("Findings", len(investigation.get('findings', [])))
            cols[3].metric("Completion", investigation.get('completion_time', 'N/A'))
            
            if st.button("View Full Report", key=investigation.get('investigation_id')):
                st.session_state.selected_investigation = investigation.get('investigation_id')
    
    # Show selected investigation details
    if 'selected_investigation' in st.session_state:
        investigation_id = st.session_state.selected_investigation
        investigation = next(
            (inv for inv in investigations if inv.get('investigation_id') == investigation_id),
            None
        )
        
        if investigation:
            st.markdown("---")
            render_results(investigation)

async def render_dashboard():
    """Render analytics dashboard"""
    st.markdown('<h2 class="sub-header">Investigation Analytics Dashboard</h2>', 
                unsafe_allow_html=True)
    
    # Get all investigations
    investigations = await get_all_investigations()
    
    if not investigations:
        st.info("No data available for dashboard.")
        return
    
    df = pd.DataFrame(investigations)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Investigations", len(df))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        completed = len(df[df['status'] == 'completed']) if 'status' in df.columns else 0
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Completed", completed)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        in_progress = len(df[df['status'] == 'in_progress']) if 'status' in df.columns else 0
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("In Progress", in_progress)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        avg_findings = df['findings'].apply(len).mean() if 'findings' in df.columns else 0
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Avg Findings", f"{avg_findings:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        if 'severity' in df.columns:
            severity_counts = df['severity'].value_counts()
            fig = px.pie(
                values=severity_counts.values,
                names=severity_counts.index,
                title="Investigations by Severity"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'status' in df.columns:
            status_counts = df['status'].value_counts()
            fig = px.bar(
                x=status_counts.index,
                y=status_counts.values,
                title="Investigations by Status",
                labels={'x': 'Status', 'y': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Timeline
    if 'completion_time' in df.columns:
        df['completion_date'] = pd.to_datetime(df['completion_time']).dt.date
        timeline = df.groupby('completion_date').size().reset_index(name='count')
        fig = px.line(
            timeline,
            x='completion_date',
            y='count',
            title="Investigation Timeline"
        )
        st.plotly_chart(fig, use_container_width=True)

async def render_system_health():
    """Render system health monitoring"""
    st.markdown('<h2 class="sub-header">System Health Monitoring</h2>', 
                unsafe_allow_html=True)
    
    # Get system metrics
    metrics = await get_system_metrics()
    
    # Agent health
    st.subheader("Agent Status")
    if 'agent_health' in metrics:
        agent_data = metrics['agent_health']
        for agent, status in agent_data.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(f"**{agent}**")
            
            if status.get('status') == 'healthy':
                col2.markdown('<span class="status-completed">✅ Healthy</span>', 
                            unsafe_allow_html=True)
            else:
                col2.markdown('<span class="status-failed">❌ Unhealthy</span>', 
                            unsafe_allow_html=True)
            
            col3.write(f"Response: {status.get('response_time', 0)}ms")
    
    # Tool status
    st.subheader("Tool Status")
    if 'tool_health' in metrics:
        tool_data = metrics['tool_health']
        cols = st.columns(3)
        for i, (tool, status) in enumerate(tool_data.items()):
            with cols[i % 3]:
                st.markdown(f"**{tool}**")
                if status.get('available'):
                    st.success("Available")
                else:
                    st.error("Unavailable")
    
    # API metrics
    st.subheader("API Metrics")
    if 'api_metrics' in metrics:
        api_data = metrics['api_metrics']
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Requests", api_data.get('total_requests', 0))
        col2.metric("Avg Response Time", f"{api_data.get('avg_response_time', 0)}ms")
        col3.metric("Error Rate", f"{api_data.get('error_rate', 0)}%")
    
    # Resource usage
    st.subheader("Resource Usage")
    if 'resources' in metrics:
        resource_data = metrics['resources']
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=resource_data.get('timestamps', []),
            y=resource_data.get('cpu_usage', []),
            name='CPU Usage',
            mode='lines'
        ))
        
        fig.add_trace(go.Scatter(
            x=resource_data.get('timestamps', []),
            y=resource_data.get('memory_usage', []),
            name='Memory Usage',
            mode='lines'
        ))
        
        fig.update_layout(
            title="Resource Usage Over Time",
            xaxis_title="Time",
            yaxis_title="Usage %"
        )
        
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
