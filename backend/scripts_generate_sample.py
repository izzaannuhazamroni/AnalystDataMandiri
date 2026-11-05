"""Buat data contoh penjualan: python scripts_generate_sample.py ../sample_data/penjualan_contoh.csv"""
import random
import sys
from datetime import date, timedelta

import pandas as pd

random.seed(7)
cabang = ["Jakarta", "Surabaya", "Bandung", "Madiun", "Malang", "Medan", "Makassar"]
kategori = ["Makanan", "Minuman", "Snack"]
rows = []
start = date(2025, 1, 1)
for i in range(1, 3001):
    d = start + timedelta(days=random.randint(0, 600))
    qty = random.randint(1, 20)
    harga = random.choice([5000, 12000, 25000, 40000, 75000])
    omset = qty * harga
    hpp = int(omset * random.uniform(0.5, 0.7))
    biaya = int(omset * random.uniform(0.05, 0.12))
    rows.append(
        {
            "No Transaksi": f"TRX{i:05d}",
            "Tanggal": d.strftime("%d/%m/%Y"),
            "Cabang": random.choice(cabang),
            "Kategori": random.choice(kategori),
            "Qty": qty,
            "Harga Satuan": harga,
            "Omset": omset,
            "HPP": hpp,
            "Biaya Operasional": biaya,
        }
    )
out = sys.argv[1] if len(sys.argv) > 1 else "penjualan_contoh.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print("ditulis:", out)
