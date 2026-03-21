"""Quick test script to verify data loading"""
import pandas as pd

print("Testing data loading...")

# Test TOI data
try:
    toi_df = pd.read_csv('data/TOI_2025.10.02_08.11.35.csv', comment='#')
    print(f"✓ TOI data loaded: {len(toi_df)} rows")
    print(f"  Columns: {list(toi_df.columns[:5])}...")
    print(f"  Sample TOI: {toi_df['toi'].iloc[0]}")
except Exception as e:
    print(f"✗ Failed to load TOI data: {e}")

# Test Kepler data
try:
    kepler_df = pd.read_csv('data/cumulative_data.csv', comment='#')
    confirmed = kepler_df[kepler_df['koi_disposition'] == 'CONFIRMED']
    print(f"✓ Kepler data loaded: {len(kepler_df)} rows, {len(confirmed)} confirmed")
    if len(confirmed) > 0:
        print(f"  Sample planet: {confirmed['kepler_name'].iloc[0]}")
except Exception as e:
    print(f"✗ Failed to load Kepler data: {e}")

# Test K2 data
try:
    k2_df = pd.read_csv('data/k2pandc_2025.10.02_08.11.42.csv', comment='#')
    print(f"✓ K2 data loaded: {len(k2_df)} rows")
    if len(k2_df) > 0:
        print(f"  Sample planet: {k2_df['pl_name'].iloc[0]}")
except Exception as e:
    print(f"✗ Failed to load K2 data: {e}")

print("\nData loading test complete!")
