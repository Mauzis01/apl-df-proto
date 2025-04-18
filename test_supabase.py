"""
Test script for Supabase integration.

Run this script to verify that:
1. Supabase connection is working properly
2. All required tables exist
3. CRUD operations work correctly
"""

import os
import sys
import json
import logging
from pathlib import Path

# Set up logging
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

logging.basicConfig(
    filename=logs_dir / "supabase_test.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add parent directory to path to import from dealer_feasibility
sys.path.append(str(Path(__file__).parent.parent))

from dealer_feasibility.utils import test_supabase_connection
from dealer_feasibility.src.models.dealer import DealerOutlet
from dealer_feasibility.src.models.scenario import Scenario
from dealer_feasibility.src.database.repositories import DealerRepository, ScenarioRepository, ResultsRepository

def main():
    """Main test function"""
    print("\n=== Testing Supabase Integration ===\n")
    
    # Step 1: Test connection
    print("Testing Supabase connection...")
    connection_results = test_supabase_connection()
    
    if connection_results['connection']:
        print("✅ Connection established successfully!")
    else:
        print(f"❌ Connection failed: {connection_results.get('error', 'Unknown error')}")
        return
    
    # Check if tables exist
    tables_exist = all(info.get('exists', False) for info in connection_results['tables'].values())
    if tables_exist:
        print("✅ All required tables exist")
    else:
        missing_tables = [table for table, info in connection_results['tables'].items() if not info.get('exists', False)]
        print(f"❌ Missing tables: {', '.join(missing_tables)}")
        return
    
    # Step 2: Test CRUD operations
    print("\nTesting CRUD operations...")
    
    try:
        # Create test dealer
        print("\n--- Testing Dealer Repository ---")
        test_dealer = DealerOutlet(
            name=f"Test Dealer {os.urandom(4).hex()}",  # Unique name
            location="Test Location",
            pmg_sales=1000.0,
            hsd_sales=2000.0,
            hobc_sales=500.0,
            lube_sales=100.0,
            investment_items=[
                {
                    "name": "Test Item 1",
                    "cost": 100000.0,
                    "quantity": 2
                },
                {
                    "name": "Test Item 2",
                    "cost": 200000.0,
                    "quantity": 1
                }
            ]
        )
        
        # Save dealer
        print(f"Creating dealer: {test_dealer.name}")
        dealer_id = DealerRepository.save(test_dealer)
        print(f"✅ Dealer created with ID: {dealer_id}")
        
        # Fetch dealer
        print(f"Fetching dealer with ID: {dealer_id}")
        fetched_dealer = DealerRepository.get_by_id(dealer_id)
        if fetched_dealer and fetched_dealer.name == test_dealer.name:
            print(f"✅ Dealer fetched successfully: {fetched_dealer.name}")
        else:
            print(f"❌ Failed to fetch dealer correctly")
            
        # Create test scenario
        print("\n--- Testing Scenario Repository ---")
        test_scenario = Scenario(
            name=f"Test Scenario {os.urandom(4).hex()}",  # Unique name
            description="Test Description",
            discount_rate=0.12,
            inflation_rate=0.05,
            tax_rate=0.35,
            analysis_years=10,
            default_growth_rates={
                'pmg': {1: 0.05, 2: 0.04},
                'hsd': {1: 0.04, 2: 0.03},
                'hobc': {1: 0.06, 2: 0.05},
                'lube': {1: 0.01, 2: 0.01}
            },
            default_margins={
                'pmg': {1: 5.0, 2: 5.0},
                'hsd': {1: 4.0, 2: 4.0},
                'hobc': {1: 6.0, 2: 6.0},
                'lube': {1: 100.0, 2: 100.0}
            }
        )
        
        # Save scenario
        print(f"Creating scenario: {test_scenario.name}")
        scenario_id = ScenarioRepository.save(test_scenario)
        print(f"✅ Scenario created with ID: {scenario_id}")
        
        # Fetch scenario
        print(f"Fetching scenario with ID: {scenario_id}")
        fetched_scenario = ScenarioRepository.get_by_id(scenario_id)
        if fetched_scenario and fetched_scenario.name == test_scenario.name:
            print(f"✅ Scenario fetched successfully: {fetched_scenario.name}")
        else:
            print(f"❌ Failed to fetch scenario correctly")
            
        # Test Results Repository
        print("\n--- Testing Results Repository ---")
        test_results = {
            'npv': 1000000.0,
            'irr': 0.15,
            'payback_period': 4.5,
            'cash_flows': [
                -1000000.0,
                250000.0,
                300000.0,
                350000.0,
                400000.0
            ],
            'yearly_data': {
                'pmg_sales': {0: 365000.0, 1: 383250.0},
                'hsd_sales': {0: 730000.0, 1: 759200.0},
                'pmg_revenue': {0: 1825000.0, 1: 1916250.0},
                'hsd_revenue': {0: 2920000.0, 1: 3036800.0},
                'total_revenue': {0: 4745000.0, 1: 4953050.0}
            }
        }
        
        # Save results
        print(f"Saving results for dealer {dealer_id} and scenario {scenario_id}")
        result_id = ResultsRepository.save_result(dealer_id, scenario_id, test_results)
        print(f"✅ Results saved with ID: {result_id}")
        
        # Fetch results
        print(f"Fetching results for dealer {dealer_id} and scenario {scenario_id}")
        fetched_results = ResultsRepository.get_result(dealer_id, scenario_id)
        if fetched_results and 'npv' in fetched_results:
            print(f"✅ Results fetched successfully: NPV = {fetched_results['npv']}")
        else:
            print(f"❌ Failed to fetch results correctly")
            
        print("\n✅ All tests passed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        logging.error(f"Error during Supabase testing: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    main() 