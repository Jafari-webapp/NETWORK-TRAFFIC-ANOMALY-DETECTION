"""
Turns engineered features into the exact numeric matrix the trained models expect.

CRITICAL — matches your notebook's Stage 5 (leakage removal + get_dummies) but fixes
one real production issue: get_dummies() on a single incoming batch only creates
columns for categories present in THAT batch. If an uploaded file is missing some
interface/rule-name values the scaler saw during training, a naive get_dummies()
call would produce a different column count and either crash or silently
misalign values with the wrong feature.

Fix: we reindex the one-hot-encoded frame against `scaler.feature_names_in_`
(the exact 32 columns RobustScaler was fit on) — any column the scaler expects
but this batch doesn't have gets filled with 0, and any extra/unseen category
column is dropped. This is what "the pipeline used at training time = pipeline
used at inference time" requires in practice for one-hot features on live data.

We NEVER call scaler.fit() or scaler.fit_transform() here — only .transform().
"""
import pandas as pd

from app.ml.feature_engineering import engineer_features

# Columns dropped before modelling — identifiers, raw text, and the raw timestamp
# (Stage 5.1 of the notebook). Not predictive on their own and prevent leakage.
LEAKAGE_COLUMNS = [
    "Time", "Src IP", "Dst IP", "Message", "Live PCAP", "Username",
]


def build_feature_matrix(df: pd.DataFrame, pipeline: dict) -> pd.DataFrame:
    """
    df: raw-ish rows with Title Case Sophos columns.
    pipeline: the loaded joblib dict (scaler + selected_features).
    Returns: a DataFrame with exactly `selected_features` columns, scaled, ready
             for primary_model / secondary_model .predict() / .score_samples().
    """
    engineered = engineer_features(df)

    drop_cols = [c for c in LEAKAGE_COLUMNS if c in engineered.columns]
    working = engineered.drop(columns=drop_cols)

    categorical_cols = working.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    if categorical_cols:
        working = pd.get_dummies(working, columns=categorical_cols, drop_first=True)

    # Coerce anything left to numeric (defensive — booleans/ints should already be fine)
    working = working.apply(pd.to_numeric, errors="coerce").fillna(0)

    scaler = pipeline["scaler"]
    expected_columns = list(scaler.feature_names_in_)

    # Reindex to the scaler's exact training-time schema: fills missing dummy
    # columns with 0, drops anything the scaler never saw. No leakage — this is
    # purely a column-alignment step, not a fit.
    aligned = working.reindex(columns=expected_columns, fill_value=0)

    scaled = scaler.transform(aligned)
    scaled_df = pd.DataFrame(scaled, columns=expected_columns, index=aligned.index)

    selected_features = pipeline["selected_features"]
    return scaled_df[selected_features]
