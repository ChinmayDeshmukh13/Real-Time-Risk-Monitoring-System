# config/portfolio.py
# Single source of truth for portfolio configuration
# Import from here — never from main.py

HOLDINGS = {
    'HDFCBANK': 200, 'ICICIBANK': 300, 'KOTAKBANK': 100,
    'AXISBANK':  250, 'SBIN':      400, 'BAJFINANCE':  80,
    'TCS':       100, 'INFY':      200, 'WIPRO':       500,
    'HCLTECH':   300, 'RELIANCE':  150, 'ONGC':        600,
    'POWERGRID': 800, 'NTPC':      700, 'LT':          100,
    'HINDUNILVR':120, 'NESTLEIND':  50, 'ASIANPAINT':  100,
    'SUNPHARMA': 200, 'TITAN':     150,
}

SECTOR_MAP = {
    'HDFCBANK':   'Banking', 'ICICIBANK':  'Banking',
    'KOTAKBANK':  'Banking', 'AXISBANK':   'Banking',
    'SBIN':       'Banking', 'BAJFINANCE': 'Banking',
    'TCS':        'IT',      'INFY':       'IT',
    'WIPRO':      'IT',      'HCLTECH':    'IT',
    'RELIANCE':   'Energy',  'ONGC':       'Energy',
    'POWERGRID':  'Energy',  'NTPC':       'Energy',
    'LT':         'Energy',  'HINDUNILVR': 'Consumer',
    'NESTLEIND':  'Consumer','ASIANPAINT': 'Consumer',
    'SUNPHARMA':  'Consumer','TITAN':      'Consumer',
}

CONFIDENCE_LEVEL = 0.95
VAR_WINDOW_DAYS  = 252

OPTIONS_CONFIG = [
    {'symbol': 'ICICIBANK', 'option_type': 'call', 'quantity': 200},
    {'symbol': 'INFY',      'option_type': 'put',  'quantity': 200},
    {'symbol': 'TCS',       'option_type': 'call', 'quantity':  50},
    {'symbol': 'HDFCBANK',  'option_type': 'put',  'quantity': 150},
    {'symbol': 'RELIANCE',  'option_type': 'call', 'quantity': 100},
]