"""
Test script for financial metrics calculation
"""
import os
import sys
import logging
import traceback
from datetime import datetime

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/test_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

# Import required modules
from src.models.dealer import DealerOutlet
from src.models.scenario import Scenario
from src.calculations.sales import SalesCalculator

def create_test_dealer():
    """Create a test dealer"""
    print("Creating test dealer...")
    
    try:
        dealer = DealerOutlet(
            name="Test Dealer",
            location="Test Location",
            pmg_sales=1000,  # 1000 liters per day
            hsd_sales=2000,  # 2000 liters per day
            hobc_sales=100,  # 100 liters per day
            lube_sales=50,   # 50 liters per day
            initial_investment=5000000,  # 5 million PKR
            operating_costs=50000  # 50,000 PKR per month
        )
        
        print(f"Successfully created test dealer: {dealer.name}")
        return dealer
    except Exception as e:
        print(f"Error creating test dealer: {str(e)}")
        traceback.print_exc()
        return None

def create_test_scenario():
    """Create a test scenario with different margin formats"""
    print("Creating test scenario...")
    
    try:
        # Test 1: Simple float margins
        scenario1 = Scenario(
            name="Test Scenario 1 - Simple Margins",
            description="Scenario with simple float margins",
            discount_rate=0.10,
            inflation_rate=0.05,
            tax_rate=0.29,
            analysis_years=10,
            default_growth_rates={
                'pmg': 0.05,
                'hsd': 0.05,
                'hobc': 0.06,
                'lube': 0.01
            },
            default_margins={
                'pmg': 5.0,
                'hsd': 4.0,
                'hobc': 6.0,
                'lube': 100.0
            },
            signage_maintenance=5000,
            signage_maintenance_year=3
        )
        
        # Test 2: Dictionary margins
        scenario2 = Scenario(
            name="Test Scenario 2 - Dictionary Margins",
            description="Scenario with dictionary margins",
            discount_rate=0.10,
            inflation_rate=0.05,
            tax_rate=0.29,
            analysis_years=10,
            default_growth_rates={
                'pmg': {1: 0.05, 2: 0.04, 3: 0.03},
                'hsd': {1: 0.05, 2: 0.04, 3: 0.03},
                'hobc': {1: 0.06, 2: 0.05, 3: 0.04},
                'lube': {1: 0.01, 2: 0.01, 3: 0.01}
            },
            default_margins={
                'pmg': {1: 5.0, 2: 5.2, 3: 5.4},
                'hsd': {1: 4.0, 2: 4.2, 3: 4.4},
                'hobc': {1: 6.0, 2: 6.2, 3: 6.4},
                'lube': {1: 100.0, 2: 102.0, 3: 104.0}
            },
            signage_maintenance=5000,
            signage_maintenance_year=3
        )
        
        # Mixed scenario with different formats
        scenario3 = Scenario(
            name="Test Scenario 3 - Mixed Formats",
            description="Scenario with mixed formats for margins and growth rates",
            discount_rate=0.10,
            inflation_rate=0.05,
            tax_rate=0.29,
            analysis_years=10,
            default_growth_rates={
                'pmg': 0.05,
                'hsd': {1: 0.05, 2: 0.04, 3: 0.03},
                'hobc': 0.06,
                'lube': {1: 0.01, 2: 0.01, 3: 0.01}
            },
            default_margins={
                'pmg': {1: 5.0, 2: 5.2, 3: 5.4},
                'hsd': 4.0,
                'hobc': {1: 6.0, 2: 6.2, 3: 6.4},
                'lube': 100.0
            },
            signage_maintenance=5000,
            signage_maintenance_year=3
        )
        
        print(f"Successfully created test scenarios")
        return [scenario1, scenario2, scenario3]
    except Exception as e:
        print(f"Error creating test scenarios: {str(e)}")
        traceback.print_exc()
        return None

def test_calculate_metrics(dealer, scenarios):
    """Test calculating financial metrics with different scenarios"""
    print("\n=== Testing Financial Metrics Calculation ===")
    
    for i, scenario in enumerate(scenarios):
        print(f"\nTesting Scenario {i+1}: {scenario.name}")
        print(f"Description: {scenario.description}")
        
        try:
            # Debug info
            print(f"Growth rates type: {type(scenario.default_growth_rates)}")
            print(f"PMG growth rates: {scenario.default_growth_rates.get('pmg', 'Not found')}")
            print(f"Margins type: {type(scenario.default_margins)}")
            print(f"PMG margins: {scenario.default_margins.get('pmg', 'Not found')}")
            
            # Calculate metrics
            results = SalesCalculator.run_scenario(dealer, scenario)
            
            # Display results
            if results:
                print(f"\nSuccess! Results for {scenario.name}:")
                print(f"NPV: PKR {results.get('npv', 0):,.0f}")
                print(f"IRR: {results.get('irr', 0) * 100:.2f}%")
                print(f"Payback Period: {results.get('payback_period', 0):.2f} years")
                
                # Check yearly data
                yearly_data = results.get('yearly_data', {})
                if yearly_data:
                    print(f"\nFirst year sales:")
                    for product in ['pmg', 'hsd', 'hobc', 'lube']:
                        if f"{product}_sales" in yearly_data:
                            print(f"{product.upper()} Sales: {yearly_data[f'{product}_sales'].get(0, 0):,.0f} liters")
                    
                    print(f"\nFirst year revenue:")
                    for product in ['pmg', 'hsd', 'hobc', 'lube']:
                        if f"{product}_revenue" in yearly_data:
                            print(f"{product.upper()} Revenue: PKR {yearly_data[f'{product}_revenue'].get(0, 0):,.0f}")
            else:
                print(f"No results returned for {scenario.name}")
        
        except AttributeError as e:
            print(f"Attribute error calculating metrics for {scenario.name}: {str(e)}")
            if "'int' object has no attribute 'values'" in str(e):
                print("This is the specific error we're trying to fix!")
            traceback.print_exc()
        
        except Exception as e:
            print(f"Error calculating metrics for {scenario.name}: {str(e)}")
            traceback.print_exc()

def main():
    """Main function for testing"""
    print("=== Testing Financial Metrics ===")
    
    # Create test data
    dealer = create_test_dealer()
    scenarios = create_test_scenario()
    
    if not dealer or not scenarios:
        print("Failed to create test data. Exiting.")
        return
    
    # Test metrics calculation
    test_calculate_metrics(dealer, scenarios)
    
    print("\nTest script completed.")

if __name__ == "__main__":
    main() 