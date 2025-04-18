import streamlit as st
import sys
import traceback
import os
import logging
import inspect
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import plotly.express as px
from io import BytesIO
import json
import functools

# Add the project root to Python path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Import utility functions
from utils import safely_create_scenario, safely_create_dealer, test_supabase_connection

# Import models
from src.models.dealer import DealerOutlet
from src.models.scenario import Scenario

# Import calculations
from src.calculations.sales import SalesCalculator
from src.calculations.financial import FinancialCalculator

# Import Excel utilities
from src.excel.parser import ExcelParser
from src.excel.report import ReportGenerator

# Import database repositories
from src.database.repositories import DealerRepository, ScenarioRepository, ResultsRepository

# Import Supabase configuration
from src.database.supabase_config import get_supabase_client

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Set up logging
logging.basicConfig(
    filename="logs/app_log.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_interaction(action, details=None):
    """Log user interactions with the app"""
    if details:
        logging.info(f"USER ACTION: {action} - {details}")
    else:
        logging.info(f"USER ACTION: {action}")

def handle_exceptions(func):
    """Decorator to handle exceptions and provide user feedback"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = str(e)
            logging.error(f"Error in {func.__name__}: {error_message}")
            logging.error(traceback.format_exc())
            st.error(f"An error occurred: {error_message}")
            return None
    return wrapper

@handle_exceptions
def scenario_form():
    """Form for entering scenario information"""
    log_interaction("Opening scenario form")
    
    current_scenario = st.session_state.get("scenario", None)
    
    st.subheader("Scenario Configuration")
    st.caption("Define the parameters for this feasibility analysis scenario.")

    # Use tabs for better organization
    tab_basic, tab_financial, tab_growth, tab_margins, tab_maintenance = st.tabs([
        "📄 Basic Info", "💰 Financial", "📈 Growth", "💲 Margins", "🔧 Maintenance"
    ])

    with tab_basic:
        st.markdown("##### Scenario Identification")
        col1, col2 = st.columns(2)
        with col1:
            scenario_name = st.text_input("Scenario Name", value=current_scenario.name if current_scenario else "", help="Unique name for this scenario.")
        with col2:
            scenario_description = st.text_area("Description", value=current_scenario.description if current_scenario and hasattr(current_scenario, 'description') else "", help="Optional description of the scenario assumptions.")
        
        analysis_years = st.slider(
            "Analysis Period (Years)", 
            min_value=1, 
            max_value=30, 
            value=current_scenario.analysis_years if current_scenario else 10,
            help="The number of years to include in the financial projections."
        )
        st.divider()

    with tab_financial:
        st.markdown("##### Core Financial Assumptions")
        col1, col2, col3 = st.columns(3)
        with col1:
            discount_rate = st.number_input(
                "Discount Rate (%)", 
                min_value=0.0, 
                max_value=100.0, 
                value=float(current_scenario.discount_rate * 100) if current_scenario else 10.0,
                step=0.5,
                help="Rate used to calculate the present value of future cash flows (e.g., WACC)."
            ) / 100
        with col2:
            inflation_rate = st.number_input(
                "Inflation Rate (%)", 
                min_value=0.0, 
                max_value=100.0, 
                value=float(current_scenario.inflation_rate * 100) if current_scenario else 5.0,
                step=0.5,
                help="Assumed annual rate of inflation, used for escalating costs."
            ) / 100
        with col3:
            tax_rate = st.number_input(
                "Corporate Tax Rate (%)", 
                min_value=0.0, 
                max_value=100.0, 
                value=float(current_scenario.tax_rate * 100) if current_scenario else 35.0,
                step=0.5,
                help="Applicable corporate income tax rate."
            ) / 100
        st.divider()

    with tab_growth:
        st.markdown("##### Annual Sales Growth Rates (%)")
        st.caption("Enter the expected year-on-year growth in sales volume for each product.")
        
        # Initialize growth rates
        growth_rates = st.session_state.get("growth_rates", {})
        
        # Ensure growth_rates is in correct format
        if not isinstance(growth_rates, dict):
            growth_rates = {}
            
        if not growth_rates and current_scenario and hasattr(current_scenario, 'default_growth_rates'):
            # Handle different possible formats of default_growth_rates
            try:
                if isinstance(current_scenario.default_growth_rates, dict):
                    for product in ['pmg', 'hsd', 'xtron', 'lubricants']:
                        mapped_key = 'hobc' if product == 'xtron' else ('lube' if product == 'lubricants' else product)
                        rate_dict = current_scenario.default_growth_rates.get(mapped_key, {})
                        
                        # Ensure rate_dict is a dictionary
                        if isinstance(rate_dict, dict):
                            growth_rates[product] = rate_dict
                        else:
                            # If it's not a dictionary, try to convert to float directly
                            try:
                                value = float(rate_dict)
                                growth_rates[product] = {1: value}
                            except (TypeError, ValueError):
                                growth_rates[product] = {1: 0.05}  # Default 5% if conversion fails
                else:
                    # Default if not a dict
                    growth_rates = {
                        'pmg': {1: 0.05}, 
                        'hsd': {1: 0.05}, 
                        'xtron': {1: 0.06}, 
                        'lubricants': {1: 0.01}
                    }
            except Exception as e:
                logging.error(f"Error parsing growth rates: {str(e)}")
                growth_rates = {
                    'pmg': {1: 0.05}, 
                    'hsd': {1: 0.05}, 
                    'xtron': {1: 0.06}, 
                    'lubricants': {1: 0.01}
                }
        elif not growth_rates:  # Default if no session state or current scenario
             growth_rates = {
                'pmg': {1: 0.05}, 
                'hsd': {1: 0.05}, 
                'xtron': {1: 0.06}, 
                'lubricants': {1: 0.01}
            }

        # Add advanced growth rate editing
        growth_mode = st.radio(
            "Growth Rate Mode",
            options=["Simple (Same rate for all years)", "Advanced (Different rates per year)"],
            horizontal=True,
            help="Choose whether to use the same growth rate for all years or set different rates for specific years."
        )
        
        if growth_mode == "Simple (Same rate for all years)":
            # Simple mode - single growth rate for all years
            col1, col2 = st.columns(2)
            with col1:
                pmg_growth = st.number_input(
                    "PMG Growth Rate (%)", 
                    value=float(next(iter(growth_rates.get('pmg', {1: 0.05}).values()), 0.05)) * 100, 
                    step=0.5, 
                    help="Annual growth rate for PMG sales volume."
                ) / 100
                
                hsd_growth = st.number_input(
                    "HSD Growth Rate (%)", 
                    value=float(next(iter(growth_rates.get('hsd', {1: 0.05}).values()), 0.05)) * 100, 
                    step=0.5, 
                    help="Annual growth rate for HSD sales volume."
                ) / 100
            
            with col2:
                xtron_growth = st.number_input(
                    "XTRON/HOBC Growth Rate (%)", 
                    value=float(next(iter(growth_rates.get('xtron', {1: 0.06}).values()), 0.06)) * 100, 
                    step=0.5, 
                    help="Annual growth rate for XTRON/HOBC sales volume."
                ) / 100
                
                lube_growth = st.number_input(
                    "Lubricants Growth Rate (%)", 
                    value=float(next(iter(growth_rates.get('lubricants', {1: 0.01}).values()), 0.01)) * 100, 
                    step=0.5, 
                    help="Annual growth rate for Lubricants sales volume."
                ) / 100
            
            # Update growth_rates with simple values
            growth_rates = {
                'pmg': {1: pmg_growth},
                'hsd': {1: hsd_growth},
                'xtron': {1: xtron_growth},
                'lubricants': {1: lube_growth}
            }
        else:
            # Advanced mode - different growth rates per year
            st.info("Enter growth rates for specific years. Rates for years not specified will be interpolated.")
            
            # Determine analysis years
            max_years = current_scenario.analysis_years if current_scenario else 15
            
            # Create tabs for each product
            product_tabs = st.tabs(["PMG", "HSD", "XTRON/HOBC", "Lubricants"])
            
            # Map UI tab labels to internal product keys
            product_map = {
                0: 'pmg',
                1: 'hsd',
                2: 'xtron',
                3: 'lubricants'
            }
            
            for i, tab in enumerate(product_tabs):
                product_key = product_map[i]
                with tab:
                    product_growth = growth_rates.get(product_key, {1: 0.05 if product_key != 'lubricants' else 0.01})
                    
                    # Convert to ordered list of (year, rate) tuples for display
                    year_rates = [(int(year), float(rate)) for year, rate in product_growth.items()]
                    year_rates.sort(key=lambda x: x[0])
                    
                    # Show existing data in a table
                    if year_rates:
                        st.write(f"Current growth rates for {product_key.upper()}")
                        rate_df = pd.DataFrame(year_rates, columns=["Year", "Growth Rate"])
                        rate_df["Growth Rate (%)"] = rate_df["Growth Rate"].apply(lambda x: f"{x*100:.2f}%")
                        st.dataframe(rate_df[["Year", "Growth Rate (%)"]], hide_index=True)
                    
                    # Add new year/rate
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        new_year = st.number_input(
                            f"Year", 
                            min_value=1, 
                            max_value=max_years,
                            value=1,
                            key=f"new_year_{product_key}"
                        )
                    
                    with col2:
                        new_rate = st.number_input(
                            f"Growth Rate (%)", 
                            min_value=-20.0, 
                            max_value=100.0,
                            value=5.0 if product_key != 'lubricants' else 1.0,
                            step=0.5,
                            key=f"new_rate_{product_key}"
                        ) / 100
                    
                    with col3:
                        if st.button("Add/Update", key=f"add_rate_{product_key}"):
                            # Update the growth rate for this product and year
                            if product_key not in growth_rates:
                                growth_rates[product_key] = {}
                            
                            growth_rates[product_key][new_year] = new_rate
                            st.success(f"Added growth rate for Year {new_year}")
                            st.rerun()  # Refresh to show the updated table
                    
                    # Option to clear all rates for this product
                    if st.button("Clear All Rates", key=f"clear_rates_{product_key}"):
                        if product_key in growth_rates:
                            # Keep only the first year with a default rate
                            default_rate = 0.05 if product_key != 'lubricants' else 0.01
                            growth_rates[product_key] = {1: default_rate}
                            st.success(f"Cleared growth rates for {product_key.upper()}")
                            st.rerun()
        
        # Store back in session state for persistence within the form
        st.session_state.growth_rates = growth_rates
        st.divider()

    with tab_margins:
        st.markdown("##### Product Margins (PKR per Liter)")
        st.caption("Enter the expected profit margin per liter for each product.")
        
        # Initialize margins
        margins = st.session_state.get("margins", {})
        
        # Ensure margins is in correct format
        if not isinstance(margins, dict):
            margins = {}
            
        if not margins and current_scenario and hasattr(current_scenario, 'default_margins'):
            # Handle different possible formats of default_margins
            try:
                if isinstance(current_scenario.default_margins, dict):
                    for product in ['pmg', 'hsd', 'xtron', 'lubricants']:
                        mapped_key = 'hobc' if product == 'xtron' else ('lube' if product == 'lubricants' else product)
                        margin_dict = current_scenario.default_margins.get(mapped_key, {})
                        
                        # Ensure margin_dict is a dictionary
                        if isinstance(margin_dict, dict):
                            margins[product] = margin_dict
                        else:
                            # If it's not a dictionary, try to convert to float directly
                            try:
                                value = float(margin_dict)
                                margins[product] = {1: value}
                            except (TypeError, ValueError):
                                # Default values if conversion fails
                                default_values = {'pmg': 5.0, 'hsd': 4.0, 'xtron': 6.0, 'lubricants': 100.0}
                                margins[product] = {1: default_values.get(product, 5.0)}
                else:
                    # Default if not a dict
                    margins = {
                        'pmg': {1: 5.0}, 
                        'hsd': {1: 4.0}, 
                        'xtron': {1: 6.0}, 
                        'lubricants': {1: 100.0}
                    }
            except Exception as e:
                logging.error(f"Error parsing margins: {str(e)}")
                margins = {
                    'pmg': {1: 5.0}, 
                    'hsd': {1: 4.0}, 
                    'xtron': {1: 6.0}, 
                    'lubricants': {1: 100.0}
                }
        elif not margins:
            margins = {
                'pmg': {1: 5.0}, 
                'hsd': {1: 4.0}, 
                'xtron': {1: 6.0}, 
                'lubricants': {1: 100.0}
            }

        # Add advanced margin editing
        margin_mode = st.radio(
            "Margin Mode",
            options=["Simple (Same margin for all years)", "Advanced (Different margins per year)"],
            horizontal=True,
            help="Choose whether to use the same margin for all years or set different margins for specific years."
        )
        
        if margin_mode == "Simple (Same margin for all years)":
            # Simple mode - single margin for all years
            col1, col2 = st.columns(2)
            with col1:
                pmg_margin = st.number_input(
                    "PMG Margin (PKR/L)", 
                    value=float(next(iter(margins.get('pmg', {1: 5.0}).values()), 5.0)), 
                    step=0.1, 
                    help="Profit margin per liter of PMG."
                )
                
                hsd_margin = st.number_input(
                    "HSD Margin (PKR/L)", 
                    value=float(next(iter(margins.get('hsd', {1: 4.0}).values()), 4.0)), 
                    step=0.1, 
                    help="Profit margin per liter of HSD."
                )
            
            with col2:
                xtron_margin = st.number_input(
                    "XTRON/HOBC Margin (PKR/L)", 
                    value=float(next(iter(margins.get('xtron', {1: 6.0}).values()), 6.0)), 
                    step=0.1, 
                    help="Profit margin per liter of XTRON/HOBC."
                )
                
                lube_margin = st.number_input(
                    "Lubricants Margin (PKR/L)", 
                    value=float(next(iter(margins.get('lubricants', {1: 100.0}).values()), 100.0)), 
                    step=1.0, 
                    help="Profit margin per liter of Lubricants."
                )
            
            # Update margins with simple values
            margins = {
                'pmg': {1: pmg_margin},
                'hsd': {1: hsd_margin},
                'xtron': {1: xtron_margin},
                'lubricants': {1: lube_margin}
            }
        else:
            # Advanced mode - different margins per year
            st.info("Enter margins for specific years. Margins for years not specified will be interpolated.")
            
            # Determine analysis years
            max_years = current_scenario.analysis_years if current_scenario else 15
            
            # Create tabs for each product
            product_tabs = st.tabs(["PMG", "HSD", "XTRON/HOBC", "Lubricants"])
            
            # Map UI tab labels to internal product keys
            product_map = {
                0: 'pmg',
                1: 'hsd',
                2: 'xtron',
                3: 'lubricants'
            }
            
            # Default margins for each product
            default_margins = {
                'pmg': 5.0,
                'hsd': 4.0,
                'xtron': 6.0,
                'lubricants': 100.0
            }
            
            for i, tab in enumerate(product_tabs):
                product_key = product_map[i]
                with tab:
                    product_margin = margins.get(product_key, {1: default_margins.get(product_key, 5.0)})
                    
                    # Convert to ordered list of (year, margin) tuples for display
                    year_margins = [(int(year), float(margin)) for year, margin in product_margin.items()]
                    year_margins.sort(key=lambda x: x[0])
                    
                    # Show existing data in a table
                    if year_margins:
                        st.write(f"Current margins for {product_key.upper()}")
                        margin_df = pd.DataFrame(year_margins, columns=["Year", "Margin"])
                        margin_df["Margin (PKR/L)"] = margin_df["Margin"].apply(lambda x: f"{x:.2f}")
                        st.dataframe(margin_df[["Year", "Margin (PKR/L)"]], hide_index=True)
                    
                    # Add new year/margin
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        new_year = st.number_input(
                            f"Year", 
                            min_value=1, 
                            max_value=max_years,
                            value=1,
                            key=f"new_year_margin_{product_key}"
                        )
                    
                    with col2:
                        step_value = 1.0 if product_key == 'lubricants' else 0.1
                        default_value = default_margins.get(product_key, 5.0)
                        
                        new_margin = st.number_input(
                            f"Margin (PKR/L)", 
                            min_value=0.0, 
                            max_value=1000.0,
                            value=default_value,
                            step=step_value,
                            key=f"new_margin_{product_key}"
                        )
                    
                    with col3:
                        if st.button("Add/Update", key=f"add_margin_{product_key}"):
                            # Update the margin for this product and year
                            if product_key not in margins:
                                margins[product_key] = {}
                            
                            margins[product_key][new_year] = new_margin
                            st.success(f"Added margin for Year {new_year}")
                            st.rerun()  # Refresh to show the updated table
                    
                    # Option to clear all margins for this product
                    if st.button("Clear All Margins", key=f"clear_margins_{product_key}"):
                        if product_key in margins:
                            # Reset to default margin for year 1
                            default_value = default_margins.get(product_key, 5.0)
                            margins[product_key] = {1: default_value}
                            st.success(f"Cleared margins for {product_key.upper()}")
                            st.rerun()
        
        # Store back in session state
        st.session_state.margins = margins
        st.divider()

    with tab_maintenance:
        st.markdown("##### Major Maintenance Costs")
        st.caption("Enter costs for significant, non-annual maintenance events.")
        col1, col2 = st.columns(2)
        with col1:
            signage_maintenance = st.number_input(
                "Signage Maintenance Cost (PKR)", 
                value=float(current_scenario.signage_maintenance) if current_scenario else 10000000.0,
                help="Estimated cost for major signage overhaul."
            )
            other_maintenance = st.number_input(
                "Other Major Maintenance Cost (PKR)", 
                value=float(current_scenario.other_maintenance) if current_scenario else 2000000.0,
                help="Estimated cost for other significant periodic maintenance."
            )
        with col2:
             # Fix default maintenance year values to ensure they don't exceed analysis_years
             default_signage_year = min(int(current_scenario.signage_maintenance_year) if current_scenario else 7, analysis_years)
             signage_maintenance_year = st.number_input(
                "Signage Maintenance Year", 
                min_value=1, 
                max_value=analysis_years, 
                value=default_signage_year,
                help="Year in which the signage maintenance cost occurs."
            )
             default_other_year = min(int(current_scenario.other_maintenance_year) if current_scenario else 5, analysis_years)
             other_maintenance_year = st.number_input(
                "Other Maintenance Year", 
                min_value=1, 
                max_value=analysis_years, 
                value=min(int(current_scenario.other_maintenance_year) if current_scenario else 5, analysis_years),
                help="Year in which the other major maintenance cost occurs."
            )
        st.divider()

    # Save Button (outside tabs)
    submit_button = st.button("💾 Save Scenario Configuration", type="primary")
    
    if submit_button:
        if not scenario_name:
            st.error("Scenario name is required")
            return current_scenario
        
        try:
            # Prepare growth rates and margins for saving as proper year-keyed dictionaries
            internal_growth_rates = {}
            for product, rate in growth_rates.items():
                # Ensure rate is a float
                try:
                    rate_value = float(rate)
                except (TypeError, ValueError):
                    rate_value = 0.0
                    logging.warning(f"Invalid growth rate for {product}: {rate}, using 0.0 instead")
                
                # Store as {1: rate} to match expected Dict[int, float] structure
                internal_growth_rates[product] = {1: rate_value}
                 
            internal_margins = {}
            for product, margin_val in margins.items():
                # Ensure margin is a float
                try:
                    margin_value = float(margin_val)
                except (TypeError, ValueError):
                    margin_value = 0.0
                    logging.warning(f"Invalid margin for {product}: {margin_val}, using 0.0 instead")
                
                # Store as {1: margin_val}
                internal_margins[product] = {1: margin_value}

            # Map keys for database compatibility if needed (e.g., xtron -> hobc)
            db_growth_rates = {
                ('hobc' if k == 'xtron' else ('lube' if k == 'lubricants' else k)): v 
                for k, v in internal_growth_rates.items()
            }
            db_margins = {
                ('hobc' if k == 'xtron' else ('lube' if k == 'lubricants' else k)): v 
                for k, v in internal_margins.items()
            }
            
            scenario_params = {
                'name': scenario_name,
                'description': scenario_description,
                'discount_rate': discount_rate,
                'inflation_rate': inflation_rate,
                'tax_rate': tax_rate,
                'analysis_years': analysis_years,
                'default_growth_rates': db_growth_rates, # Use mapped keys
                'default_margins': db_margins,       # Use mapped keys
                'signage_maintenance': signage_maintenance,
                'signage_maintenance_year': signage_maintenance_year,
                'other_maintenance': other_maintenance,
                'other_maintenance_year': other_maintenance_year
            }
            
            if current_scenario and hasattr(current_scenario, 'id'):
                scenario_params['id'] = current_scenario.id
            
            scenario = safely_create_scenario(**scenario_params)
            scenario_id = ScenarioRepository.save(scenario)
            scenario.id = scenario_id
            
            # Update session state
            st.session_state.scenario = scenario
            st.session_state.scenario_id = scenario_id
            # Keep UI consistent with saved data
            st.session_state.growth_rates = growth_rates 
            st.session_state.margins = margins
            
            log_interaction("Saved scenario information", f"Scenario: {scenario.name}")
            st.success(f"✅ Scenario '{scenario_name}' saved successfully! ID: {scenario_id}")
            
            # Optionally rerun
            # st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error saving scenario: {str(e)}")
            logging.error(f"Error in scenario_form save: {str(e)}")
            logging.error(traceback.format_exc())
            
    return st.session_state.get("scenario", None)

@handle_exceptions
def dealer_form():
    """Form for entering dealer information"""
    log_interaction("Opening dealer form")
    
    # Get current dealer from session state if it exists
    current_dealer = st.session_state.get("dealer", None)
    
    st.subheader("Dealer Information")
    st.caption("Enter the basic details of the dealership.")
    
    # Basic information
    col1, col2 = st.columns(2)
    with col1:
        dealer_name = st.text_input("Dealer Name", value=current_dealer.name if current_dealer else "", help="The official name of the dealership.")
    with col2:
        dealer_location = st.text_input("Location", value=current_dealer.location if current_dealer else "", help="The city or primary location of the dealership.")
    
    col1, col2 = st.columns(2)
    with col1:
        district = st.text_input("District", value=current_dealer.district if current_dealer and hasattr(current_dealer, 'district') else "", help="The administrative district.")
    with col2:
        feeding_point = st.text_input("Feeding Point", value=current_dealer.feeding_point if current_dealer and hasattr(current_dealer, 'feeding_point') else "", help="The supply depot or source.")
    
    col1, col2 = st.columns(2)
    with col1:
        area_executive = st.text_input("Area Executive", value=current_dealer.area_executive if current_dealer and hasattr(current_dealer, 'area_executive') else "", help="APL representative responsible for the area.")
    with col2:
        referred_by = st.text_input("Referred By", value=current_dealer.referred_by if current_dealer and hasattr(current_dealer, 'referred_by') else "", help="Person or entity who referred this dealer prospect.")
        
    st.divider()

    # Sales volumes
    st.subheader("Projected Sales Volumes (First Year)")
    st.caption("Enter the estimated average daily sales volume for each product.")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pmg_sales = st.number_input("PMG Sales (L/day)", min_value=0.0, value=float(current_dealer.pmg_sales) if current_dealer else 0.0, help="Projected daily sales volume for Premier Motor Gasoline.")
    with col2:
        hsd_sales = st.number_input("HSD Sales (L/day)", min_value=0.0, value=float(current_dealer.hsd_sales) if current_dealer else 0.0, help="Projected daily sales volume for High-Speed Diesel.")
    with col3:
        hobc_sales = st.number_input("HOBC/XTRON Sales (L/day)", min_value=0.0, value=float(current_dealer.hobc_sales) if current_dealer else 0.0, help="Projected daily sales volume for High Octane Blending Component / XTRON.")
    with col4:
        lube_sales = st.number_input("Lube Sales (L/day)", min_value=0.0, value=float(current_dealer.lube_sales) if current_dealer else 0.0, help="Projected daily sales volume for Lubricants.")
    
    st.divider()
    
    # Investment items
    st.subheader("Investment Items")
    st.caption("List all planned capital expenditures. You can edit directly in the table, add rows, or import/export via Excel.")

    # Initialize investment items if not in session state
    if "investment_items" not in st.session_state:
        # Use current dealer's items or default if none
        default_items = [
            {"name": "Digital Pylon Sign (9.2 M)", "cost": 5000000, "quantity": 1},
            {"name": "Canopy Spreaders (Full lighting system with LED's)", "cost": 200000, "quantity": 1},
            {"name": "Dispenser", "cost": 300000, "quantity": 2},
            {"name": "Underground Tank", "cost": 1500000, "quantity": 4}
        ]
        st.session_state.investment_items = (
            current_dealer.investment_items 
            if current_dealer and hasattr(current_dealer, 'investment_items') and current_dealer.investment_items 
            else default_items
        )
    
    # Convert cost and quantity to numeric for the editor
    items_df_input = pd.DataFrame(st.session_state.investment_items)
    items_df_input['cost'] = pd.to_numeric(items_df_input['cost'], errors='coerce').fillna(0)
    items_df_input['quantity'] = pd.to_numeric(items_df_input['quantity'], errors='coerce').fillna(1).astype(int)

    # Use st.data_editor for interactive editing
    edited_df = st.data_editor(
        items_df_input,
        num_rows="dynamic", # Allow adding/deleting rows
        column_config={
            "name": st.column_config.TextColumn("Item Name", required=True, help="Description of the investment item."),
            "cost": st.column_config.NumberColumn("Cost (PKR)", format="%.0f", required=True, help="Cost per unit of the item."),
            "quantity": st.column_config.NumberColumn("Quantity", format="%d", required=True, min_value=1, help="Number of units.")
        },
        key="investment_editor"
    )

    # Update session state after editing
    # Convert back to list of dicts
    st.session_state.investment_items = edited_df.to_dict('records')
    
    # Import/Export functionality
    col1, col2 = st.columns(2)
    with col1:
        # Export Template Button
        sample_df = pd.DataFrame([
            {"name": "Item Name Example 1", "cost": 100000, "quantity": 1},
            {"name": "Item Name Example 2", "cost": 50000, "quantity": 2}
        ])
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sample_df.to_excel(writer, sheet_name='Investment Items', index=False)
            worksheet = writer.sheets['Investment Items']
            for i, col in enumerate(sample_df.columns):
                column_width = max(sample_df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, column_width)
        output.seek(0)
        
        st.download_button(
            label="📄 Export Investment Items Template",
            data=output,
            file_name="investment_items_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download an Excel template to fill in investment items offline."
        )

    with col2:
        # Import Button
        uploaded_file = st.file_uploader("⬆️ Import Investment Items", type=["xlsx", "xls"], help="Upload an Excel file following the template structure.")
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                required_columns = {"name", "cost", "quantity"}
                if not all(col in df.columns for col in required_columns):
                    st.error(f"Imported file must contain columns: {', '.join(required_columns)}")
                else:
                    items = df.to_dict('records')
                    st.session_state.investment_items = items
                    st.success(f"Successfully imported {len(items)} investment items. The table above is updated.")
                    # No rerun needed as data editor updates reactively
            except Exception as e:
                st.error(f"Error importing file: {str(e)}")
                logging.error(f"Error importing investment items: {str(e)}")
    
    st.divider()

    # Calculate and display total investment dynamically
    total_investment = sum(float(item.get("cost", 0)) * int(item.get("quantity", 1)) for item in st.session_state.investment_items)
    st.metric(label="Total Initial Investment", value=f"PKR {total_investment:,.0f}", help="Sum of (Cost * Quantity) for all items listed above.")
    
    st.divider()
    
    # Operating costs
    st.subheader("Operating Costs")
    operating_costs = st.number_input(
        "Estimated Monthly Operating Costs (PKR)", 
        min_value=0.0, 
        value=float(current_dealer.operating_costs) if current_dealer and hasattr(current_dealer, 'operating_costs') else 0.0,
        help="Enter the total estimated monthly operational expenses (salaries, utilities, etc.)."
    )
    
    st.divider()
    
    # Save button
    submit_button = st.button("💾 Save Dealer Information", type="primary")
    
    if submit_button:
        # Check required fields
        if not dealer_name:
            st.error("Dealer name is required")
            return current_dealer
        if not dealer_location:
            st.error("Dealer location is required")
            return current_dealer
            
        # Prepare dealer parameters
        dealer_params = {
            "name": dealer_name,
            "location": dealer_location,
            "district": district,
            "feeding_point": feeding_point,
            "area_executive": area_executive,
            "referred_by": referred_by,
            "pmg_sales": pmg_sales,
            "hsd_sales": hsd_sales,
            "hobc_sales": hobc_sales, # Note: Model uses hobc_sales
            "lube_sales": lube_sales,
            "initial_investment": total_investment, # Use dynamically calculated total
            "operating_costs": operating_costs,
            # Ensure investment_items are saved correctly
            "investment_items": [
                {"name": item.get("name"), "cost": float(item.get("cost", 0)), "quantity": int(item.get("quantity", 1))}
                for item in st.session_state.investment_items if item.get("name") # Only include items with a name
            ]
        }
        
        # Add ID if exists
        if current_dealer and hasattr(current_dealer, 'id'):
            dealer_params["id"] = current_dealer.id
        
        try:
            # Create dealer object safely
            print(dealer_params)
            dealer = safely_create_dealer(**dealer_params)
            
            # Save to database
            dealer_id = DealerRepository.save(dealer)
            dealer.id = dealer_id # Update object with saved ID
            
            # Save to session state
            st.session_state.dealer = dealer
            st.session_state.dealer_id = dealer_id
            
            log_interaction("Saved dealer information", f"Dealer: {dealer.name}")
            st.success(f"✅ Dealer information saved successfully! ID: {dealer_id}")
            
            # Optional: Rerun to reflect saved state cleanly, though not strictly necessary
            # st.rerun() 
            
        except Exception as e:
            st.error(f"❌ Error saving dealer: {str(e)}")
            logging.error(f"Error in dealer_form save: {str(e)}")
            logging.error(traceback.format_exc())
        
    return st.session_state.get("dealer", None) # Return the potentially updated dealer from session state

def show_dealer_summary(dealer):
    """Display a summary of the current dealer"""
    st.subheader("Current Dealer")
    st.write(f"**Name:** {dealer.name}")
    st.write(f"**Location:** {dealer.location}")
    if dealer.district:
        st.write(f"**District:** {dealer.district}")
    if dealer.feeding_point:
        st.write(f"**Feeding Point:** {dealer.feeding_point}")
    
    # Show investment summary
    total_investment = dealer.initial_investment if dealer.initial_investment else 0
    st.write(f"**Total Investment:** PKR {total_investment:,.0f}")
    
    # Show sales volumes
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write(f"**PMG Sales:** {dealer.pmg_sales:,.0f} liters")
    with col2:
        st.write(f"**HSD Sales:** {dealer.hsd_sales:,.0f} liters")
    with col3:
        st.write(f"**HOBC Sales:** {dealer.hobc_sales:,.0f} liters")
    with col4:
        st.write(f"**Lube Sales:** {dealer.lube_sales:,.0f} liters")

def show_scenario_summary(scenario):
    """Display a summary of the current scenario"""
    st.subheader("Current Scenario")
    st.write(f"**Name:** {scenario.name}")
    if scenario.description:
        st.write(f"**Description:** {scenario.description}")
    
    # Financial parameters
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Discount Rate:** {scenario.discount_rate:.1%}")
    with col2:
        st.write(f"**Inflation Rate:** {scenario.inflation_rate:.1%}")
    with col3:
        st.write(f"**Tax Rate:** {scenario.tax_rate:.1%}")
    
    st.write(f"**Analysis Years:** {scenario.analysis_years}")
    
    # Show maintenance costs
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Signage Maintenance:** PKR {scenario.signage_maintenance:,.0f} (Year {scenario.signage_maintenance_year})")
    with col2:
        st.write(f"**Other Maintenance:** PKR {scenario.other_maintenance:,.0f} (Year {scenario.other_maintenance_year})")

@handle_exceptions
def calculate_financial_metrics(dealer, scenario):
    """Calculate financial metrics for a dealer and scenario"""
    if not dealer or not scenario:
        st.error("Please provide both dealer and scenario information.")
        return None
    
    log_interaction("Calculating financial metrics", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
    
    try:
        # Debug: Log the types of growth rates and margins
        logging.info(f"Growth rates type: {type(scenario.default_growth_rates)}")
        logging.info(f"Margins type: {type(scenario.default_margins)}")
        
        # Initialize default dictionaries if missing or not a dictionary
        if not hasattr(scenario, 'default_growth_rates') or not isinstance(scenario.default_growth_rates, dict):
            logging.warning("Missing or invalid growth rates, initializing empty dictionary")
            scenario.default_growth_rates = {}
            
        if not hasattr(scenario, 'default_margins') or not isinstance(scenario.default_margins, dict):
            logging.warning("Missing or invalid margins, initializing empty dictionary")
            scenario.default_margins = {}
            
        # Fix: Ensure each product has valid growth rates and margins
        for product in ['pmg', 'hsd', 'hobc', 'lube']:
            # Check growth rates
            if product not in scenario.default_growth_rates:
                logging.warning(f"Missing growth rates for {product}, initializing empty")
                scenario.default_growth_rates[product] = {1: 0.05}  # Default 5% growth
            
            # Convert growth rates to dictionary if not already
            if not isinstance(scenario.default_growth_rates[product], dict):
                try:
                    value = float(scenario.default_growth_rates[product])
                    logging.info(f"Converting {product} growth rate from {value} to dict")
                    scenario.default_growth_rates[product] = {1: value}  # Set as default for year 1
                except (TypeError, ValueError) as e:
                    logging.error(f"Error converting growth rate for {product}: {e}")
                    scenario.default_growth_rates[product] = {1: 0.05}  # Default to 5% growth
            
            # Check margins
            if product not in scenario.default_margins:
                logging.warning(f"Missing margins for {product}, initializing default")
                default_values = {'pmg': 5.0, 'hsd': 4.0, 'hobc': 6.0, 'lube': 100.0}
                scenario.default_margins[product] = {1: default_values.get(product, 5.0)}
                
            # Convert margins to dictionary if not already
            if not isinstance(scenario.default_margins[product], dict):
                try:
                    value = float(scenario.default_margins[product])
                    logging.info(f"Converting {product} margin from {value} to dict")
                    scenario.default_margins[product] = {1: value}  # Set as default for all years
                except (TypeError, ValueError) as e:
                    logging.error(f"Error converting margin for {product}: {e}")
                    default_values = {'pmg': 5.0, 'hsd': 4.0, 'hobc': 6.0, 'lube': 100.0}
                    scenario.default_margins[product] = {1: default_values.get(product, 5.0)}
            
            # Ensure all values in growth rates are floats
            for year, rate in list(scenario.default_growth_rates[product].items()):
                try:
                    scenario.default_growth_rates[product][year] = float(rate)
                except (TypeError, ValueError):
                    logging.warning(f"Invalid growth rate value for {product}, year {year}: {rate}")
                    scenario.default_growth_rates[product][year] = 0.05  # Default 5% growth
            
            # Ensure all values in margins are floats
            for year, margin in list(scenario.default_margins[product].items()):
                try:
                    scenario.default_margins[product][year] = float(margin)
                except (TypeError, ValueError):
                    logging.warning(f"Invalid margin value for {product}, year {year}: {margin}")
                    default_values = {'pmg': 5.0, 'hsd': 4.0, 'hobc': 6.0, 'lube': 100.0}
                    scenario.default_margins[product][year] = default_values.get(product, 5.0)
        
        # Run scenario calculations
        try:
            results = SalesCalculator.run_scenario(dealer, scenario)
        except Exception as calc_error:
            logging.error(f"Error in SalesCalculator.run_scenario: {str(calc_error)}")
            logging.error(traceback.format_exc())
            st.error(f"Calculation error: {str(calc_error)}")
            return None
        
        # Save results to database if IDs are available
        if hasattr(dealer, 'id') and dealer.id and hasattr(scenario, 'id') and scenario.id:
            logging.info(f"Saving results to database for dealer {dealer.id} and scenario {scenario.id}")
            ResultsRepository.save_result(dealer.id, scenario.id, results)
        else:
            logging.warning("Could not save results to database: missing dealer or scenario ID")
        
        # Save results to session state
        st.session_state.results = results
        
        return results
    except AttributeError as e:
        error_msg = str(e)
        if "'int' object has no attribute 'values'" in error_msg or "'dict' object" in error_msg:
            st.error("Error: An issue was detected with the data format. Please check your growth rates and margins data.")
            logging.error(f"Type error in calculations: {error_msg}")
            
            # Provide more detailed error information for debugging
            logging.error(f"Scenario object type: {type(scenario)}")
            if hasattr(scenario, 'default_growth_rates'):
                logging.error(f"Growth rates type: {type(scenario.default_growth_rates)}")
                if isinstance(scenario.default_growth_rates, dict):
                    for k, v in scenario.default_growth_rates.items():
                        logging.error(f"  {k}: {type(v)}")
            if hasattr(scenario, 'default_margins'):
                logging.error(f"Margins type: {type(scenario.default_margins)}")
                if isinstance(scenario.default_margins, dict):
                    for k, v in scenario.default_margins.items():
                        logging.error(f"  {k}: {type(v)}")
        else:
            st.error(f"Attribute error: {error_msg}")
            logging.error(f"Attribute error in calculations: {error_msg}")
        return None
    except TypeError as e:
        error_msg = str(e)
        if "unsupported operand type(s) for *:" in error_msg:
            st.error("Error: Cannot multiply these data types. Please check your growth rates and margins data.")
        else:
            st.error(f"Type error: {error_msg}")
        logging.error(f"Type error in calculations: {error_msg}")
        logging.error(traceback.format_exc())
        return None
    except Exception as e:
        st.error(f"Error calculating metrics: {str(e)}")
        logging.error(f"Error in calculate_financial_metrics: {str(e)}")
        logging.error(traceback.format_exc())
        return None

def handle_dealer_page():
    """Handle the dealer page"""
    st.title("Dealer Information")
    
    log_interaction("Loaded dealer page")
    
    # Create tabs for creating/editing dealer and viewing dealer list
    tab1, tab2 = st.tabs(["Create/Edit Dealer", "Dealer List"])
    
    with tab1:
        # Call dealer form
        current_dealer = dealer_form()
        if current_dealer:
            show_dealer_summary(current_dealer)
    
    with tab2:
        st.subheader("Dealer List")
        
        # Refresh button
        if st.button("Refresh Dealer List"):
            log_interaction("Refreshed dealer list")
            # Clear cached data
            if "dealer_list" in st.session_state:
                del st.session_state.dealer_list
        
        # Get dealer list from database
        if "dealer_list" not in st.session_state:
            try:
                st.session_state.dealer_list = DealerRepository.get_all()
                log_interaction("Loaded dealer list from database", f"Count: {len(st.session_state.dealer_list)}")
            except Exception as e:
                st.error(f"Error loading dealers from database: {str(e)}")
                logging.error(f"Error loading dealers: {str(e)}")
                st.session_state.dealer_list = []
        
        dealers = st.session_state.dealer_list
        
        if not dealers:
            st.info("No dealers found in the database. Create a dealer first.")
        else:
            # Convert to DataFrame for display
            dealers_df = pd.DataFrame([
                {
                    'ID': d['id'],
                    'Name': d['name'],
                    'Location': d['location'],
                    'District': d.get('district', ''),
                    'PMG Sales': f"{d.get('pmg_sales', 0):,.0f} L/day",
                    'HSD Sales': f"{d.get('hsd_sales', 0):,.0f} L/day",
                    'Investment': f"PKR {d.get('initial_investment', 0):,.0f}",
                    'Created': d.get('created_at', '')
                } for d in dealers
            ])
            
            st.dataframe(dealers_df)
            
            # Dealer selection
            selected_dealer_id = st.selectbox(
                "Select a dealer to load",
                options=[d['id'] for d in dealers],
                format_func=lambda x: next((d['name'] + " - " + d['location'] for d in dealers if d['id'] == x), x)
            )
            
            if st.button("Load Selected Dealer"):
                try:
                    # Load dealer from database
                    dealer = DealerRepository.get_by_id(selected_dealer_id)
                    
                    if dealer:
                        # Save to session state
                        st.session_state.dealer = dealer
                        st.session_state.dealer_id = dealer.id
                        
                        # Success message
                        log_interaction("Loaded dealer from database", f"Dealer: {dealer.name}, ID: {dealer.id}")
                        st.success(f"Dealer '{dealer.name}' loaded successfully!")
                        
                        # Show dealer summary
                        show_dealer_summary(dealer)
                    else:
                        st.error(f"Dealer with ID {selected_dealer_id} not found.")
                except Exception as e:
                    st.error(f"Error loading dealer: {str(e)}")
                    logging.error(f"Error loading dealer: {str(e)}")
                    logging.error(traceback.format_exc())

def handle_scenario_page():
    """Handle the scenario page"""
    st.title("Scenario Information")
    
    log_interaction("Loaded scenario page")
    
    # Show dealer summary if available
    dealer = st.session_state.get("dealer")
    if dealer:
        show_dealer_summary(dealer)
    else:
        st.warning("Please create or select a dealer first!")
        st.stop()
    
    # Create tabs for creating/editing scenario, viewing scenario list, and calculating results
    tab1, tab2, tab3 = st.tabs(["Create/Edit Scenario", "Scenario List", "Calculate Results"])
    
    with tab1:
        # Call scenario form
        current_scenario = scenario_form()
        if current_scenario:
            show_scenario_summary(current_scenario)
    
    with tab2:
        st.subheader("Scenario List")
        
        # Refresh button
        if st.button("Refresh Scenario List"):
            log_interaction("Refreshed scenario list")
            # Clear cached data
            if "scenario_list" in st.session_state:
                del st.session_state.scenario_list
                
        # Get scenario list from database
        if "scenario_list" not in st.session_state:
            try:
                st.session_state.scenario_list = ScenarioRepository.get_all()
                log_interaction("Loaded scenario list from database", f"Count: {len(st.session_state.scenario_list)}")
            except Exception as e:
                st.error(f"Error loading scenarios from database: {str(e)}")
                logging.error(f"Error loading scenarios: {str(e)}")
                st.session_state.scenario_list = []
        
        scenarios = st.session_state.scenario_list
        
        if not scenarios:
            st.info("No scenarios found in the database. Create a scenario first.")
        else:
            # Convert to DataFrame for display
            scenarios_df = pd.DataFrame([
                {
                    'ID': s['id'],
                    'Name': s['name'],
                    'Description': s.get('description', '')[:50] + ('...' if s.get('description', '') and len(s.get('description', '')) > 50 else ''),
                    'Discount Rate': f"{s.get('discount_rate', 0) * 100:.1f}%",
                    'Inflation Rate': f"{s.get('inflation_rate', 0) * 100:.1f}%",
                    'Analysis Years': s.get('analysis_years', 0),
                    'Created': s.get('created_at', '')
                } for s in scenarios
            ])
            
            st.dataframe(scenarios_df)
            
            # Scenario selection
            selected_scenario_id = st.selectbox(
                "Select a scenario to load",
                options=[s['id'] for s in scenarios],
                format_func=lambda x: next((s['name'] for s in scenarios if s['id'] == x), x)
            )
            
            if st.button("Load Selected Scenario"):
                try:
                    # Load scenario from database
                    scenario = ScenarioRepository.get_by_id(selected_scenario_id)
                    
                    if scenario:
                        # Save to session state
                        st.session_state.scenario = scenario
                        st.session_state.scenario_id = scenario.id
                        
                        # Save growth rates and margins to session state
                        if hasattr(scenario, 'default_growth_rates') and scenario.default_growth_rates:
                            st.session_state.growth_rates = scenario.default_growth_rates
                        
                        if hasattr(scenario, 'default_margins') and scenario.default_margins:
                            st.session_state.margins = scenario.default_margins
                        
                        # Success message
                        log_interaction("Loaded scenario from database", f"Scenario: {scenario.name}, ID: {scenario.id}")
                        st.success(f"Scenario '{scenario.name}' loaded successfully!")
                        
                        # Show scenario summary
                        show_scenario_summary(scenario)
                    else:
                        st.error(f"Scenario with ID {selected_scenario_id} not found.")
                except Exception as e:
                    st.error(f"Error loading scenario: {str(e)}")
                    logging.error(f"Error loading scenario: {str(e)}")
                    logging.error(traceback.format_exc())
    
    # Dedicated Calculate Results tab
    with tab3:
        st.subheader("Calculate Financial Metrics")
        
        # Check if we have the necessary data
        scenario = st.session_state.get("scenario")
        
        if not scenario:
            st.warning("Please create or select a scenario first before calculating results.")
            st.info("You can create a scenario in the 'Create/Edit Scenario' tab or select an existing one from the 'Scenario List' tab.")
        else:
            # Show scenario summary
            show_scenario_summary(scenario)
            
            # Create a prominent calculate button
            st.markdown("### Ready to calculate financial metrics for this scenario?")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                calculate_button = st.button(
                    "🧮 Calculate Results", 
                    type="primary",
                    use_container_width=True,
                    key="calculate_results_main"
                )
            
            with col2:
                st.info("This will calculate NPV, IRR, Payback Period, and other financial metrics based on your scenario settings.")
                
            if calculate_button:
                log_interaction("Calculating results from dedicated Calculate Results tab", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
                with st.spinner("Calculating financial metrics..."):
                    # Calculate metrics
                    results = calculate_financial_metrics(dealer, scenario)
                    
                    if results:
                        st.session_state.results = results
                        st.success("✅ Calculation completed successfully!")
                        
                        # Create an attractive results display
                        st.markdown("## 📊 Financial Metrics Results")
                        
                        # Main metrics in a colorful card-like display
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            npv = results.get('npv', 0)
                            npv_color = "green" if npv > 0 else "red"
                            st.markdown(f"""
                            <div style="padding: 20px; border-radius: 10px; background-color: #f0f8ff; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                                <h3>Net Present Value</h3>
                                <p style="font-size: 24px; font-weight: bold; color: {npv_color};">PKR {npv:,.0f}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with col2:
                            irr = results.get('irr', 0) * 100
                            irr_color = "green" if irr > scenario.discount_rate * 100 else "orange" if irr > 0 else "red"
                            st.markdown(f"""
                            <div style="padding: 20px; border-radius: 10px; background-color: #f0fff0; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                                <h3>Internal Rate of Return</h3>
                                <p style="font-size: 24px; font-weight: bold; color: {irr_color};">{irr:.2f}%</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with col3:
                            payback = results.get('payback_period', 0)
                            payback_color = "green" if payback < 5 else "orange" if payback < 10 else "red"
                            st.markdown(f"""
                            <div style="padding: 20px; border-radius: 10px; background-color: #fff0f5; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                                <h3>Payback Period</h3>
                                <p style="font-size: 24px; font-weight: bold; color: {payback_color};">{payback:.2f} years</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Show a preview of cash flows
                        st.markdown("### Cash Flow Preview")
                        cash_flows = results.get('cash_flows', [])
                        if cash_flows:
                            # Display first 5 years of cash flows
                            preview_flows = cash_flows[:min(5, len(cash_flows))]
                            preview_df = pd.DataFrame({
                                'Year': [f"Year {i}" for i in range(len(preview_flows))],
                                'Cash Flow': preview_flows,
                                'Cash Flow (PKR)': [f"PKR {flow:,.0f}" for flow in preview_flows]
                            })
                            st.dataframe(preview_df)
                            
                            # Show link to full results
                            st.info("Visit the 'Results' page for complete details or the 'Detailed Analysis' page for visualizations.")
                            if st.button("Go to Results Page", key="goto_results"):
                                # Use st.experimental_set_query_params to switch page (if available)
                                # Otherwise suggest manual navigation
                                st.markdown("Please navigate to the 'Results' page from the sidebar")
                    else:
                        st.error("❌ Failed to calculate results. See error details above.")
    
    # Add banner at the bottom to highlight the Calculate Results tab
    if not st.session_state.get("results") and st.session_state.get("scenario"):
        st.markdown("---")
        st.markdown(
            """
            <div style="padding: 15px; background-color: #f0f8ff; border-radius: 10px; text-align: center;">
                <h3>Ready to see the financial results?</h3>
                <p>Go to the <b>Calculate Results</b> tab above to generate financial metrics for your scenario.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

def handle_results_page():
    """Handle the results page"""
    st.title("Results")
    
    log_interaction("Loaded results page")
    
    # Check if dealer and scenario are selected
    dealer = st.session_state.get("dealer")
    scenario = st.session_state.get("scenario")
    
    if not dealer:
        st.warning("Please create or select a dealer first!")
        st.stop()
    
    if not scenario:
        st.warning("Please create or select a scenario first!")
        st.stop()
    
    # Show summaries
    show_dealer_summary(dealer)
    show_scenario_summary(scenario)
    
    # Try to load saved results first
    results = st.session_state.get("results")
    
    if not results:
        # Check if we have saved results in the database
        try:
            saved_results = ResultsRepository.get_by_dealer_scenario(dealer.id, scenario.id)
            if saved_results:
                results = saved_results.results_data
                st.session_state.results = results
                st.success("Loaded saved results from database.")
                log_interaction("Loaded saved results", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
        except Exception as e:
            st.error(f"Error loading saved results: {str(e)}")
            logging.error(f"Error loading saved results: {str(e)}")
    
    # If still no results, show options to calculate or go back
    if not results:
        st.warning("No results available for this dealer and scenario combination.")
        
        # Option to calculate now
        if st.button("Calculate Results Now", type="primary"):
            log_interaction("Calculating results from results page", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
            with st.spinner("Calculating financial metrics..."):
                # Calculate metrics
                results = calculate_financial_metrics(dealer, scenario)
                
                if results:
                    st.session_state.results = results
                    st.success("✅ Calculation completed successfully!")
                    log_interaction("Calculation successful", f"NPV: {results.get('npv', 0)}, IRR: {results.get('irr', 0)}")
                    
                    # Save results to database
                    try:
                        ResultsRepository.save(dealer.id, scenario.id, results)
                        st.success("Results saved to database.")
                        log_interaction("Saved results to database", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
                    except Exception as e:
                        st.error(f"Error saving results: {str(e)}")
                        logging.error(f"Error saving results: {str(e)}")
                else:
                    st.error("❌ Failed to calculate results.")
                    st.stop()
        
        # Option to go to scenario page
        if st.button("Go to Scenario Page"):
            # Use st.experimental_set_query_params to switch page (if available)
            # Otherwise suggest manual navigation
            st.markdown("Please navigate to the 'Scenario' page from the sidebar")
            st.stop()
    
    # If we have results, display them
    if results:
        # Main results section
        st.header("Financial Metrics Summary")
        
        # Create an attractive metrics display
        col1, col2, col3 = st.columns(3)
        
        with col1:
            npv = results.get('npv', 0)
            npv_color = "green" if npv > 0 else "red"
            st.markdown(f"""
            <div style="padding: 20px; border-radius: 10px; background-color: #f0f8ff; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h3>Net Present Value</h3>
                <p style="font-size: 24px; font-weight: bold; color: {npv_color};">PKR {npv:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            irr = results.get('irr', 0) * 100
            irr_color = "green" if irr > scenario.discount_rate * 100 else "orange" if irr > 0 else "red"
            st.markdown(f"""
            <div style="padding: 20px; border-radius: 10px; background-color: #f0fff0; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h3>Internal Rate of Return</h3>
                <p style="font-size: 24px; font-weight: bold; color: {irr_color};">{irr:.2f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            payback = results.get('payback_period', 0)
            payback_color = "green" if payback < 5 else "orange" if payback < 10 else "red"
            st.markdown(f"""
            <div style="padding: 20px; border-radius: 10px; background-color: #fff0f5; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h3>Payback Period</h3>
                <p style="font-size: 24px; font-weight: bold; color: {payback_color};">{payback:.2f} years</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Investment summary
        st.subheader("Investment Summary")
        initial_investment = results.get('initial_investment', 0)
        st.metric("Initial Investment", f"PKR {initial_investment:,.0f}")
        
        # Key financial indicators
        st.subheader("Key Financial Indicators")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Discount Rate", f"{scenario.discount_rate * 100:.2f}%")
            st.metric("Analysis Period", f"{scenario.analysis_years} years")
            
        with col2:
            st.metric("Inflation Rate", f"{scenario.inflation_rate * 100:.2f}%")
            st.metric("MIRR", f"{results.get('mirr', 0) * 100:.2f}%")
        
        # Cash flow analysis
        st.header("Cash Flow Analysis")
        cash_flows = results.get('cash_flows', [])
        discounted_cash_flows = results.get('discounted_cash_flows', [])
        cumulative_cash_flows = results.get('cumulative_cash_flows', [])
        
        if cash_flows:
            # Create DataFrame with all cash flow data
            df = pd.DataFrame({
                'Year': [f"Year {i}" for i in range(len(cash_flows))],
                'Cash Flow': cash_flows,
                'Discounted Cash Flow': discounted_cash_flows,
                'Cumulative Cash Flow': cumulative_cash_flows,
                'Cash Flow (PKR)': [f"PKR {flow:,.0f}" for flow in cash_flows],
                'Discounted Cash Flow (PKR)': [f"PKR {flow:,.0f}" for flow in discounted_cash_flows],
                'Cumulative Cash Flow (PKR)': [f"PKR {flow:,.0f}" for flow in cumulative_cash_flows]
            })
            
            # Display the cash flow data
            st.dataframe(df)
            
            # Option to download cash flow data
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Cash Flow Data",
                data=csv,
                file_name=f"cash_flow_analysis_{dealer.name}_{scenario.name}.csv",
                mime="text/csv"
            )
            
            # Link to detailed analysis
            st.info("For visual representations of this data, please visit the 'Detailed Analysis' page.")
            if st.button("Go to Detailed Analysis"):
                # Use st.experimental_set_query_params to switch page (if available)
                # Otherwise suggest manual navigation
                st.markdown("Please navigate to the 'Detailed Analysis' page from the sidebar")
        else:
            st.warning("Cash flow data is not available.")
        
        # Sensitivity analysis if available
        sensitivity_results = results.get('sensitivity_analysis')
        if sensitivity_results:
            st.header("Sensitivity Analysis")
            st.write("The following table shows how changes in key parameters affect the NPV:")
            
            sensitivity_df = pd.DataFrame(sensitivity_results)
            st.dataframe(sensitivity_df)
        
        # Actions section
        st.header("Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Recalculate Results"):
                log_interaction("Recalculating results", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
                with st.spinner("Recalculating financial metrics..."):
                    # Calculate metrics
                    results = calculate_financial_metrics(dealer, scenario)
                    
                    if results:
                        st.session_state.results = results
                        st.success("✅ Recalculation completed successfully!")
                        
                        # Save results to database
                        try:
                            ResultsRepository.save(dealer.id, scenario.id, results)
                            st.success("Updated results saved to database.")
                            log_interaction("Updated saved results", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
                        except Exception as e:
                            st.error(f"Error saving updated results: {str(e)}")
                            logging.error(f"Error saving updated results: {str(e)}")
                    else:
                        st.error("❌ Failed to recalculate results.")
        
        with col2:
            # Generate report button
            if st.button("Generate Report"):
                log_interaction("Generating report", f"Dealer: {dealer.name}, Scenario: {scenario.name}")
                with st.spinner("Generating comprehensive report..."):
                    try:
                        # Generate PDF report
                        pdf_file = generate_pdf_report(dealer, scenario, results)
                        
                        # Provide download link
                        with open(pdf_file, "rb") as f:
                            pdf_bytes = f.read()
                        
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_bytes,
                            file_name=f"feasibility_report_{dealer.name}_{scenario.name}.pdf",
                            mime="application/pdf"
                        )
                        
                        # Success message
                        st.success("Report generated successfully! Click the download button above to save it.")
                    except Exception as e:
                        st.error(f"Error generating report: {str(e)}")
                        logging.error(f"Error generating report: {str(e)}")
                        logging.error(traceback.format_exc())

def handle_detailed_analysis_page():
    """Handle the detailed analysis page"""
    log_interaction("Viewed detailed analysis page")
    
    # Display current dealer and scenario summary if available
    if st.session_state.get("dealer") is not None:
        show_dealer_summary(st.session_state.dealer)
    
    if st.session_state.get("scenario") is not None:
        show_scenario_summary(st.session_state.scenario)
    
    # Check if results are available
    if not st.session_state.get("results"):
        st.warning("Please calculate results first.")
        return None
    
    # Display detailed analysis
    results = st.session_state.results
    yearly_data = results.get('yearly_data', {})
    
    if not yearly_data:
        st.warning("No detailed data available.")
        return None
    
    # Create yearly data dataframe
    years = list(range(len(results.get('cash_flows', []))))
    
    yearly_df = pd.DataFrame({
        'Year': years,
        'PMG Sales (Liters)': [yearly_data.get('pmg_sales', {}).get(year, 0) for year in years],
        'HSD Sales (Liters)': [yearly_data.get('hsd_sales', {}).get(year, 0) for year in years],
        'HOBC Sales (Liters)': [yearly_data.get('hobc_sales', {}).get(year, 0) for year in years],
        'Lube Sales (Liters)': [yearly_data.get('lube_sales', {}).get(year, 0) for year in years],
        'PMG Revenue': [yearly_data.get('pmg_revenue', {}).get(year, 0) for year in years],
        'HSD Revenue': [yearly_data.get('hsd_revenue', {}).get(year, 0) for year in years],
        'HOBC Revenue': [yearly_data.get('hobc_revenue', {}).get(year, 0) for year in years],
        'Lube Revenue': [yearly_data.get('lube_revenue', {}).get(year, 0) for year in years],
        'Total Revenue': [yearly_data.get('total_revenue', {}).get(year, 0) for year in years],
        'Operating Costs': [yearly_data.get('operating_costs', {}).get(year, 0) for year in years],
        'Insurance': [yearly_data.get('insurance', {}).get(year, 0) for year in years],
        'Net Cash Flow': results.get('cash_flows', [0] * len(years))
    })
    
    # Display the dataframe
    st.dataframe(yearly_df)
    
    # Download button
    csv = yearly_df.to_csv(index=False)
    st.download_button(
        label="Download Detailed Analysis (CSV)",
        data=csv,
        file_name=f"detailed_analysis_{st.session_state.dealer.name}_{st.session_state.scenario.name}.csv",
        mime="text/csv"
    )
    
    # Choose metrics to visualize
    st.subheader("Visualize Metrics")
    metrics = st.multiselect(
        "Select metrics to visualize",
        options=[col for col in yearly_df.columns if col != 'Year'],
        default=['PMG Sales (Liters)', 'HSD Sales (Liters)', 'Net Cash Flow']
    )
    
    if metrics:
        st.line_chart(yearly_df.set_index('Year')[metrics])

def handle_comparison_page():
    """Handle the comparison page"""
    log_interaction("Viewed comparison page")
    
    st.title("Scenario Comparison")
    
    # Display current dealer if available
    dealer = st.session_state.get("dealer")
    if dealer is None:
        st.warning("Please create or select a dealer first before comparing scenarios.")
        return
    
    show_dealer_summary(dealer)
    
    # Get all available scenarios
    try:
        all_scenarios = ScenarioRepository.get_all()
        if not all_scenarios:
            st.warning("No scenarios found in the database. Please create scenarios first.")
            return
    except Exception as e:
        st.error(f"Error loading scenarios: {str(e)}")
        logging.error(f"Error loading scenarios: {str(e)}")
        return
    
    # Create a multiselect for scenarios
    scenario_options = {s['id']: f"{s['name']} ({s.get('description', '')[:20]}...)" for s in all_scenarios}
    selected_scenario_ids = st.multiselect(
        "Select scenarios to compare (up to 5)",
        options=list(scenario_options.keys()),
        format_func=lambda x: scenario_options.get(x, x),
        help="Choose up to 5 scenarios to compare side by side."
    )
    
    if not selected_scenario_ids:
        st.info("Please select at least one scenario to analyze.")
        return
    
    if len(selected_scenario_ids) > 5:
        st.warning("Too many scenarios selected. Please limit your selection to 5 scenarios.")
        return
    
    # Show comparison control panel
    st.subheader("Comparison Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        metrics_to_compare = st.multiselect(
            "Metrics to compare",
            options=["NPV", "IRR", "Payback Period", "Total Revenue", "PMG Revenue", 
                    "HSD Revenue", "HOBC Revenue", "Lube Revenue", "Sales Volume"],
            default=["NPV", "IRR", "Payback Period"],
            help="Select financial metrics to compare across scenarios."
        )
    
    with col2:
        show_detailed = st.checkbox("Show detailed charts", value=True,
                                   help="Display detailed charts for each metric.")
    
    # Calculate or retrieve results for each scenario
    st.subheader("Calculating Results")
    
    # Button to trigger calculation
    calculate_button = st.button("Calculate and Compare Scenarios", type="primary")
    
    if calculate_button:
        comparison_results = {}
        scenario_objects = {}
        failed_scenarios = []
        
        with st.spinner("Calculating results for selected scenarios..."):
            for scenario_id in selected_scenario_ids:
                # Get scenario
                try:
                    scenario = ScenarioRepository.get_by_id(scenario_id)
                    if not scenario:
                        st.warning(f"Scenario with ID {scenario_id} not found.")
                        continue
                    
                    scenario_objects[scenario_id] = scenario
                    
                    # Check if results already exist
                    existing_results = None
                    try:
                        existing_results = ResultsRepository.get_result(dealer.id, scenario_id)
                    except Exception as e:
                        logging.warning(f"Could not retrieve saved results: {str(e)}")
                    
                    if existing_results:
                        # Use existing results
                        comparison_results[scenario_id] = existing_results
                        st.success(f"✅ Loaded saved results for '{scenario.name}'")
                    else:
                        # Calculate new results
                        results = calculate_financial_metrics(dealer, scenario)
                        if results:
                            comparison_results[scenario_id] = results
                            st.success(f"✅ Calculated results for '{scenario.name}'")
                        else:
                            failed_scenarios.append(scenario.name)
                except Exception as e:
                    st.error(f"Error processing scenario {scenario_id}: {str(e)}")
                    logging.error(f"Error in comparison calculation: {str(e)}")
                    logging.error(traceback.format_exc())
                    failed_scenarios.append(scenario_id)
        
        if failed_scenarios:
            st.error(f"Failed to calculate results for scenarios: {', '.join(failed_scenarios)}")
        
        if comparison_results:
            st.session_state.comparison_results = comparison_results
            st.session_state.comparison_scenarios = scenario_objects
            st.success("Comparison calculation completed! View the results below.")
            # Force a refresh to show results
            st.rerun()
    
    # Display comparison results if available
    comparison_results = st.session_state.get("comparison_results", {})
    scenario_objects = st.session_state.get("comparison_scenarios", {})
    
    if comparison_results:
        st.header("Comparison Results")
        
        # Create a summary table first
        st.subheader("Financial Metrics Summary")
        
        summary_data = []
        for scenario_id, results in comparison_results.items():
            scenario = scenario_objects.get(scenario_id)
            if scenario:
                summary_data.append({
                    "Scenario": scenario.name,
                    "NPV (PKR)": f"{results.get('npv', 0):,.0f}",
                    "IRR (%)": f"{results.get('irr', 0) * 100:.2f}%",
                    "Payback (Years)": f"{results.get('payback_period', 0):.2f}",
                    "Analysis Years": scenario.analysis_years,
                    "Discount Rate (%)": f"{scenario.discount_rate * 100:.1f}%"
                })
        
        if summary_data:
            st.dataframe(pd.DataFrame(summary_data).set_index("Scenario"))
        
        # Calculate numeric data for charts
        chart_data = []
        for scenario_id, results in comparison_results.items():
            scenario = scenario_objects.get(scenario_id)
            if scenario:
                chart_data.append({
                    "Scenario": scenario.name,
                    "NPV": float(results.get('npv', 0)),
                    "IRR": float(results.get('irr', 0) * 100),
                    "Payback Period": float(results.get('payback_period', 0)),
                    "ID": scenario_id
                })
        
        chart_df = pd.DataFrame(chart_data)
        
        if "NPV" in metrics_to_compare and not chart_df.empty:
            st.subheader("Net Present Value (NPV) Comparison")
            # Sort by NPV descending
            npv_df = chart_df.sort_values("NPV", ascending=False)
            
            # NPV bar chart
            npv_fig = px.bar(
                npv_df,
                x="Scenario", 
                y="NPV",
                title="NPV Comparison",
                labels={"NPV": "NPV (PKR)", "Scenario": "Scenario Name"}
            )
            st.plotly_chart(npv_fig)
        
        if "IRR" in metrics_to_compare and not chart_df.empty:
            st.subheader("Internal Rate of Return (IRR) Comparison")
            # Sort by IRR descending
            irr_df = chart_df.sort_values("IRR", ascending=False)
            
            # IRR bar chart
            irr_fig = px.bar(
                irr_df,
                x="Scenario", 
                y="IRR",
                title="IRR Comparison",
                labels={"IRR": "IRR (%)", "Scenario": "Scenario Name"}
            )
            st.plotly_chart(irr_fig)
        
        if "Payback Period" in metrics_to_compare and not chart_df.empty:
            st.subheader("Payback Period Comparison")
            # Sort by Payback Period ascending (lower is better)
            payback_df = chart_df.sort_values("Payback Period", ascending=True)
            
            # Payback Period bar chart
            payback_fig = px.bar(
                payback_df,
                x="Scenario", 
                y="Payback Period",
                title="Payback Period Comparison",
                labels={"Payback Period": "Years", "Scenario": "Scenario Name"}
            )
            st.plotly_chart(payback_fig)
        
        # Cash flow comparison if detailed charts are enabled
        if show_detailed:
            st.subheader("Cash Flow Comparison")
            
            # Get the maximum analysis years to normalize data
            max_years = max([scenario_objects[scenario_id].analysis_years for scenario_id in comparison_results.keys()])
            
            # Prepare cash flow data
            cf_data = []
            for scenario_id, results in comparison_results.items():
                scenario = scenario_objects.get(scenario_id)
                if scenario and "cash_flows" in results:
                    cash_flows = results["cash_flows"]
                    for year, cf in enumerate(cash_flows[:max_years]):
                        cf_data.append({
                            "Scenario": scenario.name,
                            "Year": f"Year {year}",
                            "Year_Num": year,
                            "Cash Flow": cf
                        })
            
            if cf_data:
                cf_df = pd.DataFrame(cf_data)
                
                # Cash flow line chart
                cf_fig = px.line(
                    cf_df,
                    x="Year_Num", 
                    y="Cash Flow",
                    color="Scenario",
                    title="Cash Flow Comparison",
                    labels={"Cash Flow": "Cash Flow (PKR)", "Year_Num": "Year"}
                )
                st.plotly_chart(cf_fig)
            
            # Revenue comparison
            if any(metric in ["Total Revenue", "PMG Revenue", "HSD Revenue", 
                             "HOBC Revenue", "Lube Revenue"] for metric in metrics_to_compare):
                st.subheader("Revenue Comparison (Year 5)")
                
                rev_data = []
                for scenario_id, results in comparison_results.items():
                    scenario = scenario_objects.get(scenario_id)
                    if scenario and "yearly_data" in results:
                        yearly_data = results["yearly_data"]
                        # Use year 5 or the last available year for comparison
                        year_idx = min(5, len(next(iter(yearly_data.values()), [])) - 1)
                        
                        rev_data.append({
                            "Scenario": scenario.name,
                            "Total Revenue": yearly_data.get("total_revenue", {}).get(year_idx, 0),
                            "PMG Revenue": yearly_data.get("pmg_revenue", {}).get(year_idx, 0),
                            "HSD Revenue": yearly_data.get("hsd_revenue", {}).get(year_idx, 0),
                            "HOBC Revenue": yearly_data.get("hobc_revenue", {}).get(year_idx, 0),
                            "Lube Revenue": yearly_data.get("lube_revenue", {}).get(year_idx, 0)
                        })
                
                if rev_data:
                    rev_df = pd.DataFrame(rev_data).set_index("Scenario")
                    
                    # Format as PKR
                    for col in rev_df.columns:
                        rev_df[f"{col} (PKR)"] = rev_df[col].apply(lambda x: f"PKR {x:,.0f}")
                    
                    # Show data table
                    st.dataframe(rev_df[[col for col in rev_df.columns if "PKR" in col]])
                    
                    # Create a revenue comparison chart
                    if "Total Revenue" in metrics_to_compare:
                        rev_fig = px.bar(
                            rev_df.reset_index(),
                            x="Scenario",
                            y="Total Revenue",
                            title="Total Revenue Comparison (Year 5)",
                            labels={"Total Revenue": "Revenue (PKR)"}
                        )
                        st.plotly_chart(rev_fig)
            
            # Sales Volume comparison
            if "Sales Volume" in metrics_to_compare:
                st.subheader("Sales Volume Comparison (Year 5)")
                
                sales_data = []
                for scenario_id, results in comparison_results.items():
                    scenario = scenario_objects.get(scenario_id)
                    if scenario and "yearly_data" in results:
                        yearly_data = results["yearly_data"]
                        # Use year 5 or the last available year for comparison
                        year_idx = min(5, len(next(iter(yearly_data.values()), [])) - 1)
                        
                        sales_data.append({
                            "Scenario": scenario.name,
                            "PMG Sales": yearly_data.get("pmg_sales", {}).get(year_idx, 0),
                            "HSD Sales": yearly_data.get("hsd_sales", {}).get(year_idx, 0),
                            "HOBC Sales": yearly_data.get("hobc_sales", {}).get(year_idx, 0),
                            "Lube Sales": yearly_data.get("lube_sales", {}).get(year_idx, 0)
                        })
                
                if sales_data:
                    sales_df = pd.DataFrame(sales_data)
                    
                    # Reshape for grouped bar chart
                    sales_melted = pd.melt(
                        sales_df, 
                        id_vars=["Scenario"],
                        value_vars=["PMG Sales", "HSD Sales", "HOBC Sales", "Lube Sales"],
                        var_name="Product", 
                        value_name="Volume"
                    )
                    
                    # Create a sales volume comparison chart
                    sales_fig = px.bar(
                        sales_melted,
                        x="Scenario",
                        y="Volume",
                        color="Product",
                        barmode="group",
                        title="Sales Volume Comparison by Product (Year 5)",
                        labels={"Volume": "Volume (Liters)"}
                    )
                    st.plotly_chart(sales_fig)
        
        # Add option to download comparison data
        st.subheader("Export Comparison Results")
        
        # Prepare comparison data for export
        export_data = {
            "summary": summary_data,
            "scenarios": {scenario.name: scenario.to_dict() for scenario in scenario_objects.values()},
            "results": {scenario_objects[scenario_id].name: results for scenario_id, results in comparison_results.items()},
            "dealer": dealer.to_dict() if hasattr(dealer, "to_dict") else {},
            "comparison_date": datetime.now().isoformat()
        }
        
        # Convert to JSON for download
        comparison_json = json.dumps(export_data, indent=2)
        
        # Create a download button
        st.download_button(
            label="Download Comparison Data",
            data=comparison_json,
            file_name=f"scenario_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    else:
        if calculate_button:
            st.warning("No comparison results available. Please check the errors above.")
        else:
            st.info("Select scenarios and click 'Calculate and Compare Scenarios' to view comparison results.")

def handle_reports_page():
    """Handle the reports page"""
    st.title("Reports")
    
    # Check if dealer and scenario are selected
    dealer = st.session_state.get("dealer")
    scenario = st.session_state.get("scenario")
    
    if not dealer or not scenario:
        st.warning("Please select both a dealer and a scenario first!")
        return
    
    # Show summaries
    show_dealer_summary(dealer)
    show_scenario_summary(scenario)
    
    # Check if we have results
    results = st.session_state.get("results")
    
    if not results:
        st.warning("Please calculate results first!")
        return
    
    # Report options
    st.subheader("Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Generate PDF Report"):
            try:
                with st.spinner("Generating PDF report..."):
                    pdf_buffer = generate_pdf_report(dealer, scenario, results)
                
                # Offer the PDF for download
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_buffer,
                    file_name=f"dealer_feasibility_report_{dealer.name.replace(' ', '_')}_{scenario.name.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
                st.success("PDF report generated successfully!")
            except Exception as e:
                st.error(f"Error generating PDF report: {str(e)}")
                logging.error(f"Error generating PDF report: {str(e)}")
    
    with col2:
        if st.button("Generate Excel Report"):
            try:
                with st.spinner("Generating Excel report..."):
                    excel_buffer = generate_excel_report(dealer, scenario, results)
                
                # Offer the Excel file for download
                st.download_button(
                    label="Download Excel Report",
                    data=excel_buffer,
                    file_name=f"dealer_feasibility_report_{dealer.name}_{scenario.name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("Excel report generated successfully!")
            except Exception as e:
                st.error(f"Error generating Excel report: {str(e)}")
                logging.error(f"Error generating Excel report: {str(e)}")
    
    with col3:
        if st.button("Generate Data Backup"):
            try:
                # Create a comprehensive data backup with all information
                backup_data = {
                    "dealer": dealer.to_dict() if hasattr(dealer, "to_dict") else {},
                    "scenario": scenario.to_dict() if hasattr(scenario, "to_dict") else {},
                    "results": results
                }
                
                # Convert to JSON
                backup_json = json.dumps(backup_data, indent=2)
                
                # Offer JSON file for download
                st.download_button(
                    label="Download Data Backup",
                    data=backup_json,
                    file_name=f"dealer_feasibility_backup_{dealer.name}_{scenario.name}.json",
                    mime="application/json"
                )
                st.success("Data backup generated successfully!")
            except Exception as e:
                st.error(f"Error generating data backup: {str(e)}")
                logging.error(f"Error generating data backup: {str(e)}")
    
    # Report preview
    st.subheader("Report Preview")
    
    # Key metrics
    st.write("### Key Financial Metrics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Net Present Value (NPV)", f"PKR {results.get('npv', 0):,.0f}")
    with col2:
        st.metric("Internal Rate of Return (IRR)", f"{results.get('irr', 0) * 100:.2f}%")
    with col3:
        st.metric("Payback Period", f"{results.get('payback_period', 0):.2f} years")
    
    # Cash flow chart
    st.write("### Cash Flow Analysis")
    
    cash_flows = results.get('cash_flows', [])
    if cash_flows:
        cf_df = pd.DataFrame({
            'Year': [f"Year {i}" for i in range(len(cash_flows))],
            'Cash Flow': cash_flows
        })
        
        # Format as PKR
        cf_df['Cash Flow (PKR)'] = cf_df['Cash Flow'].apply(lambda x: f"PKR {x:,.0f}")
        
        # Display cash flows table
        st.dataframe(cf_df[['Year', 'Cash Flow (PKR)']])
        
        # Plot cash flows
        fig = px.bar(
            cf_df, 
            x='Year', 
            y='Cash Flow',
            title='Yearly Cash Flows',
            labels={'Cash Flow': 'Cash Flow (PKR)'}
        )
        st.plotly_chart(fig)
    
    # Sales and revenue data
    st.write("### Sales and Revenue Projection")
    
    yearly_data = results.get('yearly_data', {})
    if yearly_data:
        years = list(range(len(next(iter(yearly_data.values())))))
        
        # Create sales DataFrame
        sales_data = {'Year': [f"Year {i}" for i in years]}
        for product in ['pmg', 'hsd', 'hobc', 'lube']:
            if f"{product}_sales" in yearly_data:
                sales_data[f"{product.upper()} Sales (L)"] = [
                    yearly_data[f"{product}_sales"].get(i, 0) for i in years
                ]
        
        sales_df = pd.DataFrame(sales_data)
        st.dataframe(sales_df)
        
        # Plot sales
        st.write("#### Sales Volume Projection")
        sales_fig = px.line(
            sales_df,
            x='Year',
            y=[col for col in sales_df.columns if 'Sales' in col],
            title='Yearly Sales Volume by Product',
            labels={'value': 'Sales Volume (L)', 'variable': 'Product'}
        )
        st.plotly_chart(sales_fig)
        
        # Revenue data
        revenue_data = {'Year': [f"Year {i}" for i in years]}
        for product in ['pmg', 'hsd', 'hobc', 'lube']:
            if f"{product}_revenue" in yearly_data:
                revenue_data[f"{product.upper()} Revenue"] = [
                    yearly_data[f"{product}_revenue"].get(i, 0) for i in years
                ]
        
        if 'total_revenue' in yearly_data:
            revenue_data['Total Revenue'] = [
                yearly_data['total_revenue'].get(i, 0) for i in years
            ]
        
        revenue_df = pd.DataFrame(revenue_data)
        
        # Plot revenue
        st.write("#### Revenue Projection")
        revenue_fig = px.line(
            revenue_df,
            x='Year',
            y=[col for col in revenue_df.columns if 'Revenue' in col],
            title='Yearly Revenue by Product',
            labels={'value': 'Revenue (PKR)', 'variable': 'Product'}
        )
        st.plotly_chart(revenue_fig)

def generate_pdf_report(dealer, scenario, results):
    """Generate a PDF report with dealer feasibility analysis results"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from io import BytesIO
        import matplotlib.pyplot as plt
        
        # Create BytesIO buffer
        buffer = BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading2_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Title
        elements.append(Paragraph(f"Dealer Feasibility Analysis Report", title_style))
        elements.append(Spacer(1, 12))
        
        # Date
        elements.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d')}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Dealer Information
        elements.append(Paragraph("Dealer Information", heading2_style))
        elements.append(Spacer(1, 6))
        
        dealer_data = [
            ["Name", dealer.name],
            ["Location", dealer.location],
            ["PMG Sales", f"{dealer.pmg_sales:,.0f} L/day"],
            ["HSD Sales", f"{dealer.hsd_sales:,.0f} L/day"],
            ["Initial Investment", f"PKR {dealer.initial_investment:,.0f}"]
        ]
        
        # Create table
        dealer_table = Table(dealer_data, colWidths=[2*inch, 3*inch])
        dealer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(dealer_table)
        elements.append(Spacer(1, 12))
        
        # Scenario Information
        elements.append(Paragraph("Scenario Information", heading2_style))
        elements.append(Spacer(1, 6))
        
        scenario_data = [
            ["Name", scenario.name],
            ["Description", scenario.description],
            ["Discount Rate", f"{scenario.discount_rate*100:.1f}%"],
            ["Inflation Rate", f"{scenario.inflation_rate*100:.1f}%"],
            ["Tax Rate", f"{scenario.tax_rate*100:.1f}%"],
            ["Analysis Years", str(scenario.analysis_years)]
        ]
        
        # Create table
        scenario_table = Table(scenario_data, colWidths=[2*inch, 3*inch])
        scenario_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(scenario_table)
        elements.append(Spacer(1, 12))
        
        # Financial Results
        elements.append(Paragraph("Financial Results", heading2_style))
        elements.append(Spacer(1, 6))
        
        results_data = [
            ["Metric", "Value"],
            ["Net Present Value (NPV)", f"PKR {results.get('npv', 0):,.0f}"],
            ["Internal Rate of Return (IRR)", f"{results.get('irr', 0)*100:.2f}%"],
            ["Payback Period", f"{results.get('payback_period', 0):.2f} years"]
        ]
        
        # Create table
        results_table = Table(results_data, colWidths=[2.5*inch, 2.5*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(results_table)
        elements.append(Spacer(1, 12))
        
        # Cash Flow Chart
        elements.append(Paragraph("Cash Flow Analysis", heading2_style))
        elements.append(Spacer(1, 6))
        
        cash_flows = results.get('cash_flows', [])
        if cash_flows:
            # Create matplotlib figure
            plt.figure(figsize=(6, 4))
            years = list(range(len(cash_flows)))
            plt.bar(years, cash_flows)
            plt.title('Yearly Cash Flows')
            plt.xlabel('Year')
            plt.ylabel('Cash Flow (PKR)')
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Save the figure to a BytesIO object
            img_buffer = BytesIO()
            plt.tight_layout()
            plt.savefig(img_buffer, format='png')
            img_buffer.seek(0)
            plt.close()
            
            # Add image to PDF
            img = Image(img_buffer, width=6*inch, height=4*inch)
            elements.append(img)
        
        # Generate PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        logging.error(f"Error generating PDF report: {str(e)}")
        raise

def generate_excel_report(dealer, scenario, results):
    """Generate an Excel report with dealer feasibility analysis results"""
    try:
        import xlsxwriter
        from io import BytesIO
        
        # Create BytesIO buffer
        output = BytesIO()
        
        # Create workbook and add worksheets
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Summary worksheet
            summary_data = {
                'Metric': ['Dealer Name', 'Location', 'Scenario Name', 'NPV', 'IRR', 'Payback Period'],
                'Value': [
                    dealer.name,
                    dealer.location,
                    scenario.name,
                    f"PKR {results.get('npv', 0):,.0f}",
                    f"{results.get('irr', 0)*100:.2f}%",
                    f"{results.get('payback_period', 0):.2f} years"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Format Summary sheet
            summary_sheet = writer.sheets['Summary']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#CCCCCC', 'border': 1})
            for col_num, value in enumerate(summary_df.columns.values):
                summary_sheet.write(0, col_num, value, header_format)
            
            # Dealer Details worksheet
            dealer_data = {
                'Attribute': [
                    'Name', 'Location', 'PMG Sales', 'HSD Sales', 'HOBC Sales', 'Lube Sales',
                    'Initial Investment', 'Operating Costs'
                ],
                'Value': [
                    dealer.name,
                    dealer.location,
                    f"{dealer.pmg_sales:,.0f} L/day",
                    f"{dealer.hsd_sales:,.0f} L/day",
                    f"{dealer.hobc_sales:,.0f} L/day",
                    f"{dealer.lube_sales:,.0f} L/day",
                    f"PKR {dealer.initial_investment:,.0f}",
                    f"PKR {dealer.operating_costs:,.0f}/month"
                ]
            }
            dealer_df = pd.DataFrame(dealer_data)
            dealer_df.to_excel(writer, sheet_name='Dealer Details', index=False)
            
            # Format Dealer Details sheet
            dealer_sheet = writer.sheets['Dealer Details']
            for col_num, value in enumerate(dealer_df.columns.values):
                dealer_sheet.write(0, col_num, value, header_format)
            
            # Investment Items
            if hasattr(dealer, 'investment_items') and dealer.investment_items:
                items_df = pd.DataFrame(dealer.investment_items)
                items_df.to_excel(writer, sheet_name='Investment Items', index=False)
                
                # Format Investment Items sheet
                items_sheet = writer.sheets['Investment Items']
                for col_num, value in enumerate(items_df.columns.values):
                    items_sheet.write(0, col_num, value, header_format)
            
            # Cash Flows worksheet
            cash_flows = results.get('cash_flows', [])
            if cash_flows:
                cf_data = {
                    'Year': [f"Year {i}" for i in range(len(cash_flows))],
                    'Cash Flow': cash_flows,
                    'Cash Flow (PKR)': [f"PKR {flow:,.0f}" for flow in cash_flows]
                }
                cf_df = pd.DataFrame(cf_data)
                cf_df.to_excel(writer, sheet_name='Cash Flows', index=False)
                
                # Format Cash Flows sheet
                cf_sheet = writer.sheets['Cash Flows']
                for col_num, value in enumerate(cf_df.columns.values):
                    cf_sheet.write(0, col_num, value, header_format)
            
            # Yearly Data worksheets
            yearly_data = results.get('yearly_data', {})
            if yearly_data:
                years = list(range(len(next(iter(yearly_data.values())))))
                
                # Sales Data
                sales_data = {'Year': [f"Year {i}" for i in years]}
                for product in ['pmg', 'hsd', 'hobc', 'lube']:
                    if f"{product}_sales" in yearly_data:
                        sales_data[f"{product.upper()} Sales (L)"] = [
                            yearly_data[f"{product}_sales"].get(i, 0) for i in years
                        ]
                
                sales_df = pd.DataFrame(sales_data)
                sales_df.to_excel(writer, sheet_name='Sales Projection', index=False)
                
                # Format Sales Projection sheet
                sales_sheet = writer.sheets['Sales Projection']
                for col_num, value in enumerate(sales_df.columns.values):
                    sales_sheet.write(0, col_num, value, header_format)
                
                # Revenue Data
                revenue_data = {'Year': [f"Year {i}" for i in years]}
                for product in ['pmg', 'hsd', 'hobc', 'lube']:
                    if f"{product}_revenue" in yearly_data:
                        revenue_data[f"{product.upper()} Revenue"] = [
                            yearly_data[f"{product}_revenue"].get(i, 0) for i in years
                        ]
                    revenue_data[f"{product.upper()} Revenue (PKR)"] = [
                        f"PKR {yearly_data[f'{product}_revenue'].get(i, 0):,.0f}" for i in years
                    ]
                
                if 'total_revenue' in yearly_data:
                    revenue_data['Total Revenue'] = [
                        yearly_data['total_revenue'].get(i, 0) for i in years
                    ]
                    revenue_data['Total Revenue (PKR)'] = [
                        f"PKR {yearly_data['total_revenue'].get(i, 0):,.0f}" for i in years
                    ]
                
                revenue_df = pd.DataFrame(revenue_data)
                revenue_df.to_excel(writer, sheet_name='Revenue Projection', index=False)
                
                # Format Revenue Projection sheet
                revenue_sheet = writer.sheets['Revenue Projection']
                for col_num, value in enumerate(revenue_df.columns.values):
                    revenue_sheet.write(0, col_num, value, header_format)
        
        # Get the value of the BytesIO buffer
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        logging.error(f"Error generating Excel report: {str(e)}")
        raise

@handle_exceptions
def handle_database_admin_page():
    """Handle the database admin page for monitoring and managing the database."""
    st.title("Database Administration")
    st.write("Monitor and manage the Supabase database connection and tables.")
    
    tabs = st.tabs(["Connection Status", "Table Statistics", "Database Management"])
    
    # Connection Status Tab
    with tabs[0]:
        st.header("Connection Status")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("Test the connection to the Supabase database and check table status.")
        
        with col2:
            test_button = st.button("Test Connection", key="test_connection")
        
        if test_button or 'db_status' in st.session_state:
            with st.spinner("Testing connection..."):
                if test_button or 'db_status' not in st.session_state:
                    status = test_supabase_connection()
                    st.session_state.db_status = status
                else:
                    status = st.session_state.db_status
                
                # Display connection status
                if status['connection']:
                    st.success("✅ Successfully connected to Supabase!")
                else:
                    st.error("❌ Failed to connect to Supabase")
                    if status['error']:
                        st.error(f"Error: {status['error']}")
                    st.stop()
                
                # Display table status
                st.subheader("Table Status")
                
                table_data = []
                for table, info in status['tables'].items():
                    exists = "✅" if info.get('exists', False) else "❌"
                    count = info.get('count', 0) if info.get('exists', False) else "N/A"
                    error = info.get('error', 'None')
                    table_data.append([table, exists, count, error])
                
                st.table({
                    "Table Name": [row[0] for row in table_data],
                    "Exists": [row[1] for row in table_data],
                    "Row Count": [row[2] for row in table_data],
                    "Error": [row[3] for row in table_data]
                })
    
    # Table Statistics Tab
    with tabs[1]:
        st.header("Table Statistics")
        
        refresh_stats = st.button("Refresh Statistics", key="refresh_stats")
        
        # Only proceed if we've already tested the connection
        if 'db_status' not in st.session_state or not st.session_state.db_status['connection']:
            st.warning("Please test the connection first in the Connection Status tab")
            st.stop()
        
        if refresh_stats or 'table_stats' in st.session_state:
            with st.spinner("Fetching table statistics..."):
                if refresh_stats or 'table_stats' not in st.session_state:
                    # Initialize stats dictionary
                    stats = {}
                    
                    try:
                        supabase = get_supabase_client()
                        
                        # Get dealers count and sample
                        dealers_response = supabase.from_('dealers').select('*').limit(3).execute()
                        stats['dealers'] = {
                            'count': len(dealers_response.data),
                            'sample': dealers_response.data
                        }
                        
                        # Get scenarios count and sample
                        scenarios_response = supabase.from_('scenarios').select('*').limit(3).execute()
                        stats['scenarios'] = {
                            'count': len(scenarios_response.data),
                            'sample': scenarios_response.data
                        }
                        
                        st.session_state.table_stats = stats
                    except Exception as e:
                        st.error(f"Error fetching statistics: {str(e)}")
                        st.stop()
                else:
                    stats = st.session_state.table_stats
                
                # Display dealer stats
                st.subheader("Dealers")
                st.write(f"Sample dealers (up to 3):")
                if stats['dealers']['sample']:
                    st.json(stats['dealers']['sample'])
                else:
                    st.info("No dealers found in the database")
                
                # Display scenario stats
                st.subheader("Scenarios")
                st.write(f"Sample scenarios (up to 3):")
                if stats['scenarios']['sample']:
                    st.json(stats['scenarios']['sample'])
                else:
                    st.info("No scenarios found in the database")
    
    # Database Management Tab
    with tabs[2]:
        st.header("Database Management")
        st.warning("⚠️ Operations in this section can modify database data. Use with caution.")
        
        # Only proceed if we've already tested the connection
        if 'db_status' not in st.session_state or not st.session_state.db_status['connection']:
            st.warning("Please test the connection first in the Connection Status tab")
            st.stop()
        
        # Delete test data
        st.subheader("Delete Test Data")
        test_data_col1, test_data_col2 = st.columns([3, 1])
        
        with test_data_col1:
            st.write("Delete all records with 'Test' in their name. This operation cannot be undone.")
        
        with test_data_col2:
            delete_test = st.button("Delete Test Data", key="delete_test_data")
        
        if delete_test:
            try:
                with st.spinner("Deleting test data..."):
                    supabase = get_supabase_client()
                    
                    # Delete test dealers
                    dealers_response = supabase.from_('dealers').delete().ilike('name', '%Test%').execute()
                    
                    # Delete test scenarios
                    scenarios_response = supabase.from_('scenarios').delete().ilike('name', '%Test%').execute()
                    
                    st.success(f"Successfully deleted test data")
                    
                    # Reset stats
                    if 'table_stats' in st.session_state:
                        del st.session_state.table_stats
            except Exception as e:
                st.error(f"Error deleting test data: {str(e)}")
        
        # Check schema version
        st.subheader("Schema Version")
        schema_col1, schema_col2 = st.columns([3, 1])
        
        with schema_col1:
            st.write("Check the current database schema version.")
        
        with schema_col2:
            check_schema = st.button("Check Version", key="check_schema")
        
        if check_schema:
            try:
                with st.spinner("Checking schema version..."):
                    supabase = get_supabase_client()
                    
                    # Get schema version
                    response = supabase.from_('schema_version').select('*').order('id.desc').limit(1).execute()
                    
                    if response.data:
                        version_info = response.data[0]
                        st.info(f"Schema Version: {version_info['version']}")
                        st.write(f"Applied at: {version_info['applied_at']}")
                        st.write(f"Description: {version_info['description']}")
                    else:
                        st.warning("No schema version information found")
            except Exception as e:
                st.error(f"Error checking schema version: {str(e)}")

@handle_exceptions
def main():
    """Main function to run the Streamlit app"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Log app start
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_interaction("App started", f"Time: {start_time}")
    
    # Set up page config
    st.set_page_config(
        page_title="Dealer Feasibility Tool",
        page_icon="🏢",
        layout="wide"
    )
    
    # Initialize session state
    if "dealer" not in st.session_state:
        st.session_state.dealer = None
    if "scenario" not in st.session_state:
        st.session_state.scenario = None
    if "results" not in st.session_state:
        st.session_state.results = {}
    
    # App title
    st.title("Dealer Feasibility Analysis Tool")
    
    # Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page",
        [
            "Dealer Information", 
            "Scenario Setup", 
            "Results",
            "Detailed Analysis", 
            "Comparison", 
            "Reports",
            "Database Admin"
        ]
    )
    log_interaction("Viewed page", page)
    
    if page == "Dealer Information":
        handle_dealer_page()
    elif page == "Scenario Setup":
        handle_scenario_page()
    elif page == "Results":
        handle_results_page()
    elif page == "Detailed Analysis":
        handle_detailed_analysis_page()
    elif page == "Comparison":
        handle_comparison_page()
    elif page == "Reports":
        handle_reports_page()
    elif page == "Database Admin":
        handle_database_admin_page()

# Run the app
if __name__ == "__main__":
    main() 