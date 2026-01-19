import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SPX Backtest Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .positive {
        color: #00cc00;
    }
    .negative {
        color: #ff3333;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_trade_log(file_path: str):
    """Load trade log from Excel file"""
    try:
        df = pd.read_excel(file_path)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        return df
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()

def compute_metrics(df: pd.DataFrame) -> dict:
    """Compute performance metrics"""
    if df.empty or 'PnL' not in df.columns:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "positive_pnl": 0.0,
            "negative_pnl": 0.0,
            "wins": 0,
            "losses": 0
        }
    
    wins = (df["PnL"] > 0).sum()
    losses = (df["PnL"] < 0).sum()
    win_rate = wins / len(df) * 100 if len(df) > 0 else 0
    
    total_pnl = df["PnL"].sum()
    positive_pnl = df[df["PnL"] > 0]["PnL"].sum() if wins > 0 else 0
    negative_pnl = df[df["PnL"] < 0]["PnL"].sum() if losses > 0 else 0
    
    equity = df["PnL"].cumsum()
    drawdown = equity - equity.cummax()
    max_drawdown = drawdown.min()
    
    return {
        "trades": len(df),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "max_drawdown": max_drawdown,
        "positive_pnl": positive_pnl,
        "negative_pnl": negative_pnl,
        "wins": wins,
        "losses": losses
    }

def main():
    st.title("📈 SPX Backtest Dashboard")
    st.markdown("---")
    
    # File path
    excel_file = Path("trade_log.xlsx")
    
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        if auto_refresh:
            st.rerun()
        
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if excel_file.exists():
            file_size = excel_file.stat().st_size / 1024  # KB
            st.caption(f"File size: {file_size:.2f} KB")
    
    # Load data
    df = load_trade_log(str(excel_file))
    
    if df.empty:
        st.warning("⚠️ No trade data found. Please run the backtest first.")
        st.info("Run: `python3 backtest_daily.py`")
        return
    
    # Compute metrics
    metrics = compute_metrics(df)
    
    # KPI Cards
    st.header("📊 Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", metrics["trades"])
    
    with col2:
        win_rate_color = "normal" if metrics["win_rate"] >= 50 else "inverse"
        st.metric("Win Rate", f"{metrics['win_rate']:.2f}%", delta=None)
    
    with col3:
        pnl_color = "normal" if metrics["total_pnl"] >= 0 else "inverse"
        st.metric("Total PnL", f"${metrics['total_pnl']:.2f}", delta=None)
    
    with col4:
        st.metric("Max Drawdown", f"${metrics['max_drawdown']:.2f}", delta=None)
    
    # Additional metrics
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("Wins", metrics["wins"])
    
    with col6:
        st.metric("Losses", metrics["losses"])
    
    with col7:
        st.metric("Total Positive PnL", f"${metrics['positive_pnl']:.2f}")
    
    with col8:
        st.metric("Total Negative PnL", f"${metrics['negative_pnl']:.2f}")
    
    st.markdown("---")
    
    # Charts Row 1
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📈 Equity Curve")
        if 'Date' in df.columns and 'PnL' in df.columns:
            df_sorted = df.sort_values('Date').copy()
            df_sorted['Cumulative PnL'] = df_sorted['PnL'].cumsum()
            
            fig_equity = go.Figure()
            fig_equity.add_trace(go.Scatter(
                x=df_sorted['Date'],
                y=df_sorted['Cumulative PnL'],
                mode='lines+markers',
                name='Equity',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            fig_equity.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_equity.update_layout(
                xaxis_title="Date",
                yaxis_title="Cumulative PnL ($)",
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_equity, use_container_width=True)
        else:
            st.info("Date or PnL column not found")
    
    with col_chart2:
        st.subheader("📊 PnL Distribution")
        if 'PnL' in df.columns:
            fig_pnl = px.histogram(
                df,
                x='PnL',
                nbins=20,
                title="PnL Distribution",
                labels={'PnL': 'PnL ($)', 'count': 'Frequency'},
                color_discrete_sequence=['#1f77b4']
            )
            fig_pnl.add_vline(x=0, line_dash="dash", line_color="red", opacity=0.5)
            fig_pnl.update_layout(height=400)
            st.plotly_chart(fig_pnl, use_container_width=True)
        else:
            st.info("PnL column not found")
    
    # Charts Row 2
    col_chart3, col_chart4 = st.columns(2)
    
    with col_chart3:
        st.subheader("🎯 Exit Reason Breakdown")
        if 'Exit Reason' in df.columns:
            exit_counts = df['Exit Reason'].value_counts()
            fig_exit = px.pie(
                values=exit_counts.values,
                names=exit_counts.index,
                title="Exit Reasons",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_exit.update_layout(height=400)
            st.plotly_chart(fig_exit, use_container_width=True)
        else:
            st.info("Exit Reason column not found")
    
    with col_chart4:
        st.subheader("📉 Drawdown Chart")
        if 'Date' in df.columns and 'PnL' in df.columns:
            df_sorted = df.sort_values('Date').copy()
            df_sorted['Cumulative PnL'] = df_sorted['PnL'].cumsum()
            df_sorted['Running Max'] = df_sorted['Cumulative PnL'].cummax()
            df_sorted['Drawdown'] = df_sorted['Cumulative PnL'] - df_sorted['Running Max']
            
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=df_sorted['Date'],
                y=df_sorted['Drawdown'],
                mode='lines',
                fill='tozeroy',
                name='Drawdown',
                line=dict(color='red', width=2),
                fillcolor='rgba(255, 0, 0, 0.3)'
            ))
            fig_dd.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_dd.update_layout(
                xaxis_title="Date",
                yaxis_title="Drawdown ($)",
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_dd, use_container_width=True)
        else:
            st.info("Date or PnL column not found")
    
    st.markdown("---")
    
    # Trade Table
    st.header("📋 Trade Log")
    
    # Filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        if 'Type' in df.columns:
            type_filter = st.multiselect("Filter by Type", df['Type'].unique(), default=df['Type'].unique())
        else:
            type_filter = []
    
    with col_filter2:
        if 'Exit Reason' in df.columns:
            exit_filter = st.multiselect("Filter by Exit Reason", df['Exit Reason'].unique(), default=df['Exit Reason'].unique())
        else:
            exit_filter = []
    
    with col_filter3:
        if 'Result' in df.columns:
            result_filter = st.multiselect("Filter by Result", df['Result'].unique(), default=df['Result'].unique())
        else:
            result_filter = []
    
    # Apply filters
    df_filtered = df.copy()
    if 'Type' in df.columns and type_filter:
        df_filtered = df_filtered[df_filtered['Type'].isin(type_filter)]
    if 'Exit Reason' in df.columns and exit_filter:
        df_filtered = df_filtered[df_filtered['Exit Reason'].isin(exit_filter)]
    if 'Result' in df.columns and result_filter:
        df_filtered = df_filtered[df_filtered['Result'].isin(result_filter)]
    
    # Display table
    st.dataframe(
        df_filtered,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Download button
    csv = df_filtered.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name=f"spx_trades_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    st.caption("Dashboard updates automatically when trade_log.xlsx is updated")

if __name__ == "__main__":
    main()
