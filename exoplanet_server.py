"""
Exoplanet Data Server - Serves real NASA data to the visualization
"""
from flask import Flask, jsonify, send_file
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

def load_exoplanet_data():
    """Load and process exoplanet data from CSV files"""
    try:
        toi_df = pd.read_csv('data/TOI_2025.10.02_08.11.35.csv', comment='#')
        confirmed_df = pd.read_csv('data/cumulative_data.csv', comment='#')
        k2_df = pd.read_csv('data/k2pandc_2025.10.02_08.11.42.csv', comment='#')
        return toi_df, confirmed_df, k2_df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None

@app.route('/')
def index():
    return send_file('xx.html')

@app.route('/api/piz-zones')
def get_piz_zones():
    """Get Priority Investigation Zones from TOI data"""
    toi_df, _, _ = load_exoplanet_data()
    if toi_df is None:
        return jsonify({'error': 'Failed to load data'}), 500
    
    zones = []
    sample_toi = toi_df.head(20)
    
    for idx, row in sample_toi.iterrows():
        zone = {
            'id': f"PIZ-{row.get('toi', idx):05.2f}",
            'position': [
                (float(row.get('ra', 0)) % 360 - 180) / 10,
                (float(row.get('dec', 0))) / 10,
                (idx % 5 - 2) * 10
            ],
            'targets': int(row.get('toi', 1)),
            'priority': 'HIGH' if row.get('tfopwg_disp') == 'CP' else 'MEDIUM',
            'confidence': min(95, max(60, 70 + idx % 30))
        }
        zones.append(zone)
    
    return jsonify(zones)

@app.route('/api/planets')
def get_planets():
    """Get confirmed exoplanets data"""
    _, confirmed_df, _ = load_exoplanet_data()
    if confirmed_df is None:
        return jsonify({'error': 'Failed to load data'}), 500
    
    planets = []
    sample_confirmed = confirmed_df[confirmed_df['koi_disposition'] == 'CONFIRMED'].head(30)
    
    for idx, row in sample_confirmed.iterrows():
        planet = {
            'id': row.get('kepler_name', f"KOI-{row.get('kepoi_name', idx)}"),
            'position': [
                (float(row.get('ra', 0)) % 360 - 180) / 10,
                (float(row.get('dec', 0))) / 10,
                (idx % 5 - 2) * 10
            ],
            'size': float(row.get('koi_prad', 1.0)) if pd.notna(row.get('koi_prad')) else 1.0,
            'habitable': is_habitable(row),
            'mass': float(row.get('koi_prad', 1.0)) if pd.notna(row.get('koi_prad')) else 1.0,
            'radius': float(row.get('koi_prad', 1.0)) if pd.notna(row.get('koi_prad')) else 1.0,
            'period': float(row.get('koi_period', 10.0)) if pd.notna(row.get('koi_period')) else 10.0,
            'temp': float(row.get('koi_teq', 300)) if pd.notna(row.get('koi_teq')) else 300,
        }
        planets.append(planet)
    
    return jsonify(planets)

def is_habitable(row):
    """Determine if planet is potentially habitable"""
    try:
        temp = float(row.get('koi_teq', 0))
        radius = float(row.get('koi_prad', 0))
        insol = float(row.get('koi_insol', 0))
        
        if pd.notna(temp) and pd.notna(radius) and pd.notna(insol):
            return (200 < temp < 350 and 0.5 < radius < 2.0 and 0.2 < insol < 2.0)
        return False
    except:
        return False

@app.route('/api/planet/<planet_id>')
def get_planet_details(planet_id):
    """Get detailed information about a specific planet"""
    _, confirmed_df, _ = load_exoplanet_data()
    if confirmed_df is None:
        return jsonify({'error': 'Failed to load data'}), 500
    
    planet_row = confirmed_df[confirmed_df['kepler_name'] == planet_id]
    if planet_row.empty:
        return jsonify({'error': 'Planet not found'}), 404
    
    row = planet_row.iloc[0]
    details = {
        'id': planet_id,
        'mass': f"{float(row.get('koi_prad', 1.0)):.2f} Earth masses",
        'radius': f"{float(row.get('koi_prad', 1.0)):.2f} Earth radii",
        'period': f"{float(row.get('koi_period', 10.0)):.1f} days",
        'temp': f"{int(float(row.get('koi_teq', 300)))}K",
        'habitable': is_habitable(row)
    }
    return jsonify(details)

if __name__ == '__main__':
    print("🚀 Starting Exoplanet Data Server...")
    print("📊 Loading NASA data...")
    toi, confirmed, k2 = load_exoplanet_data()
    if toi is not None:
        print(f"✓ Loaded {len(toi)} TOI candidates")
        print(f"✓ Loaded {len(confirmed)} Kepler candidates")
        print(f"✓ Loaded {len(k2)} K2 candidates")
    print("🌐 Server running on http://localhost:5000")
    app.run(debug=True, port=5000)
