"""
Streamlit components for WawaStock UI.

This module provides reusable components for the Streamlit interface:
- bridge: Integration with WawaStock engines and registries
- charts: Interactive charts using Plotly
- metrics: Performance metrics display
- tables: Data tables for trades and results
"""

from .bridge import StreamlitBridge

__all__ = ['StreamlitBridge']
