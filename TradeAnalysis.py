import os
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Trading Copilot & Risk Manager",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 AI-Powered Trading Copilot & Risk Manager")
st.markdown(
    "Combine Python, Streamlit, and Generative AI to parse unstructured trading"
    " signals and automate risk management."
)
st.markdown("---")

# --- Sidebar for API Key Management ---
st.sidebar.header("🔑 Configuration")
api_key_input = st.sidebar.text_input(
    "Enter Gemini API Key", type="password", help="Get your key from Google AI Studio"
)

# Fallback sequence: Sidebar Input -> Streamlit Secrets -> Environment Variable
api_key = None
if api_key_input:
  api_key = api_key_input
else:
  try:
    if "GEMINI_API_KEY" in st.secrets:
      api_key = st.secrets["GEMINI_API_KEY"]
  except Exception:
    pass

  if not api_key:
    api_key = os.environ.get("GEMINI_API_KEY")

# Initialize Client safely
client = None
if api_key:
  try:
    client = genai.Client(api_key=api_key)
    st.sidebar.success("✅ Gemini AI Connected Successfully!")
  except Exception as e:
    st.sidebar.error(f"Failed to initialize client: {e}")
else:
  st.sidebar.warning(
      "⚠️ Please enter your Gemini API Key above to enable AI features."
  )

# --- Pydantic Schema for Structured AI Output ---
class TradeSignal(BaseModel):
  direction: str = Field(description="Must be either 'Long' or 'Short'")
  asset: str = Field(description="The ticker symbol or asset name, e.g., BTC, ETH")
  entry_price: float = Field(description="The entry price")
  stop_loss: float = Field(description="The stop-loss price")
  take_profit: float = Field(description="The take-profit price")


# --- Layout: Two Columns ---
col_inputs, col_outputs = st.columns([1, 1], gap="large")

with col_inputs:
  st.subheader("1. AI Signal Parser (Unstructured Text)")
  st.markdown(
      "Paste any trade signal or text below, and let the AI extract the"
      " parameters:"
  )

  raw_signal_text = st.text_area(
      "Trade Signal Text",
      value=(
          "Hey, I'm looking at setting up a long position on Ethereum (ETH)"
          " around $3,200. I'll put my stop loss down at $3,050 to manage risk,"
          " and target a take profit at $3,600."
      ),
      height=100,
  )

  # Default values if AI hasn't parsed yet
  parsed_direction = "Long (Buy)"
  parsed_entry = 3200.0
  parsed_sl = 3050.0
  parsed_tp = 3600.0

  if st.button("✨ Parse with Gemini AI", type="primary"):
    if not client:
      st.error(
          "Gemini API Key missing! Please add it to your Streamlit secrets."
      )
    else:
      with st.spinner("Parsing trade signal using LLM..."):
        try:
          response = client.models.generate_content(
              model="gemini-3.8-flash",
              contents=(
                  "Extract the trading parameters from this text:"
                  f" {raw_signal_text}"
              ),
              config=types.GenerateContentConfig(
                  response_mime_type="application/json",
                  response_schema=TradeSignal,
              ),
          )
          # Parse structured response
          import json

          data = json.loads(response.text)
          parsed_entry = float(data.get("entry_price", 3200.0))
          parsed_sl = float(data.get("stop_loss", 3050.0))
          parsed_tp = float(data.get("take_profit", 3600.0))
          direction_str = data.get("direction", "Long")
          parsed_direction = (
              "Long (Buy)" if "long" in direction_str.lower() else "Short (Sell)"
          )
          st.success("Successfully extracted trade parameters!")
        except Exception as e:
          st.error(f"Error parsing text: {e}")

  st.markdown("---")
  st.subheader("2. Account & Risk Settings")
  account_balance = st.number_input(
      "Account Balance ($)", min_value=1.0, value=10000.0, step=100.0
  )
  risk_pct = st.slider(
      "Account Risk per Trade (%)",
      min_value=0.1,
      max_value=5.0,
      value=1.0,
      step=0.1,
  )

  st.subheader("3. Trade Setup Parameters")
  direction = st.radio(
      "Trade Direction",
      options=["Long (Buy)", "Short (Sell)"],
      index=0 if "Long" in parsed_direction else 1,
      horizontal=True,
  )

  entry_price = st.number_input(
      "Entry Price ($)",
      min_value=0.0001,
      value=float(parsed_entry),
      step=0.1,
  )
  stop_loss = st.number_input(
      "Stop-Loss Price ($)", min_value=0.0001, value=float(parsed_sl), step=0.1
  )
  take_profit = st.number_input(
      "Take-Profit Price ($)",
      min_value=0.0001,
      value=float(parsed_tp),
      step=0.1,
  )
  leverage = st.slider(
      "Leverage Multiplier (x)", min_value=1, max_value=125, value=1, step=1
  )

# --- Core Mathematical Calculations ---
dollar_risk = account_balance * (risk_pct / 100.0)

is_valid_setup = True
if "Long" in direction:
  if stop_loss >= entry_price:
    is_valid_setup = False
  risk_per_unit = entry_price - stop_loss
  reward_per_unit = take_profit - entry_price
else:
  if stop_loss <= entry_price:
    is_valid_setup = False
  risk_per_unit = stop_loss - entry_price
  reward_per_unit = entry_price - take_profit

if is_valid_setup and risk_per_unit > 0:
  position_size_units = dollar_risk / risk_per_unit
  notional_value = position_size_units * entry_price
  margin_required = notional_value / leverage
  potential_profit = position_size_units * reward_per_unit
  rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0
else:
  position_size_units, notional_value, margin_required, potential_profit, rr_ratio = (
      0,
      0,
      0,
      0,
      0,
  )

with col_outputs:
  st.subheader("4. Execution Metrics & AI Copilot")

  m1, m2 = st.columns(2)
  with m1:
    st.metric(
        label="Position Size (Units)", value=f"{position_size_units:,.4f}"
    )
    st.metric(label="Total Position Value", value=f"${notional_value:,.2f}")
    st.metric(label="Margin Required", value=f"${margin_required:,.2f}")

  with m2:
    st.metric(
        label="Max Dollar Risk",
        value=f"${dollar_risk:,.2f}",
        delta=f"-{risk_pct}%",
        delta_color="inverse",
    )
    st.metric(label="Potential Profit", value=f"${potential_profit:,.2f}")
    st.metric(label="Risk-to-Reward (R:R)", value=f"1 : {rr_ratio:.2f}")

  st.markdown("---")
  st.subheader("🧠 AI Risk Copilot Analysis")

  if st.button("Generate AI Risk Critique"):
    if not client:
      st.warning("API key missing. Showing baseline validation.")
      if rr_ratio >= 2.0:
        st.success(f"Good setup with 1:{rr_ratio:.2f} R:R ratio.")
      else:
        st.warning(f"Low R:R ratio (1:{rr_ratio:.2f}). Adjust target.")
    else:
      with st.spinner("AI Risk Analyst reviewing trade setup..."):
        prompt = f"""
                You are a professional risk management copilot. Analyze this trade setup:
                - Direction: {direction}
                - Account Balance: ${account_balance:,.2f}
                - Risk Percentage: {risk_pct}% (${dollar_risk:,.2f})
                - Entry: ${entry_price:,.2f}
                - Stop Loss: ${stop_loss:,.2f}
                - Take Profit: ${take_profit:,.2f}
                - Calculated Risk-to-Reward Ratio: 1:{rr_ratio:.2f}
                
                Provide a short, professional bullet-point critique on whether this setup is sound, highlighting any psychological or mathematical risk pitfalls. Keep it under 4 sentences.
                """
        response = client.models.generate_content(
            model="gemini-3.8-flash", contents=prompt
        )
        st.info(response.text)