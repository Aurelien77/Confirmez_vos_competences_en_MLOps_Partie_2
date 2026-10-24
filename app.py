import streamlit as st
import pandas as pd
import pickle
import numpy as np

st.set_page_config(page_title="Scoring Home Credit", layout="wide")

@st.cache_resource
def load_model():
    with open("learning_models/modele_lgbm.pkl", "rb") as f:
        return pickle.load(f)

@st.cache_data
def load_data():
    return pd.read_pickle("df_home_credit.pkl")

model = load_model()
df = load_data()

features_model = [str(f) for f in model.feature_names_in_]
features = [f for f in features_model if f in df.columns]

missing = set(features_model) - set(features)
if missing:
    st.warning(f"{len(missing)} features manquantes dans les données (ex: {list(missing)[:5]})")

st.title("Application de scoring – Home Credit")
st.markdown("Prédiction du risque de défaut avec LightGBM")

col1, col2 = st.columns([1, 2])

with col1:
    mode = st.radio("Sélection du client", ["Par ID", "Aléatoire"])

    if mode == "Par ID":
        min_id = int(df["SK_ID_CURR"].min())
        max_id = int(df["SK_ID_CURR"].max())
        client_id = st.number_input(
            "SK_ID_CURR",
            min_value=min_id,
            max_value=max_id,
            value=min_id,
            step=1
        )
        client = df[df["SK_ID_CURR"] == client_id]
    else:
        if st.button("Tirer un client au hasard"):
            st.session_state.random_idx = np.random.randint(0, len(df))
        idx = st.session_state.get("random_idx", 0)
        client = df.iloc[[idx]]
        client_id = int(client["SK_ID_CURR"].iloc[0])
        st.write(f"**Client sélectionné :** {client_id}")

    if client.empty:
        st.error("Client non trouvé")
        st.stop()

with col2:
    X = client[features].copy()
    for col in features_model:
        if col not in X.columns:
            X[col] = np.nan
    X = X[features_model]

    proba = model.predict_proba(X)[0, 1]
    target = client["TARGET"].iloc[0] if "TARGET" in client.columns else None

    if proba < 0.1:
        niveau = "Très faible"
    elif proba < 0.3:
        niveau = "Faible"
    elif proba < 0.5:
        niveau = "Moyen"
    elif proba < 0.7:
        niveau = "Élevé"
    else:
        niveau = "Très élevé"

    st.metric("Probabilité de défaut", f"{proba:.1%}")
    st.metric("Niveau de risque", niveau)
    if target is not None:
        st.metric("TARGET réel", "Défaut" if target == 1 else "Bon client")

st.subheader("Informations principales")
info_cols = [
    "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY", "DAYS_BIRTH",
    "DAYS_EMPLOYED", "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
    "CNT_CHILDREN", "CNT_FAM_MEMBERS"
]
info_cols = [c for c in info_cols if c in client.columns]
if info_cols:
    st.dataframe(client[info_cols].T, use_container_width=True)

with st.expander("Features utilisées pour la prédiction"):
    st.write(f"{len(features)} features disponibles sur {len(features_model)}")
    st.dataframe(client[features].T, use_container_width=True)