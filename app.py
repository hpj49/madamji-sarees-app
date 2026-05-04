import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime

# --- SECURE CONNECTION ---
# This pulls keys from Streamlit Cloud Secrets (online) 
# or .streamlit/secrets.toml (locally)
conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url=st.secrets["SUPABASE_URL"],
    key=st.secrets["SUPABASE_KEY"]
)

st.set_page_config(page_title="Madamji Sarees Dashboard", layout="wide")
st.title("Active Order Dashboard")

# --- DATA FETCHING ---
response = conn.table("orders").select("*").execute()
raw_df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

# --- FILTERS ---
top_col1, top_col2, top_col3 = st.columns([1.5, 1, 1])
with top_col1:
    show_archive = st.checkbox("📦 Show Archive (Orders older than 5 days)")
with top_col2:
    search_challan = st.text_input("🔍 Search by Challan No")
with top_col3:
    search_party = st.text_input("🔍 Search by Party Name")

if not raw_df.empty:
    display_df = raw_df.copy()
    display_df['order_date'] = pd.to_datetime(display_df['order_date']).dt.date
    display_df['received_date'] = pd.to_datetime(display_df['received_date']).dt.date
    
    current_date = datetime.now().date()
    def calculate_days(row):
        start = row['order_date']
        end = row['received_date'] if pd.notnull(row['received_date']) else current_date
        delta = (end - start).days
        return delta if delta > 0 else 0
    display_df['Days'] = display_df.apply(calculate_days, axis=1)

    display_df['is_recent'] = display_df.apply(lambda r: pd.notnull(r['received_date']) and (current_date - r['received_date']).days <= 5, axis=1)
    
    if not show_archive:
        display_df = display_df[(display_df['received_date'].isna()) | (display_df['is_recent'] == True)]
    else:
        display_df = display_df[(display_df['received_date'].notna()) & (display_df['is_recent'] == False)]
    
    if search_challan:
        display_df = display_df[display_df['challan_no'].astype(str).str.contains(search_challan)]
    if search_party:
        display_df = display_df[display_df['party_name'].str.contains(search_party, case=False, na=False)]

    display_df.insert(0, "Edit", False)
    display_df.insert(1, "Del", False)

    # --- MAIN TABLE ---
    def highlight_recent(row):
        return ['background-color: #d4edda' if row.is_recent else '' for _ in row]

    edited_df = st.data_editor(
        display_df.style.apply(highlight_recent, axis=1),
        column_config={
            "Edit": st.column_config.CheckboxColumn("📝"),
            "Del": st.column_config.CheckboxColumn("🗑️"),
            "is_recent": None, "id": None, "created_at": None,
            "fabric_rate": st.column_config.NumberColumn("Fab Rate", format="₹%.2f"),
            "job_work_rate": st.column_config.NumberColumn("JW Rate", format="₹%.2f"),
            "cut_size": st.column_config.NumberColumn("Cut", format="%.2f"),
            "order_date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "received_date": st.column_config.DateColumn("Recv Date", format="DD/MM/YYYY"),
        },
        disabled=["order_date", "Days", "challan_no", "is_recent"], 
        hide_index=True, width="stretch", key="main_table"
    )

    act_col1, act_col2, _ = st.columns([1, 1, 3])
    if act_col1.button("🗑️ Process Deletions"):
        for c_no in edited_df[edited_df["Del"] == True]['challan_no']:
            conn.table("orders").delete().eq("challan_no", c_no).execute()
        st.rerun()
    
    if act_col2.button("💾 Save Inline Table Edits", type="primary"):
        for _, row in edited_df.iterrows():
            conn.table("orders").update({
                "rf_status": int(row['rf_status'] or 0), "pcs": int(row['pcs'] or 0),
                "fabric_rate": float(row['fabric_rate'] or 0.0), "job_work_rate": float(row['job_work_rate'] or 0.0),
                "received_date": str(row['received_date']) if pd.notnull(row['received_date']) else None,
                "fresh_qty": int(row['fresh_qty'] or 0), "plain_qty": int(row['plain_qty'] or 0), "short_qty": int(row['short_qty'] or 0)
            }).eq("challan_no", row['challan_no']).execute()
        st.success("Changes saved!")
        st.rerun()

    # --- EDIT FORM ---
    editing_rows = edited_df[edited_df["Edit"] == True]
    if not editing_rows.empty:
        curr = editing_rows.iloc[0]
        st.markdown("---")
        with st.expander(f"📝 EDITING CHALLAN: {curr['challan_no']}", expanded=True):
            with st.form("row_edit_form"):
                c1, c2 = st.columns(2)
                u_challan = c1.text_input("Challan No", value=curr['challan_no'], disabled=True)
                u_date = c2.date_input("Date", value=curr['order_date'], format="DD/MM/YYYY")
                
                c3, c4 = st.columns(2)
                u_party = c3.text_input("Party Name", value=curr['party_name'])
                u_agent = c4.text_input("Agent", value=curr.get('agent_name', ''))
                
                c5, c6 = st.columns(2)
                u_fabric = c5.text_input("Fabric Name", value=curr['fabric_name'])
                u_f_rate = c6.number_input("Fabric Rate", value=int(curr['fabric_rate'] or 0))
                
                u_addr = st.text_input("Fabric Address", value=curr['fabric_address'] or "")
                
                c7, c8, c9 = st.columns(3)
                u_pcs = c7.number_input("Pcs", value=int(curr['pcs'] or 0))
                u_cut = c8.number_input("Cut", value=float(curr.get('cut_size', 6.50)), format="%.2f")
                u_jw = c9.number_input("Job Work Rate", value=int(curr['job_work_rate'] or 0))
                
                c10, c11, c12, c13, c14 = st.columns(5)
                u_rec_date = c10.date_input("Received Date", value=curr['received_date'] if pd.notnull(curr['received_date']) else None, format="DD/MM/YYYY")
                u_fresh = c11.number_input("Fresh", value=int(curr.get('fresh_qty', 0)))
                u_short = c12.number_input("Short", value=int(curr.get('short_qty', 0)))
                u_plain = c13.number_input("Plain", value=int(curr.get('plain_qty', 0)))
                u_rf = c14.number_input("Rf", value=int(curr['rf_status'] or 0))
                
                if st.form_submit_button("Update Details"):
                    conn.table("orders").update({
                        "order_date": str(u_date), "party_name": u_party, "agent_name": u_agent,
                        "fabric_name": u_fabric, "fabric_rate": float(u_f_rate), "fabric_address": u_addr,
                        "pcs": u_pcs, "cut_size": u_cut, "job_work_rate": float(u_jw),
                        "received_date": str(u_rec_date) if u_rec_date else None,
                        "fresh_qty": u_fresh, "short_qty": u_short, "plain_qty": u_plain, "rf_status": u_rf
                    }).eq("challan_no", curr['challan_no']).execute()
                    st.success("Updated!")
                    st.rerun()

st.markdown("---")

# --- NEW ORDER ENTRY ---
with st.expander("➕ Click Here to Create a New Order", expanded=False):
    with st.form("new_order_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n_challan = c1.text_input("Challan No *")
        n_date = c2.date_input("Date", datetime.now(), format="DD/MM/YYYY")
        
        c3, c4 = st.columns(2)
        n_party = c3.text_input("Party Name")
        n_agent = c4.text_input("Agent")
        
        c5, c6 = st.columns(2)
        n_fabric = c5.text_input("Fabric Name")
        n_rate = c6.number_input("Fabric Rate", value=0)
        
        n_address = st.text_input("Fabric Address")
        
        c7, c8, c9 = st.columns(3)
        n_pcs = c7.number_input("Pcs", value=0)
        n_cut = c8.number_input("Cut", value=6.50, format="%.2f")
        n_jw = c9.number_input("Job Work Rate", value=0)
        
        c10, c11, c12, c13, c14 = st.columns(5)
        n_rec_date = c10.date_input("Received Date", value=None, format="DD/MM/YYYY")
        n_fresh = c11.number_input("Fresh", value=0)
        n_short = c12.number_input("Short", value=0)
        n_plain = c13.number_input("Plain", value=0)
        n_rf = c14.number_input("Rf", value=0)

        if st.form_submit_button("Submit"):
            if not n_challan: st.error("Challan No required!")
            else:
                conn.table("orders").insert({
                    "challan_no": n_challan, "order_date": str(n_date), "party_name": n_party, "agent_name": n_agent,
                    "fabric_name": n_fabric, "fabric_rate": float(n_rate), "fabric_address": n_address,
                    "pcs": n_pcs, "cut_size": n_cut, "job_work_rate": float(n_jw),
                    "received_date": str(n_rec_date) if n_rec_date else None,
                    "fresh_qty": n_fresh, "short_qty": n_short, 
                    "plain_qty": n_plain, "rf_status": n_rf
                }).execute()
                st.success(f"Added!")
                st.rerun()