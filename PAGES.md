Standard for adding Streamlit dashboard pages

To allow the `Home.py` to automatically discover and render new dashboards, pages should follow this simple pattern:

1) Add a top-level docstring at the beginning of the file (first triple-quoted string) with a short description of the dashboard. Example:

"""
Dashboard de Producción - Órdenes de Fabricación
"""

2) Use `st.set_page_config` to set `page_title` and `page_icon`:

st.set_page_config(page_title='Producción', page_icon='📦')

3) Ensure the file is placed under `pages/` and ends with `.py`. The `Home.py` will scan that folder and create a card for each page automatically using these metadata values.

Optional: You can add a YAML or comment block with additional fields in the future; the current auto-discovery uses the docstring and `set_page_config` call.
