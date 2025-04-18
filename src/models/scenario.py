from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class Scenario:
    """
    Represents a scenario for dealer feasibility analysis
    containing all parameters needed for calculations.
    """
    # Basic scenario information
    name: str
    description: str = ""
    
    # Financial parameters
    discount_rate: float = 0.10  # Default 10%
    inflation_rate: float = 0.03  # Default 3%
    
    # Time horizon
    analysis_years: int = 15  # Default 15 years
    
    # Sales growth parameters
    default_growth_rates: Dict[str, Dict[int, float]] = field(default_factory=lambda: {
        'pmg': {},
        'hsd': {},
        'hobc': {},
        'lube': {}
    })
    
    # Product margins
    default_margins: Dict[str, Dict[int, float]] = field(default_factory=lambda: {
        'pmg': {},
        'hsd': {},
        'hobc': {},
        'lube': {}
    })
    
    # Tax rates
    tax_rate: float = 0.29  # Default corporate tax rate
    
    # Maintenance parameters
    signage_maintenance: float = 10000000.0  # Default to 10 million PKR
    signage_maintenance_year: int = 7  # Every 7th year
    other_maintenance: float = 2000000.0  # Default to 2 million PKR
    other_maintenance_year: int = 11  # At 11th year
    
    # Insurance parameters
    insurance_rates: Dict[str, float] = field(default_factory=lambda: {})
    
    # Other assumptions
    assumptions: Dict[str, Any] = field(default_factory=lambda: {})
    
    # ID field
    id: str = None
    
    def to_dict(self) -> Dict:
        """Convert scenario to dictionary for serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'discount_rate': self.discount_rate,
            'inflation_rate': self.inflation_rate,
            'analysis_years': self.analysis_years,
            'default_growth_rates': self.default_growth_rates,
            'default_margins': self.default_margins,
            'tax_rate': self.tax_rate,
            'signage_maintenance': self.signage_maintenance,
            'signage_maintenance_year': self.signage_maintenance_year,
            'other_maintenance': self.other_maintenance,
            'other_maintenance_year': self.other_maintenance_year,
            'insurance_rates': self.insurance_rates,
            'assumptions': self.assumptions,
            'id': self.id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Scenario':
        """Create scenario from dictionary"""
        return cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            discount_rate=data.get('discount_rate', 0.10),
            inflation_rate=data.get('inflation_rate', 0.03),
            analysis_years=data.get('analysis_years', 15),
            default_growth_rates=data.get('default_growth_rates', {
                'pmg': {},
                'hsd': {},
                'hobc': {},
                'lube': {}
            }),
            default_margins=data.get('default_margins', {
                'pmg': {},
                'hsd': {},
                'hobc': {},
                'lube': {}
            }),
            tax_rate=data.get('tax_rate', 0.29),
            signage_maintenance=data.get('signage_maintenance', 10000000.0),
            signage_maintenance_year=data.get('signage_maintenance_year', 7),
            other_maintenance=data.get('other_maintenance', 2000000.0),
            other_maintenance_year=data.get('other_maintenance_year', 11),
            insurance_rates=data.get('insurance_rates', {}),
            assumptions=data.get('assumptions', {}),
            id=data.get('id')
        )
        
    def get_default_growth_rate(self, product: str, year: int) -> float:
        """
        Get the default growth rate for a product and year
        """
        product_rates = self.default_growth_rates.get(product, {})
        return product_rates.get(year, 0.0)
    
    def get_default_margin(self, product: str, year: int) -> float:
        """
        Get the default margin for a product and year
        """
        product_margins = self.default_margins.get(product, {})
        return product_margins.get(year, 0.0) 