from scrape_all import scrape_mlh
import time

print("Running manual MLH update (V2)...")
try:
    scrape_mlh()
    print("Manual MLH update complete!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
