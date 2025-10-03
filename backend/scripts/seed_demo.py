#!/usr/bin/env python3
"""
Seed demo users, plans, and bills.

Usage: python scripts/seed_demo.py
"""
import os, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEMO_DIR = DATA_DIR / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

# copy demo CSVs into main data if not present

def copy_demo_file(src_name, dest_name):
    src = DEMO_DIR / src_name
    dest = DATA_DIR / dest_name
    if not src.exists():
        print(f"Missing demo file: {src}. Please ensure data/demo/ contains demo files.")
        return
    if dest.exists():
        print(f"{dest_name} already exists at data/; skipping copy.")
        return
    print(f"Copying {src_name} -> data/{dest_name}")
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def seed_db_from_csv(csv_path, ModelClass, session):
    import pandas as pd
    df = pd.read_csv(csv_path, dtype=str)
    created = 0
    for _, row in df.iterrows():
        kwargs = {k: (v if v == v else None) for k, v in row.to_dict().items()}
        try:
            obj = ModelClass(**kwargs)
            session.add(obj)
            created += 1
        except Exception as e:
            print("Could not create model instance:", e)
    try:
        session.commit()
    except Exception as e:
        print("Commit error:", e)
    print(f"Seeded {created} rows into {ModelClass}")


def main():
    # 1) copy demo CSVs into data/ if not present
    copy_demo_file("users_demo.csv", "users.csv")
    copy_demo_file("plans_demo.csv", "plans.csv")

    # copy sample bills into data folder
    bills_src = DEMO_DIR / "bills_demo"
    bills_dest = DATA_DIR / "bills_demo"
    if bills_src.exists() and not bills_dest.exists():
        bills_dest.mkdir(parents=True, exist_ok=True)
        for p in bills_src.iterdir():
            if p.is_file():
                print("Copying bill:", p.name)
                (bills_dest / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

    # 2) attempt DB seeding via SQLAlchemy if available
    try:
        sys.path.insert(0, str(ROOT))
        from backend.app.main import app
        from backend.app.models.models import db, User, Plan  # Plan may not exist; will raise
        with app.app_context():
            print("Trying to seed DB via SQLAlchemy models...")
            users_csv = str(DATA_DIR / "users.csv")
            if os.path.exists(users_csv):
                seed_db_from_csv(users_csv, User, db.session)
            plans_csv = str(DATA_DIR / "plans.csv")
            if os.path.exists(plans_csv):
                seed_db_from_csv(plans_csv, Plan, db.session)
            print("DB seeding done.")
            return
    except Exception as e:
        print("DB seeding skipped (couldn't import models/db or Plan not defined). Reason:", e)

    print("Demo files copied to data/. If you want DB seeds, ensure models.py exposes SQLAlchemy models named User and Plan and re-run this script.")


if __name__ == "__main__":
    main()
