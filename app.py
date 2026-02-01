# app.py
# App de Priorização de Monitoramento e Manutenção
# Plotly Dash

from dash import Dash

from layout import layout
from callbacks import register_callbacks

# ======================================================
# APP
# ======================================================

app = Dash(__name__)
app.title = "Priorização de Monitoramento"
app.layout = layout

register_callbacks(app)

# ======================================================
# RUN
# ======================================================

if __name__ == "__main__":
    app.run_server(debug=True)
