"""
Test script for creating Dealer and Scenario objects
"""
import os
import sys
import logging
import inspect
from pprint import pprint

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/test_objects.log"),
        logging.StreamHandler()
    ]
)

# Import model classes
from src.models.dealer import DealerOutlet
from src.models.scenario import Scenario

def print_class_params(cls):
    """Print the parameters of a class constructor"""
    print(f"\n{cls.__name__} Constructor Parameters:")
    
    # Get constructor signature
    sig = inspect.signature(cls.__init__)
    for param_name, param in sig.parameters.items():
        if param_name != 'self':  # Skip 'self' parameter
            default = param.default if param.default is not inspect.Parameter.empty else "Required"
            print(f"  - {param_name}: {default}")

def test_dealer_creation():
    """Test creating a DealerOutlet object"""
    print("\n==== Testing DealerOutlet Creation ====")
    print_class_params(DealerOutlet)
    
    try:
        # Create a simple dealer
        dealer = DealerOutlet(
            name="Test Dealer",
            location="Test Location",
            start_date="2023-01-01",
            rental_streams={}
        )
        
        print("\nSuccessfully created dealer object:")
        print(f"  Name: {dealer.name}")
        print(f"  Location: {dealer.location}")
        print(f"  Start Date: {dealer.start_date}")
        
        # Test serialization
        dealer_dict = dealer.to_dict()
        print("\nDealer serialized to dictionary:")
        pprint(dealer_dict)
        
        return dealer
        
    except Exception as e:
        print(f"\nError creating dealer: {str(e)}")
        logging.error(f"Error creating dealer: {str(e)}")
        return None

def test_scenario_creation():
    """Test creating a Scenario object"""
    print("\n==== Testing Scenario Creation ====")
    print_class_params(Scenario)
    
    try:
        # Create default growth rates
        default_growth_rates = {
            "pmg": {1: 5.0, 2: 3.0},
            "hsd": {1: 4.0, 2: 2.5},
            "xtron": {1: 6.0, 2: 4.0},
            "lubricants": {1: 3.0, 2: 2.0}
        }
        
        # Create default margins
        default_margins = {
            "pmg": 3.5,
            "hsd": 2.8,
            "xtron": 4.2,
            "lubricants": 15.0
        }
        
        # Create a simple scenario
        scenario = Scenario(
            name="Test Scenario",
            description="A test scenario",
            discount_rate=10.0,
            inflation_rate=5.0,
            tax_rate=29.0,
            analysis_years=10,
            default_growth_rates=default_growth_rates,
            default_margins=default_margins,
            signage_maintenance=5000,
            signage_maintenance_year=3
        )
        
        print("\nSuccessfully created scenario object:")
        print(f"  Name: {scenario.name}")
        print(f"  Description: {scenario.description}")
        print(f"  Discount Rate: {scenario.discount_rate}%")
        print(f"  Analysis Years: {scenario.analysis_years}")
        
        # Test serialization
        scenario_dict = scenario.to_dict()
        print("\nScenario serialized to dictionary:")
        pprint(scenario_dict)
        
        return scenario
        
    except Exception as e:
        print(f"\nError creating scenario: {str(e)}")
        logging.error(f"Error creating scenario: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function to test object creation"""
    print("=== Testing Model Object Creation ===")
    
    # Test dealer creation
    dealer = test_dealer_creation()
    
    # Test scenario creation
    scenario = test_scenario_creation()
    
    if dealer and scenario:
        print("\nAll tests completed successfully!")
    else:
        print("\nSome tests failed. Check the logs for details.")

if __name__ == "__main__":
    main() 