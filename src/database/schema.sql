-- Schema Version Table
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY,
    version VARCHAR(20) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

-- Insert current schema version if not exists
INSERT INTO schema_version (id, version, description)
SELECT 1, '1.0.0', 'Initial schema setup'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE id = 1);

-- Enable RLS (Row Level Security)
ALTER TABLE IF EXISTS dealers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS investment_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS growth_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS margins ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS calculation_results ENABLE ROW LEVEL SECURITY;

-- Dealers Table
CREATE TABLE IF NOT EXISTS dealers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    district TEXT,
    feeding_point TEXT,
    area_executive TEXT,
    referred_by TEXT,
    pmg_sales REAL,
    hsd_sales REAL,
    hobc_sales REAL,
    lube_sales REAL,
    initial_investment REAL,
    operating_costs REAL,
    rental_streams JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Investment Items Table (related to dealers)
CREATE TABLE IF NOT EXISTS investment_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dealer_id UUID REFERENCES dealers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    cost REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Scenarios Table
CREATE TABLE IF NOT EXISTS scenarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    discount_rate REAL,
    inflation_rate REAL,
    tax_rate REAL,
    analysis_years INTEGER,
    signage_maintenance REAL,
    signage_maintenance_year INTEGER,
    other_maintenance REAL,
    other_maintenance_year INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Growth Rates Table (related to scenarios)
CREATE TABLE IF NOT EXISTS growth_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    product TEXT NOT NULL,
    year INTEGER NOT NULL,
    rate REAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(scenario_id, product, year)
);

-- Margins Table (related to scenarios)
CREATE TABLE IF NOT EXISTS margins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    product TEXT NOT NULL,
    year INTEGER NOT NULL,
    margin REAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(scenario_id, product, year)
);

-- Calculation Results Table
CREATE TABLE IF NOT EXISTS calculation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dealer_id UUID REFERENCES dealers(id) ON DELETE CASCADE,
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    npv REAL,
    irr REAL,
    payback_period REAL,
    cash_flows JSON,
    yearly_data JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(dealer_id, scenario_id)
);

-- Policies for service_role (to allow backend access)
DROP POLICY IF EXISTS service_policy_dealers ON dealers;
CREATE POLICY service_policy_dealers ON dealers FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS service_policy_investment_items ON investment_items;
CREATE POLICY service_policy_investment_items ON investment_items FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS service_policy_scenarios ON scenarios;
CREATE POLICY service_policy_scenarios ON scenarios FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS service_policy_growth_rates ON growth_rates;
CREATE POLICY service_policy_growth_rates ON growth_rates FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS service_policy_margins ON margins;
CREATE POLICY service_policy_margins ON margins FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS service_policy_calculation_results ON calculation_results;
CREATE POLICY service_policy_calculation_results ON calculation_results FOR ALL TO service_role USING (true);

-- Policies for authenticated users (keep for future use)
DROP POLICY IF EXISTS dealers_policy ON dealers;
CREATE POLICY dealers_policy ON dealers FOR ALL TO authenticated USING (true);

DROP POLICY IF EXISTS investment_items_policy ON investment_items;
CREATE POLICY investment_items_policy ON investment_items FOR ALL TO authenticated USING (true);

DROP POLICY IF EXISTS scenarios_policy ON scenarios;
CREATE POLICY scenarios_policy ON scenarios FOR ALL TO authenticated USING (true);

DROP POLICY IF EXISTS growth_rates_policy ON growth_rates;
CREATE POLICY growth_rates_policy ON growth_rates FOR ALL TO authenticated USING (true);

DROP POLICY IF EXISTS margins_policy ON margins;
CREATE POLICY margins_policy ON margins FOR ALL TO authenticated USING (true);

DROP POLICY IF EXISTS calculation_results_policy ON calculation_results;
CREATE POLICY calculation_results_policy ON calculation_results FOR ALL TO authenticated USING (true);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_investment_items_dealer_id ON investment_items(dealer_id);
CREATE INDEX IF NOT EXISTS idx_growth_rates_scenario_id ON growth_rates(scenario_id);
CREATE INDEX IF NOT EXISTS idx_margins_scenario_id ON margins(scenario_id);
CREATE INDEX IF NOT EXISTS idx_calculation_results_dealer_scenario ON calculation_results(dealer_id, scenario_id); 