import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from utils.firebase_config import (
    get_budget, create_budget, record_transaction, get_transactions, get_pending_transactions, FIREBASE_AVAILABLE,
    get_emergency_fund, get_savings_goals,
    set_savings_goal, update_goal_progress, delete_savings_goal,
    update_transaction_bundle, get_user_bundles, create_custom_bundle,
    update_budget_remaining
)
from utils.analytics import AdvancedAnalytics
from utils.payment_processor import PaymentProcessor
from utils.validators import PaymentValidator

# ===== DEMO MODE STATUS =====
if not FIREBASE_AVAILABLE:
    st.warning(
        """
        ⚠️ **DEMO MODE - DATA NOT SAVED**

        To save your data, set up Firebase:
        1. Create project at firebase.google.com
        2. Download service account key
        3. Set FIREBASE_KEY_JSON environment variable
        4. Restart this app

        Right now, everything disappears on refresh!
        """,
        icon="⚠️"
    )
else:
    st.success("✅ Database connected - data being saved", icon="✅")

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="💰 BudgetWise - Smart UPI Budget Manager",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== CUSTOM CSS - PREMIUM STYLING ====================
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary: #1E3A8A;
        --secondary: #F59E0B;
        --success: #10B981;
        --danger: #EF4444;
        --warning: #FBBF24;
    }

    /* Typography */
    .st-emotion-cache-1v0mbdj {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* Main container */
    .main {
        padding: 2rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Card styling */
    .stCard {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        border: 1px solid #E5E7EB;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
    }

    .metric-card h3 {
        margin: 0;
        font-size: 14px;
        opacity: 0.9;
        margin-bottom: 8px;
    }

    .metric-card .value {
        font-size: 28px;
        font-weight: bold;
        margin: 0;
    }

    /* Buttons */
    .stButton > button {
        width: 100%;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        border: none;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
    }

    /* Success box */
    .success-box {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 16px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 4px solid white;
    }

    /* Warning box */
    .warning-box {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: white;
        padding: 16px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 4px solid white;
    }

    /* Error box */
    .error-box {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
        color: white;
        padding: 16px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 4px solid white;
    }

    /* Info box */
    .info-box {
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%);
        color: white;
        padding: 16px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 4px solid white;
    }

    /* Radio buttons */
    .stRadio > div {
        background: white;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border: 2px solid #E5E7EB;
        transition: all 0.2s;
    }

    .stRadio > div:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }

    /* Progress bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #F3F4F6 0%, #E5E7EB 100%);
        border-radius: 8px;
    }

    /* Table styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
    }
</style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================
if 'user_id' not in st.session_state:
    st.session_state.user_id = "premium_user_" + datetime.now().strftime("%Y%m%d%H%M%S")

if 'current_month' not in st.session_state:
    st.session_state.current_month = datetime.now().strftime('%Y-%m')

if 'show_success' not in st.session_state:
    st.session_state.show_success = False

# ==================== APP REFRESH KEYS & CACHE HELPERS ====================
def init_app_state():
    if 'budget_refresh' not in st.session_state:
        st.session_state.budget_refresh = 0
    if 'goals_refresh' not in st.session_state:
        st.session_state.goals_refresh = 0
    if 'bundles_refresh' not in st.session_state:
        st.session_state.bundles_refresh = 0
    if 'pending_refresh' not in st.session_state:
        st.session_state.pending_refresh = 0

init_app_state()

# Small helper functions to refresh views
def refresh_budget():
    st.session_state.budget_refresh += 1
    st.rerun()

def refresh_goals():
    st.session_state.goals_refresh += 1
    st.rerun()

def refresh_bundles():
    st.session_state.bundles_refresh += 1
    st.rerun()

def refresh_pending():
    st.session_state.pending_refresh += 1
    st.rerun()

# Cache wrappers that use refresh keys to invalidate
@st.cache_data(ttl=1)
def get_budget_with_refresh(user_id, month, refresh_key):
    return get_budget(user_id, month)

@st.cache_data(ttl=1)
def get_transactions_with_refresh(user_id, month, refresh_key):
    return get_transactions(user_id, month)

@st.cache_data(ttl=1)
def get_bundles_with_refresh(user_id, refresh_key):
    return get_user_bundles(user_id)

@st.cache_data(ttl=1)
def get_goals_with_refresh(user_id, refresh_key):
    return get_savings_goals(user_id)

@st.cache_data(ttl=1)
def get_pending_with_refresh(user_id, month, refresh_key):
    return get_pending_transactions(user_id, month)

# ==================== HEADER ====================
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A; margin-bottom: 10px;'>💰 BudgetWise</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #6B7280; margin-top: 0;'>Smart UPI Budget Manager • Control Your Spending</h4>", unsafe_allow_html=True)

st.markdown("---")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 📍 Navigation")

    page = st.radio(
        "Select Page:",
        ["🏠 Dashboard", "💳 Setup Budget", "💵 Send Money", "⏳ Pending Transactions", "📊 Analytics", "🎯 Savings Goals", "💚 Emergency Fund", "⚡ Insights"],
        label_visibility="collapsed",
        key="nav"
    )

    st.markdown("---")

    # User info
    st.markdown("### 👤 Account")
    st.write(f"**User ID:** `{st.session_state.user_id[:10]}...`")
    st.write(f"**Month:** {st.session_state.current_month}")

    # Small demo badge for quick visibility
    if not FIREBASE_AVAILABLE:
        st.warning("⚠️ DEMO MODE - Data will NOT be saved. See the top banner for setup steps.", icon="⚠️")

    # Quick stats
    budget = get_budget_with_refresh(
        st.session_state.user_id, st.session_state.current_month, st.session_state.budget_refresh
    )
    if budget:
        total_remaining = (budget.get('meals_remaining', 0) +
                          budget.get('groceries_remaining', 0) +
                          budget.get('rent_remaining', 0) +
                          budget.get('savings_remaining', 0))
        st.markdown("### 📈 Quick Stats")
        st.metric("Total Remaining", f"₹{total_remaining:,.0f}")
        st.metric("Emergency Fund", f"₹{get_emergency_fund(st.session_state.user_id):,.0f}")

# ==================== PAGE 1: DASHBOARD ====================
if page == "🏠 Dashboard":
    st.markdown("### 📊 Your Monthly Budget Dashboard")

    budget = get_budget_with_refresh(
        st.session_state.user_id, st.session_state.current_month, st.session_state.budget_refresh
    )

    if budget is None:
        st.warning("📋 No budget set up. Go to **Setup Budget** to create one!", icon="⚠️")
        st.stop()

    # Calculate totals
    total_allocated = (budget.get('meals', 0) + budget.get('groceries', 0) +
                      budget.get('rent', 0) + budget.get('savings', 0))
    total_remaining = (budget.get('meals_remaining', 0) + budget.get('groceries_remaining', 0) +
                      budget.get('rent_remaining', 0) + budget.get('savings_remaining', 0))
    total_spent = total_allocated - total_remaining

    # Recent transactions
    st.markdown("### 📝 Recent Transactions")
    transactions = get_transactions_with_refresh(
        st.session_state.user_id, st.session_state.current_month, st.session_state.budget_refresh
    )

    # Top metrics with beautiful cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Monthly Income</h3>
            <p class="value">₹{budget.get('monthly_income', 0):,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);">
            <h3>Total Spent</h3>
            <p class="value">₹{total_spent:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%);">
            <h3>Remaining</h3>
            <p class="value">₹{total_remaining:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        emergency = get_emergency_fund(st.session_state.user_id)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #06B6D4 0%, #0891B2 100%);">
            <h3>Emergency Fund 💚</h3>
            <p class="value">₹{emergency:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Budget breakdown with progress
    st.markdown("### 💳 Your Budgets")

    bundles = [
        {'name': 'Meals & Dining', 'key': 'meals', 'emoji': '🍽️', 'color': '#FF9500'},
        {'name': 'Groceries', 'key': 'groceries', 'emoji': '🛒', 'color': '#4CAF50'},
        {'name': 'Rent', 'key': 'rent', 'emoji': '🏠', 'color': '#2196F3'},
        {'name': 'Savings (Protected)', 'key': 'savings', 'emoji': '💚', 'color': '#66BB6A'},
    ]

    cols = st.columns(2)
    for idx, bundle in enumerate(bundles):
        with cols[idx % 2]:
            key = bundle['key']
            allocated = budget.get(key, 0)
            remaining = budget.get(f'{key}_remaining', 0)
            used = allocated - remaining
            percentage = (used / allocated * 100) if allocated > 0 else 0

            # Determine color based on usage
            if key == 'savings':
                progress_color = '#10B981'
            elif percentage < 70:
                progress_color = '#10B981'
            elif percentage < 90:
                progress_color = '#F59E0B'
            else:
                progress_color = '#EF4444'

            st.markdown(f"""
            <div style='background: white; padding: 16px; border-radius: 10px; border-left: 4px solid {bundle["color"]}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <h4 style='margin: 0; color: {bundle["color"]};'>{bundle["emoji"]} {bundle["name"]}</h4>
            </div>
            """, unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Allocated:** ₹{allocated:,.0f}")
                st.write(f"**Spent:** ₹{used:,.0f}")
            with col_b:
                st.write(f"**Remaining:** ₹{remaining:,.0f}")
                st.write(f"**Used:** {percentage:.1f}%")

            st.progress(min(percentage / 100, 1.0))

            # Warnings
            if remaining < (allocated * 0.1) and key != 'savings':
                st.markdown("""
                <div class="warning-box">
                ⚠️ Low balance! Only 10% left.
                </div>
                """, unsafe_allow_html=True)

            st.markdown("")

    st.markdown("---")

    # Recent transactions
    st.markdown("### 📝 Recent Transactions")

    transactions = get_transactions(st.session_state.user_id, st.session_state.current_month)

    if transactions:
        df_trans = pd.DataFrame([
            {
                'Recipient': t.get('recipient', 'Unknown'),
                'Amount': f"₹{t.get('amount', 0):,.0f}",
                'Category': t.get('bundle', 'Unknown').title(),
                'Time': str(t.get('timestamp', ''))[:10]
            }
            for t in transactions[:5]
        ])
        st.dataframe(df_trans, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet. Start by going to **Send Money**!", icon="ℹ️")

# ==================== PAGE 2: SETUP BUDGET ====================
elif page == "💳 Setup Budget":
    st.markdown("### 🎯 Set Up Your Monthly Budget")
    st.markdown("Allocate your monthly income into smart bundles")

    # Income
    col1, col2 = st.columns([2, 1])
    with col1:
        monthly_income = st.number_input(
            "Monthly Income (₹)",
            min_value=1000,
            step=1000,
            value=45000,
            help="Your total monthly income"
        )

    st.markdown("---")
    st.markdown("### 📋 Allocate Your Budget")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🍽️ Meals & Dining**")
        meals = st.number_input("Meals", min_value=0, step=100, value=8000, label_visibility="collapsed")

        st.markdown("**🛒 Groceries**")
        groceries = st.number_input("Groceries", min_value=0, step=100, value=6000, label_visibility="collapsed")

    with col2:
        st.markdown("**🏠 Rent**")
        rent = st.number_input("Rent", min_value=0, step=100, value=25000, label_visibility="collapsed")

        st.markdown("**Other Expenses (Transport, Utilities)**")
        other = st.number_input("Other", min_value=0, step=100, value=3000, label_visibility="collapsed")

    with col3:
        st.markdown("**💚 Savings (Protected)**")
        savings = st.number_input("Savings", min_value=0, step=100, value=6000, label_visibility="collapsed")

        st.markdown("**📱 Entertainment**")
        entertainment = st.number_input("Entertainment", min_value=0, step=100, value=2000, label_visibility="collapsed")

    st.markdown("---")

    # Validation
    total = meals + groceries + rent + other + savings + entertainment

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Income", f"₹{monthly_income:,.0f}")
    with col2:
        st.metric("Total Allocated", f"₹{total:,.0f}")
    with col3:
        remaining = monthly_income - total
        status = "✅" if remaining == 0 else ("⚠️" if remaining > 0 else "❌")
        st.metric("Difference", f"₹{abs(remaining):,.0f}", status)
    with col4:
        percentage = (total / monthly_income * 100) if monthly_income > 0 else 0
        st.metric("Allocation %", f"{percentage:.1f}%")

    st.markdown("")

    # Save button
    if st.button("💾 Save Budget", use_container_width=True, type="primary", key="save_budget"):
        if total > monthly_income:
            st.error(f"❌ Total exceeds income! Reduce by ₹{total - monthly_income:,.0f}")
        else:
            budget_data = {
                'income': monthly_income,
                'meals': meals,
                'groceries': groceries,
                'rent': rent,
                'other': other,
                'savings': savings,
                'entertainment': entertainment,
            }

            success, message = create_budget(st.session_state.user_id, st.session_state.current_month, budget_data)
            if success:
                st.success("✅ Budget saved successfully!")
                st.balloons()
                st.markdown("""
                <div class="success-box">
                📈 Your budget is now active! Go to **Send Money** to start tracking.
                </div>
                """, unsafe_allow_html=True)
                # Refresh dashboard view
                st.session_state.budget_refresh = st.session_state.get('budget_refresh', 0) + 1
                st.rerun()
            else:
                if "Demo mode" in str(message):
                    st.warning(str(message))
                else:
                    st.error(f"❌ Failed to save budget: {message}")

    # Custom Bundles Section
    st.markdown("---")
    st.markdown("### 🎁 Custom Bundles (Advanced)")
    st.markdown("Create custom budget categories for your unique needs")

    custom_bundles = get_bundles_with_refresh(st.session_state.user_id, st.session_state.bundles_refresh)

    if custom_bundles and len(custom_bundles) > 0:
        st.success(f"✅ You have {len(custom_bundles)} custom bundle(s)")
        for bundle in custom_bundles:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{bundle.get('emoji', '📦')} **{bundle.get('name', 'Custom Bundle')}**")
            with col2:
                if st.button("🗑️", key=f"delete_bundle_{bundle.get('id')}", help="Delete bundle"):
                    st.info("Bundle deletion - Archive this feature if not needed")
        st.markdown("")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        new_bundle_name = st.text_input("Bundle Name", placeholder="e.g., Subscriptions, Gifts, Fitness")
    with col2:
        emoji_choice = st.selectbox("Emoji", ["📦", "🎁", "💪", "🎮", "📚", "🏥", "🚗", "✈️", "🍷", "👗"], index=0)
    with col3:
        st.write("")
        st.write("")
        if st.button("➕ Add Bundle", use_container_width=True):
            if new_bundle_name:
                success, message = create_custom_bundle(st.session_state.user_id, new_bundle_name, emoji_choice)
                if success:
                    st.success(f"✅ Bundle '{new_bundle_name}' created!")
                    # Refresh bundles list
                    st.session_state.bundles_refresh = st.session_state.get('bundles_refresh', 0) + 1
                    st.rerun()
                else:
                    if "Demo mode" in str(message):
                        st.warning(str(message))
                    else:
                        st.error(f"Failed to create bundle: {message}")
            else:
                st.warning("Please enter a bundle name")

# ==================== PAGE 3: SEND MONEY (CORE FEATURE) ====================
elif page == "💵 Send Money":
    st.markdown("### 💵 Send Money via UPI")
    st.markdown("**This is where BudgetWise works its magic!**")

    budget = get_budget_with_refresh(st.session_state.user_id, st.session_state.current_month, st.session_state.budget_refresh)

    if budget is None:
        st.error("❌ No budget set up. Please go to **Setup Budget** first.", icon="❌")
        st.stop()

    # Payment details
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Recipient Details**")
        recipient = st.text_input("Recipient Name or UPI ID", value="DMart", label_visibility="collapsed")
        amount = st.number_input("Amount (₹)", min_value=1, step=10, value=850, label_visibility="collapsed")

    with col2:
        st.markdown("**Additional Info**")
        note = st.text_input("Note (optional)", value="Payment", label_visibility="collapsed")
        category = st.selectbox("Category", ["meals", "groceries", "rent", "other", "entertainment"], index=0, label_visibility="collapsed")

    st.markdown("---")

    # CORE FEATURE: Bundle picker with urgency skip
    st.markdown("## 🎯 **Which budget does this come from?**")
    st.markdown("*Or skip now and categorize later if you're in a hurry!*")
    st.markdown("")

    # Tab selector for urgent vs normal flow
    col_skip, col_normal = st.columns([1, 4])

    with col_skip:
        skip_bundle = st.checkbox("⚡ Skip & Pay Now", help="Pay now without selecting, categorize later")

    # Create beautiful bundle selector
    bundle_options = ['meals', 'groceries', 'rent', 'other', 'entertainment']
    bundle_display = {
        'meals': '🍽️ Meals & Dining',
        'groceries': '🛒 Groceries',
        'rent': '🏠 Rent',
        'other': '🚗 Other Expenses',
        'entertainment': '🎬 Entertainment',
    }

    if skip_bundle:
        st.markdown("### ⚡ Quick Payment Mode")
        st.info("⚡ You're in urgent mode! Payment will be recorded as **UNCATEGORIZED**. You can categorize it later from the **Pending Transactions** page.")
        selected_bundle = None
    else:
        selected_bundle = st.radio(
            "Select Budget:",
            options=bundle_options,
            format_func=lambda x: bundle_display[x],
            label_visibility="collapsed",
            horizontal=False
        )

    st.markdown("")

    # Show selected bundle details (only if not skipping)
    if not skip_bundle and selected_bundle:
        remaining_key = f'{selected_bundle}_remaining'
        allocated = budget.get(selected_bundle, 0)
        remaining = budget.get(remaining_key, 0)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Allocated", f"₹{allocated:,.0f}")
        with col2:
            st.metric("Remaining", f"₹{remaining:,.0f}")
        with col3:
            percentage = ((allocated - remaining) / allocated * 100) if allocated > 0 else 0
            st.metric("Used", f"{percentage:.1f}%")

        st.markdown("")

        # Payment processor
        processor = PaymentProcessor(budget)
        validation = processor.validate_payment(amount, selected_bundle)

        # Validations and warnings
        can_proceed = validation['valid']

        if not can_proceed:
            st.markdown(f"""
            <div class="error-box">
            ❌ {validation['error']}
            </div>
            """, unsafe_allow_html=True)

        # Low balance warning
        low_balance_warnings = processor.get_low_balance_warnings()
        if selected_bundle in [w['bundle'] for w in low_balance_warnings]:
            warning = [w for w in low_balance_warnings if w['bundle'] == selected_bundle][0]
            st.markdown(f"""
            <div class="warning-box">
            ⚠️ {warning['message']}
            </div>
            """, unsafe_allow_html=True)

        # Savings protection
        if selected_bundle == 'savings':
            st.markdown("""
            <div class="error-box">
            🔒 Cannot spend from protected Savings bundle! This is by design.
            </div>
            """, unsafe_allow_html=True)
            can_proceed = False
    elif skip_bundle:
        # For urgent skip mode - we can always proceed
        can_proceed = True
        selected_bundle = "uncategorized"
    else:
        can_proceed = False

    st.markdown("---")

    # Payment confirmation
    if can_proceed:
        if skip_bundle:
            st.markdown("### ⚡ Quick Payment (Uncategorized)")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**To:** {recipient}")
            with col2:
                st.info(f"**Amount:** ₹{amount:,.0f}")
            st.warning("⚡ This payment will be marked as UNCATEGORIZED. Categorize it later to track spending!")
        else:
            st.markdown("### ✅ Payment Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**To:** {recipient}")
            with col2:
                st.info(f"**Amount:** ₹{amount:,.0f}")
            with col3:
                st.info(f"**From:** {selected_bundle.title()}")

            remaining_key = f'{selected_bundle}_remaining'
            remaining = budget.get(remaining_key, 0)
            st.success(f"After payment: **₹{remaining - amount:,.0f}** remaining")

        st.markdown("")

        # Confirm button
        if st.button("✅ Confirm & Pay", use_container_width=True, type="primary", key="confirm_pay"):
            # Validate inputs before processing
            valid, error = PaymentValidator.validate_recipient(recipient)
            if not valid:
                st.error(error)
                st.stop()

            valid, error = PaymentValidator.validate_amount(amount)
            if not valid:
                st.error(error)
                st.stop()

            # Only validate bundle when one is selected (not urgent skip)
            if not skip_bundle:
                valid, error = PaymentValidator.validate_bundle(selected_bundle)
                if not valid:
                    st.error(error)
                    st.stop()

            with st.spinner("Processing payment..."):
                transaction_data = {
                    'recipient': recipient,
                    'amount': amount,
                    'bundle': selected_bundle if selected_bundle else 'uncategorized',
                    'note': note,
                    'category': category,
                    'upi_id': recipient,
                    'status': 'pending' if skip_bundle else 'completed',
                }

                if skip_bundle:
                    # For urgent mode, just record as pending
                    success, message = record_transaction(st.session_state.user_id, st.session_state.current_month, transaction_data)
                    if success:
                        st.success("✅ Payment Recorded (Uncategorized)")
                        st.balloons()
                        st.markdown(f"""
                        <div class="success-box">
                        ⚡ **₹{amount:,.0f}** sent to **{recipient}** (UNCATEGORIZED)<br>
                        Go to **Pending Transactions** to categorize this payment later!
                        </div>
                        """, unsafe_allow_html=True)
                        # Refresh pending list
                        st.session_state.pending_refresh = st.session_state.get('pending_refresh', 0) + 1
                        st.rerun()
                    else:
                        if "Demo mode" in str(message):
                            st.warning(str(message))
                        else:
                            st.error(f"❌ Failed to record transaction: {message}")
                else:
                    # Normal flow with bundle deduction
                    result = processor.process_payment(recipient, amount, selected_bundle, note)

                    if result['success']:
                        # Record transaction
                        success, message = record_transaction(st.session_state.user_id, st.session_state.current_month, transaction_data)
                        if success:
                            # Update budget in database
                            remaining_key = f'{selected_bundle}_remaining'
                            remaining = budget.get(remaining_key, 0)
                            update_budget_remaining(st.session_state.user_id, st.session_state.current_month,
                                                  selected_bundle, remaining - amount)

                            st.success("✅ Payment Successful!")
                            st.balloons()

                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Sent", f"₹{amount:,.0f}", "")
                            with col2:
                                st.metric("New Balance", f"₹{remaining - amount:,.0f}", f"-₹{amount:,.0f}")

                            st.markdown(f"""
                            <div class="success-box">
                            ✅ **₹{amount:,.0f}** sent to **{recipient}** from **{selected_bundle}**
                            </div>
                            """, unsafe_allow_html=True)
                            # Refresh dashboard
                            st.session_state.budget_refresh = st.session_state.get('budget_refresh', 0) + 1
                            st.rerun()
                        else:
                            if "Demo mode" in str(message):
                                st.warning(str(message))
                            else:
                                st.error(f"❌ Failed to record transaction: {message}")
                    else:
                        st.error(f"❌ {result['error']}")

# ==================== PAGE 4: PENDING TRANSACTIONS ====================
elif page == "⏳ Pending Transactions":
    st.markdown("### ⏳ Categorize Your Pending Payments")
    st.markdown("Payments made in urgent mode - categorize them now to track spending properly")

    budget = get_budget_with_refresh(st.session_state.user_id, st.session_state.current_month, st.session_state.budget_refresh)

    if budget is None:
        st.error("No budget set up. Please go to 'Setup Budget' first.")
        st.stop()

    # Get pending transactions directly
    pending_transactions = get_pending_with_refresh(
        st.session_state.user_id, st.session_state.current_month, st.session_state.pending_refresh
    )

    if not pending_transactions:
        st.success("✅ No pending transactions! All payments are categorized.")
        st.info("Payments made in urgent mode will appear here for categorization.")
        st.stop()

    st.warning(f"⏳ You have {len(pending_transactions)} uncategorized payment(s) to review")
    st.markdown("---")

    # Display each pending transaction
    for idx, trans in enumerate(pending_transactions):
        st.markdown(f"### Transaction {idx + 1}")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Recipient", trans.get('recipient', 'Unknown'))
        with col2:
            st.metric("Amount", f"₹{trans.get('amount', 0):,.0f}")
        with col3:
            st.metric("Date", str(trans.get('timestamp', ''))[:10])
        with col4:
            st.metric("Status", "⏳ Pending")

        # Categorization form
        col1, col2 = st.columns(2)
        with col1:
            bundle_options = ['meals', 'groceries', 'rent', 'other', 'entertainment']
            bundle_display = {
                'meals': '🍽️ Meals & Dining',
                'groceries': '🛒 Groceries',
                'rent': '🏠 Rent',
                'other': '🚗 Other Expenses',
                'entertainment': '🎬 Entertainment',
            }

            selected_bundle = st.selectbox(
                "Categorize to bundle:",
                options=bundle_options,
                format_func=lambda x: bundle_display[x],
                key=f"pending_{idx}"
            )

        with col2:
            note = st.text_input("Add note (optional)", key=f"note_{idx}")

        # Show impact
        allocated = budget.get(selected_bundle, 0)
        remaining = budget.get(f'{selected_bundle}_remaining', 0)
        amount = trans.get('amount', 0)
        new_remaining = max(0, remaining - amount)

        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.info(f"**Bundle:** {bundle_display[selected_bundle]}")
        with col_info2:
            st.warning(f"**Impact:** ₹{amount:,.0f} will be deducted. New remaining: ₹{new_remaining:,.0f}")

        # Categorize button
        if st.button(f"✅ Categorize Transaction {idx + 1}", key=f"categorize_{idx}", use_container_width=True):
            with st.spinner("Updating transaction..."):
                try:
                    # Update budget remaining amount
                    ok1, msg1 = update_budget_remaining(st.session_state.user_id, st.session_state.current_month,
                                          selected_bundle, new_remaining)

                    # Update transaction status
                    ok2, msg2 = update_transaction_bundle(st.session_state.user_id, st.session_state.current_month,
                                            trans.get('id', ''), selected_bundle)

                    if ok1 and ok2:
                        st.success(f"✅ Transaction categorized to {bundle_display[selected_bundle]}!")
                        st.balloons()
                        st.markdown(f"""
                        <div class="success-box">
                        ✅ **₹{amount:,.0f}** to **{trans.get('recipient')}** categorized to **{bundle_display[selected_bundle]}**<br>
                        New remaining: **₹{new_remaining:,.0f}**
                        </div>
                        """, unsafe_allow_html=True)
                        # Refresh pending and budget views
                        st.session_state.pending_refresh = st.session_state.get('pending_refresh', 0) + 1
                        st.session_state.budget_refresh = st.session_state.get('budget_refresh', 0) + 1
                        st.rerun()
                    else:
                        if "Demo mode" in str(msg1 or msg2):
                            st.warning(str(msg1 or msg2))
                        else:
                            st.error(f"Error updating transaction: {msg1 or msg2}")
                except Exception as e:
                    st.error(f"Error updating transaction: {e}")

        st.markdown("---")

# ==================== PAGE 5: ANALYTICS ====================
elif page == "📊 Analytics":
    st.markdown("### 📊 Advanced Spending Analytics")

    budget = get_budget_with_refresh(st.session_state.user_id, st.session_state.current_month, st.session_state.budget_refresh)

    if budget is None:
        st.error("No budget set up. Please go to 'Setup Budget' first.")
        st.stop()

    transactions = get_transactions_with_refresh(st.session_state.user_id, st.session_state.current_month, st.session_state.budget_refresh)

    # Create analytics instance
    analytics = AdvancedAnalytics(transactions, budget)

    # Health score
    health_score = analytics.get_budget_health_score()
    col1, col2 = st.columns([1, 3])

    with col1:
        # Health score gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            title={'text': "Budget Health"},
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "#f0f0f0"},
                    {'range': [50, 100], 'color': "#e0f0f0"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig_gauge.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        # Spending breakdown data
        bundles_data = {
            'Bundle': ['Meals', 'Groceries', 'Rent', 'Other', 'Entertainment', 'Savings'],
            'Allocated': [
                budget.get('meals', 0),
                budget.get('groceries', 0),
                budget.get('rent', 0),
                budget.get('other', 0),
                budget.get('entertainment', 0),
                budget.get('savings', 0),
            ],
            'Remaining': [
                budget.get('meals_remaining', 0),
                budget.get('groceries_remaining', 0),
                budget.get('rent_remaining', 0),
                budget.get('other_remaining', 0),
                budget.get('entertainment_remaining', 0),
                budget.get('savings_remaining', 0),
            ]
        }

        df = pd.DataFrame(bundles_data)
        df['Spent'] = df['Allocated'] - df['Remaining']
        df['% Used'] = (df['Spent'] / df['Allocated'] * 100).round(1)

        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        # Bar chart
        fig_bar = px.bar(
            df[df['Bundle'] != 'Savings'],
            x='Bundle',
            y=['Spent', 'Remaining'],
            title='💰 Spending vs Remaining',
            barmode='stack',
            color_discrete_map={'Spent': '#EF4444', 'Remaining': '#10B981'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        # Pie chart
        fig_pie = px.pie(
            df[df['Spent'] > 0],
            values='Spent',
            names='Bundle',
            title='🥧 Spending Breakdown',
            color_discrete_sequence=['#FF9500', '#4CAF50', '#2196F3', '#9333EA', '#EC4899']
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Insights
    st.markdown("### 💡 Smart Insights")

    insights = analytics.get_spending_insights()
    for insight in insights:
        if insight['type'] == 'warning':
            st.markdown(f"""
            <div class="warning-box">
            {insight['message']}<br>
            💡 {insight['action']}
            </div>
            """, unsafe_allow_html=True)
        elif insight['type'] == 'success':
            st.markdown(f"""
            <div class="success-box">
            {insight['message']}<br>
            💡 {insight['action']}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="info-box">
            {insight['message']}<br>
            💡 {insight['action']}
            </div>
            """, unsafe_allow_html=True)

# ==================== PAGE 6: SAVINGS GOALS ====================
elif page == "🎯 Savings Goals":
    st.markdown("### 🎯 Your Savings Goals")
    st.markdown("Track your long-term financial goals and manage your aspirations")

    goals = get_goals_with_refresh(st.session_state.user_id, st.session_state.goals_refresh)

    if goals and len(goals) > 0:
        st.success(f"✅ You have {len(goals)} active goal(s)")
        st.markdown("---")


        for idx, goal in enumerate(goals):
            name = goal.get('name', 'Unnamed Goal')
            target = goal.get('target_amount', 0)
            current = goal.get('current_amount', 0)
            progress = (current / target * 100) if target > 0 else 0
            goal_id = goal.get('id', '')

            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### 🎯 {name}")
                st.progress(min(progress / 100, 1.0))

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Target", f"₹{target:,.0f}")
                with col_b:
                    st.metric("Current", f"₹{current:,.0f}")
                with col_c:
                    st.metric("Progress", f"{progress:.1f}%")

            with col2:
                if progress >= 100:
                    st.success("🎉 Achieved!")
                else:
                    remaining = target - current
                    st.warning(f"₹{remaining:,.0f}\nto go", icon="⏳")

            st.markdown("")

            # Goal management
            col_action1, col_action2, col_action3 = st.columns(3)
            with col_action1:
                add_amount = st.number_input(f"Add funds to {name}", min_value=0, step=100, key=f"add_{idx}")
                if st.button("➕ Add", key=f"add_btn_{idx}", use_container_width=True):
                    if add_amount > 0:
                        success, message = update_goal_progress(st.session_state.user_id, goal_id, add_amount)
                        if success:
                            st.success(f"✅ Added ₹{add_amount:,.0f} to {name}!")
                            # Refresh goals
                            st.session_state.goals_refresh = st.session_state.get('goals_refresh', 0) + 1
                            st.rerun()
                        else:
                            if "Demo mode" in str(message):
                                st.warning(str(message))
                            else:
                                st.error(f"Failed to add funds: {message}")

            with col_action2:
                st.write("")
                st.write("")
                if st.button("📊 View Details", key=f"detail_{idx}", use_container_width=True):
                    st.info(f"""
                    **Goal Details:**
                    - Name: {name}
                    - Created: {str(goal.get('created_at', ''))[:10]}
                    - Target: ₹{target:,.0f}
                    - Current: ₹{current:,.0f}
                    - Remaining: ₹{max(0, target - current):,.0f}
                    - Status: {'🎉 Achieved' if progress >= 100 else '⏳ In Progress'}
                    """)

            with col_action3:
                st.write("")
                st.write("")
                if st.button("🗑️ Delete", key=f"delete_{idx}", use_container_width=True):
                    success, message = delete_savings_goal(st.session_state.user_id, goal_id)
                    if success:
                        st.success(f"✅ Goal '{name}' deleted!")
                        st.session_state.goals_refresh = st.session_state.get('goals_refresh', 0) + 1
                        st.rerun()
                    else:
                        if "Demo mode" in str(message):
                            st.warning(str(message))
                        else:
                            st.error(f"Failed to delete goal: {message}")

            st.markdown("---")
    else:
        st.info("📌 No savings goals yet. Create your first goal below!", icon="💡")

    st.markdown("### ➕ Create New Goal")
    st.markdown("Set a new financial goal to work towards")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        goal_name = st.text_input("Goal Name", value="Vacation", placeholder="e.g., Car, House, Education")
    with col2:
        goal_amount = st.number_input("Target Amount (₹)", value=50000, step=1000, min_value=100)
    with col3:
        st.write("")
        st.write("")
        if st.button("✅ Create Goal", use_container_width=True, type="primary"):
            if goal_name and goal_amount > 0:
                success, message = set_savings_goal(st.session_state.user_id, goal_amount, goal_name)
                if success:
                    st.success(f"✅ Goal '{goal_name}' created successfully!")
                    st.balloons()
                    st.markdown(f"""
                    <div class="success-box">
                    🎯 New goal created: **{goal_name}** (₹{goal_amount:,.0f})
                    </div>
                    """, unsafe_allow_html=True)
                    # Refresh goals
                    st.session_state.goals_refresh = st.session_state.get('goals_refresh', 0) + 1
                    st.rerun()
                else:
                    if "Demo mode" in str(message):
                        st.warning(str(message))
                    else:
                        st.error(f"Failed to create goal: {message}")
            else:
                st.warning("Please enter a goal name and amount")

# ==================== PAGE 7: EMERGENCY FUND ====================
elif page == "💚 Emergency Fund":
    st.markdown("### 💚 Your Emergency Fund")
    st.markdown("Your safety net for unexpected expenses")

    emergency_balance = get_emergency_fund(st.session_state.user_id)

    # Beautiful display
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #06B6D4 0%, #0891B2 100%);">
            <h3>Emergency Fund</h3>
            <p class="value">₹{emergency_balance:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        months_buffer = emergency_balance / 10000
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%);">
            <h3>Months of Buffer</h3>
            <p class="value">{months_buffer:.1f}x</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <h3>Status</h3>
            <p class="value">🔒 Safe</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    ### 📌 How Your Emergency Fund Works

    1. **Auto-Created**: Leftover budget at month-end is automatically transferred
    2. **Protected**: Can't be spent via UPI payments - only manual transfer
    3. **Grows Automatically**: Every month, unused budget adds to it
    4. **Your Safety Net**: For true emergencies and unexpected expenses

    ### 💡 Best Practices
    - Target: 3-6 months of living expenses
    - Never use for planned purchases
    - Review quarterly
    - Build gradually over months
    """)

# ==================== PAGE 8: INSIGHTS & RECOMMENDATIONS ====================
elif page == "⚡ Insights":
    st.markdown("### ⚡ AI-Powered Insights & Recommendations")

    budget = get_budget(st.session_state.user_id, st.session_state.current_month)

    if budget is None:
        st.error("No budget set up.")
        st.stop()

    transactions = get_transactions(st.session_state.user_id, st.session_state.current_month)

    analytics = AdvancedAnalytics(transactions, budget)

    # Smart recommendations
    st.markdown("### 💡 Smart Recommendations")
    recommendations = analytics.get_recommendations()

    for rec in recommendations:
        if rec.startswith("🔴"):
            st.markdown(f"""
            <div class="error-box">
            {rec}
            </div>
            """, unsafe_allow_html=True)
        elif rec.startswith("🟡"):
            st.markdown(f"""
            <div class="warning-box">
            {rec}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="success-box">
            {rec}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Spending predictions
    st.markdown("### 📈 Spending Predictions")

    prediction = analytics.predict_savings()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Current Remaining", f"₹{prediction['current_remaining']:,.0f}")
    with col2:
        st.metric("Potential Emergency Fund", f"₹{prediction['potential_emergency_fund']:,.0f}")
    with col3:
        st.metric("Savings %", f"{prediction['savings_percentage']:.1f}%")

    st.markdown("---")

    # Daily budget calculator
    st.markdown("### 📅 Daily Budget Calculator")

    bundle_select = st.selectbox("Select Bundle", ['meals', 'groceries', 'entertainment'])

    processor = PaymentProcessor(budget)
    daily_calc = processor.calculate_daily_budget(bundle_select)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Days Left", f"{daily_calc['days_left']} days")
    with col2:
        st.metric("Daily Budget", f"₹{daily_calc['daily_budget']:.0f}")
    with col3:
        st.metric("Total Remaining", f"₹{daily_calc['total_remaining']:,.0f}")

    st.info(daily_calc['recommendation'])

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6B7280; margin-top: 40px;'>
    <h5>💰 BudgetWise - Smart UPI Budget Manager 💰</h5>
    <p>Control your spending • Protect your savings • Build your emergency fund • Automatically</p>
    <p style='font-size: 12px;'>Built with ❤️ for the Hackathon | Winning Innovation in Financial Management</p>
</div>
""", unsafe_allow_html=True)
