from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class DealerOutlet:
    """
    Represents a dealer outlet with all necessary information for feasibility analysis.
    """
    # Basic information
    name: str
    location: str
    district: str = ""
    feeding_point: str = ""
    area_executive: str = ""
    referred_by: str = ""
    
    # Sales projections for first year (liters per day)
    pmg_sales: float = 0.0  # PMG (Petrol) sales
    hsd_sales: float = 0.0  # HSD (Diesel) sales
    hobc_sales: float = 0.0  # HOBC/XTRON sales
    lube_sales: float = 0.0  # Lubricant sales
    
    # Growth rates for projections
    pmg_growth_rate: Dict[int, float] = field(default_factory=lambda: {})
    hsd_growth_rate: Dict[int, float] = field(default_factory=lambda: {})
    hobc_growth_rate: Dict[int, float] = field(default_factory=lambda: {})
    lube_growth_rate: Dict[int, float] = field(default_factory=lambda: {})
    
    # Margins per product (per liter)
    pmg_margin: Dict[int, float] = field(default_factory=lambda: {})
    hsd_margin: Dict[int, float] = field(default_factory=lambda: {})
    hobc_margin: Dict[int, float] = field(default_factory=lambda: {})
    lube_margin: Dict[int, float] = field(default_factory=lambda: {})
    
    # Investment details
    initial_investment: float = 0.0
    investment_items: List[Dict] = field(default_factory=list)  # List of dictionaries with name, cost, quantity
    
    # Operating costs
    operating_costs: float = 0.0
    
    # Rental income streams
    rental_streams: Dict[int, float] = field(default_factory=lambda: {})
    
    # Site details
    proposal_number: str = ""
    start_date: Optional[datetime] = None
    site_category: str = "DF 'A1' (with civil & mechanical works)"
    smart_signage: str = "SSP A+"
    security_deposit: float = 0.0
    joining_fee: float = 0.0
    lease_rentals: float = 0.0
    annual_insurance: float = 0.0
    
    # Insurance details
    insurance_rates: Dict[str, float] = field(default_factory=lambda: {})
    
    # Database ID
    id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert dealer data to dictionary for serialization"""
        return {
            # Basic information
            'name': self.name,
            'location': self.location,
            'district': self.district,
            'feeding_point': self.feeding_point,
            'area_executive': self.area_executive,
            'referred_by': self.referred_by,
            
            # Sales projections
            'pmg_sales': self.pmg_sales,
            'hsd_sales': self.hsd_sales,
            'hobc_sales': self.hobc_sales,
            'lube_sales': self.lube_sales,
            
            # Growth rates
            'pmg_growth_rate': self.pmg_growth_rate,
            'hsd_growth_rate': self.hsd_growth_rate,
            'hobc_growth_rate': self.hobc_growth_rate,
            'lube_growth_rate': self.lube_growth_rate,
            
            # Margins
            'pmg_margin': self.pmg_margin,
            'hsd_margin': self.hsd_margin,
            'hobc_margin': self.hobc_margin,
            'lube_margin': self.lube_margin,
            
            # Investment
            'initial_investment': self.initial_investment,
            'investment_items': self.investment_items,
            
            # Costs
            'operating_costs': self.operating_costs,
            
            # Rental streams
            'rental_streams': self.rental_streams,
            
            # Site details
            'proposal_number': self.proposal_number,
            'start_date': self.start_date,
            'site_category': self.site_category,
            'smart_signage': self.smart_signage,
            'security_deposit': self.security_deposit,
            'joining_fee': self.joining_fee,
            'lease_rentals': self.lease_rentals,
            'annual_insurance': self.annual_insurance,
            
            # Insurance
            'insurance_rates': self.insurance_rates,
            
            # ID
            'id': self.id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DealerOutlet':
        """Create dealer outlet from dictionary"""
        return cls(
            name=data.get('name', ''),
            location=data.get('location', ''),
            district=data.get('district', ''),
            feeding_point=data.get('feeding_point', ''),
            area_executive=data.get('area_executive', ''),
            referred_by=data.get('referred_by', ''),
            pmg_sales=data.get('pmg_sales', 0.0),
            hsd_sales=data.get('hsd_sales', 0.0),
            hobc_sales=data.get('hobc_sales', 0.0),
            lube_sales=data.get('lube_sales', 0.0),
            pmg_growth_rate=data.get('pmg_growth_rate', {}),
            hsd_growth_rate=data.get('hsd_growth_rate', {}),
            hobc_growth_rate=data.get('hobc_growth_rate', {}),
            lube_growth_rate=data.get('lube_growth_rate', {}),
            pmg_margin=data.get('pmg_margin', {}),
            hsd_margin=data.get('hsd_margin', {}),
            hobc_margin=data.get('hobc_margin', {}),
            lube_margin=data.get('lube_margin', {}),
            initial_investment=data.get('initial_investment', 0.0),
            investment_items=data.get('investment_items', []),
            operating_costs=data.get('operating_costs', 0.0),
            rental_streams=data.get('rental_streams', {}),
            proposal_number=data.get('proposal_number', ''),
            start_date=data.get('start_date', None),
            site_category=data.get('site_category', ''),
            smart_signage=data.get('smart_signage', ''),
            security_deposit=data.get('security_deposit', 0.0),
            joining_fee=data.get('joining_fee', 0.0),
            lease_rentals=data.get('lease_rentals', 0.0),
            annual_insurance=data.get('annual_insurance', 0.0),
            insurance_rates=data.get('insurance_rates', {}),
            id=data.get('id', None)
        ) 