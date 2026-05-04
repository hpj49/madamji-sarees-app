import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd

# Initialize Connection
conn = st.connection("supabase", type=SupabaseConnection)

st.set_page_config(page_title="Madamji Sarees Management", layout="wide")
st.title("📦 Madamji Sarees - Supabase Edition")

menu = ["View Ledger", "Add New Order", "Manage Records"]
choice = st.sidebar.selectbox("Navigation", menu)

# --- READ: View Ledger ---
if choice == "View Ledger":
    st.subheader("Current Orders")
    rows = conn.query("*", table="orders", ttl="0").execute()
    if rows.data:
        df = pd.DataFrame(rows.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found.")

# --- CREATE: Add New Order ---
elif choice == "Add New Order":
    with st.form("add_form"):
        # (Inputs for challan_no, party_name, etc. - same as previous example)
        # ... 
        if st.form_submit_button("Submit"):
            new_data = {"challan_no": "CH-101", "party_name": "Example Party"} # Example dict
            conn.table("orders").insert(new_data).execute()
            st.success("Record Added!")

# --- UPDATE & DELETE: Manage Records ---
elif choice == "Manage Records":
    st.subheader("Edit or Delete Existing Orders")
    
    # 1. Select the record to edit
    rows = conn.query("id, challan_no, party_name", table="orders", ttl="0").execute()
    if rows.data:
        order_list = {f"{r['challan_no']} - {r['party_name']}": r['id'] for r in rows.data}
        selected_order = st.selectbox("Select Order to Modify", list(order_list.keys()))
        order_id = order_list[selected_order]

        # Fetch current data for the selected ID
        current_row = conn.table("orders").select("*").eq("id", order_id).execute().data[0]

        # 2. Update Form
        with st.form("update_form"):
            new_status = st.selectbox("Update RF Status", ["Pending", "Ready", "Dispatched"], 
                                      index=["Pending", "Ready", "Dispatched"].index(current_row['rf_status']))
            new_received = st.date_input("Update Received Date")
            
            col1, col2 = st.columns(2)
            if col1.form_submit_button("Save Changes"):
                conn.table("orders").update({"rf_status": new_status, "received_date": str(new_received)}).eq("id", order_id).execute()
                st.success("Updated successfully!")
                st.rerun()

            # 3. Delete Action
            if col2.form_submit_button("🗑️ Delete Record"):
                conn.table("orders").delete().eq("id", order_id).execute()
                st.warning(f"Record {order_id} Deleted.")
                st.rerun()