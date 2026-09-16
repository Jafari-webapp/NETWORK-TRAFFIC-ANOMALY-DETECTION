"""
Deterministic feature engineering — mirrors exactly what your training notebook did
(Network_Traffic.ipynb, Stage 2 "Data Preparation" + Stage 4 "Feature Engineering"),
so the same transformation logic runs at training time and at inference time.

Input: a pandas DataFrame with the raw Sophos columns in "Title Case" form
       (Time, Log comp, Log subtype, Username, Firewall rule, Firewall rule name,
       NAT rule, NAT rule name, In interface, Out interface, Src IP, Dst IP,
       Src port, Dst port, Protocol, Rule type, Live PCAP, Message, Log occurrence).
Output: the same DataFrame with engineered columns appended.
"""
import ipaddress

import numpy as np
import pandas as pd


def _extract_ip_properties(val) -> pd.Series:
    if pd.isna(val) or str(val).strip() in ("nan", "Unknown", ""):
        return pd.Series({"Version": 0, "Is_Private": 0, "Is_Loopback": 0, "Is_Multicast": 0})
    try:
        ip = ipaddress.ip_address(str(val).strip())
        return pd.Series({
            "Version": ip.version,
            "Is_Private": int(ip.is_private),
            "Is_Loopback": int(ip.is_loopback),
            "Is_Multicast": int(ip.is_multicast),
        })
    except Exception:
        return pd.Series({"Version": 0, "Is_Private": 0, "Is_Loopback": 0, "Is_Multicast": 0})


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 2: Data Preparation — time parts, numeric coercion, chronological sort."""
    prepared = df.copy()

    if "Time" in prepared.columns:
        prepared["Time"] = pd.to_datetime(prepared["Time"], errors="coerce")
        prepared["Hour"] = prepared["Time"].dt.hour.fillna(0).astype(int)
        prepared["Day"] = prepared["Time"].dt.day.fillna(1).astype(int)
        prepared["Day_of_Week"] = prepared["Time"].dt.dayofweek.fillna(0).astype(int)
        prepared["Month"] = prepared["Time"].dt.month.fillna(1).astype(int)
        prepared["Is_Weekend"] = (prepared["Day_of_Week"] >= 5).astype(int)

    if "Log occurrence" in prepared.columns:
        prepared["Log occurrence"] = pd.to_numeric(prepared["Log occurrence"], errors="coerce").fillna(0)

    for port_col in ["Src port", "Dst port"]:
        if port_col in prepared.columns:
            prepared[port_col] = pd.to_numeric(prepared[port_col], errors="coerce").fillna(0)

    return prepared


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Stage 4: Feature Engineering — time blocks, IP properties, port/service flags, message metrics."""
    features_df = prepare(df)

    if "Time" in features_df.columns and pd.api.types.is_datetime64_any_dtype(features_df["Time"]):
        features_df["Night_Traffic"] = ((features_df["Hour"] < 6) | (features_df["Hour"] >= 22)).astype(int)
        features_df["Business_Hours"] = features_df["Hour"].between(8, 17).astype(int)

    if "Src IP" in features_df.columns:
        src_props = features_df["Src IP"].apply(_extract_ip_properties)
        features_df["Src_IP_Version"] = src_props["Version"]
        features_df["Src_Is_Private"] = src_props["Is_Private"]
        features_df["Src_Is_Loopback"] = src_props["Is_Loopback"]
        features_df["Src_Is_Multicast"] = src_props["Is_Multicast"]

    if "Dst IP" in features_df.columns:
        dst_props = features_df["Dst IP"].apply(_extract_ip_properties)
        features_df["Dst_IP_Version"] = dst_props["Version"]
        features_df["Dst_Is_Private"] = dst_props["Is_Private"]
        features_df["Dst_Is_Loopback"] = dst_props["Is_Loopback"]
        features_df["Dst_Is_Multicast"] = dst_props["Is_Multicast"]

    if "Src_Is_Private" in features_df.columns and "Dst_Is_Private" in features_df.columns:
        features_df["Is_Internal_Traffic"] = (
            (features_df["Src_Is_Private"] == 1) & (features_df["Dst_Is_Private"] == 1)
        ).astype(int)
        features_df["Is_Cross_Boundary"] = (
            (features_df["Src_Is_Private"] == 1) & (features_df["Dst_Is_Private"] == 0)
        ).astype(int)

    if "Src port" in features_df.columns and "Dst port" in features_df.columns:
        features_df["Dst_Is_Web_Port"] = features_df["Dst port"].isin([80, 443]).astype(int)
        features_df["Dst_Is_DNS_Port"] = features_df["Dst port"].eq(53).astype(int)
        features_df["Dst_Is_SSH_Port"] = features_df["Dst port"].eq(22).astype(int)
        features_df["Dst_Is_RDP_Port"] = features_df["Dst port"].eq(3389).astype(int)
        features_df["Port_Difference"] = (features_df["Src port"] - features_df["Dst port"]).abs()

    if "Message" in features_df.columns:
        features_df["Message_Length"] = features_df["Message"].astype(str).str.len()
        features_df["Message_Word_Count"] = features_df["Message"].astype(str).str.split().str.len()

    return features_df
