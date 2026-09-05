#!/usr/bin/env python3
"""Compatibility entrypoint for the safe, isolated investor demo seeder."""

from seed_investor_demo import main

if __name__ == "__main__":
    print("Legacy fake-commerce demo seeding has been disabled; using isolated synthetic data.")
    main()
