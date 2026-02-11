@echo off
uv run -m streamlit run app.py --server.baseUrlPath="ai" --server.headless="true" --browser.gatherUsageStats="false" --theme.primaryColor="#474747" --theme.base="dark" --theme.font="monospace" --theme.baseFontSize="12" --server.useStarlette="true"
