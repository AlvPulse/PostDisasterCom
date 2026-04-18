import json
import csv
import os

class DataExporter:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def export_summary_json(self, data, filename="summary.json"):
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Exported JSON to {path}")

    def export_summary_csv(self, rows, filename="summary.csv"):
        path = os.path.join(self.output_dir, filename)
        if not rows: return
        keys = rows[0].keys()
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported CSV to {path}")
