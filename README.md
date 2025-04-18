# Dealer Feasibility Analysis Tool

A comprehensive feasibility analysis tool for retail outlet dealers, providing financial metrics calculation (NPV, IRR, Payback Period) across multiple scenarios.

## Features

- Complete dealer/outlet data management
- Multiple scenario analysis
- Financial metrics calculation (NPV, IRR, Payback Period)
- Visualization of results with interactive charts
- Excel file import/export
- Detailed report generation
- Scenario comparison

## Installation

1. Clone this repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the Streamlit application:

```bash
cd dealer_feasibility
streamlit run app.py
```

The application will open in your web browser.

## Workflow

1. **Import/Export**: Upload an existing DF format Excel file or start from scratch
2. **Dealer Information**: Enter dealer details and initial sales projections
3. **Scenario Analysis**: Define various scenarios with different parameters
4. **Results & Comparison**: View results, compare scenarios, and generate reports

## Project Structure

```
dealer_feasibility/
│
├── app.py                  # Main Streamlit application
├── requirements.txt        # Dependencies
│
├── src/
│   ├── models/             # Data models
│   │   ├── dealer.py       # Dealer data model
│   │   └── scenario.py     # Scenario data model
│   │
│   ├── calculations/       # Financial calculations
│   │   ├── financial.py    # NPV, IRR, Payback calculations
│   │   └── sales.py        # Sales projection calculations
│   │
│   ├── excel/              # Excel file handling
│   │   ├── parser.py       # Excel file reader/writer
│   │   └── report.py       # Report generation
│   │
│   └── ui/                 # UI components (future expansion)
│
└── data/
    └── templates/          # Excel templates
```

## Requirements

- Python 3.8+
- Streamlit
- Pandas
- NumPy
- Plotly
- OpenPyXL
- XlsxWriter 
