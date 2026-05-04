#!/usr/bin/env python
# fix_bank_codes.py - Fix RBM bank BIC codes
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')  # Replace with your project name
django.setup()

from eft_app.models import Bank

def fix_rbm_bank_codes():
    """Fix RBM bank BIC codes to end with 0 instead of W"""
    
    print("=" * 60)
    print("Fixing RBM Bank BIC Codes")
    print("=" * 60)
    
    # Find banks that need fixing
    banks_to_fix = Bank.objects.filter(
        swift_code__startswith='NBMA',
        swift_code__endswith='W'
    )
    
    print(f"\nFound {banks_to_fix.count()} banks with incorrect BIC codes:")
    
    # Show current state
    for bank in banks_to_fix:
        print(f"  📌 {bank.bank_name}: {bank.swift_code}")
    
    if banks_to_fix.count() == 0:
        print("\n✅ No banks need fixing!")
        return
    
    # Confirm with user
    response = input(f"\nFix {banks_to_fix.count()} banks? (y/n): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    # Fix each bank
    fixed = []
    for bank in banks_to_fix:
        old_code = bank.swift_code
        bank.swift_code = old_code[:-1] + '0'
        bank.save()
        fixed.append((bank.bank_name, old_code, bank.swift_code))
        print(f"  ✅ Fixed: {bank.bank_name}: {old_code} -> {bank.swift_code}")
    
    # Verify all are fixed
    still_bad = Bank.objects.filter(
        swift_code__startswith='NBMA',
        swift_code__endswith='W'
    )
    
    print("\n" + "=" * 60)
    print(f"✅ Successfully fixed {len(fixed)} banks")
    
    if still_bad.exists():
        print(f"⚠️ Warning: {still_bad.count()} banks still need attention!")
        for bank in still_bad:
            print(f"   - {bank.bank_name}: {bank.swift_code}")
    else:
        print("✅ All RBM banks now have correct BIC codes!")
    
    # Show all RBM banks after fix
    print("\nCurrent RBM banks:")
    all_rbm = Bank.objects.filter(swift_code__startswith='NBMA')
    for bank in all_rbm:
        print(f"  ✅ {bank.bank_name}: {bank.swift_code}")

def check_bank_codes():
    """Check all bank codes for validity"""
    
    print("\n" + "=" * 60)
    print("Checking All Bank BIC Codes")
    print("=" * 60)
    
    all_banks = Bank.objects.all()
    
    valid_count = 0
    invalid_count = 0
    invalid_banks = []
    
    # BIC pattern: 8 or 11 characters, first 4 letters, next 2 letters, next 2 letters/digits, optional 3 letters/digits
    import re
    bic_pattern = re.compile(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$')
    
    for bank in all_banks:
        if bic_pattern.match(bank.swift_code):
            valid_count += 1
            print(f"  ✅ {bank.bank_name}: {bank.swift_code}")
        else:
            invalid_count += 1
            invalid_banks.append(bank)
            print(f"  ❌ {bank.bank_name}: {bank.swift_code} (INVALID FORMAT)")
    
    print("\n" + "=" * 60)
    print(f"Summary: {valid_count} valid, {invalid_count} invalid")
    
    if invalid_banks:
        print("\n⚠️ Invalid banks need attention:")
        for bank in invalid_banks:
            print(f"   - {bank.bank_name}: {bank.swift_code}")
        
        fix = input("\nFix invalid banks? (y/n): ")
        if fix.lower() == 'y':
            for bank in invalid_banks:
                # Try to auto-fix
                old_code = bank.swift_code
                # Convert to uppercase and remove spaces
                new_code = old_code.upper().strip()
                # If it's NBMA and ends with W, fix to 0
                if new_code.startswith('NBMA') and new_code.endswith('W'):
                    new_code = new_code[:-1] + '0'
                # Ensure length is 11
                if len(new_code) > 11:
                    new_code = new_code[:11]
                bank.swift_code = new_code
                bank.save()
                print(f"  ✅ Fixed: {bank.bank_name}: {old_code} -> {new_code}")

if __name__ == '__main__':
    fix_rbm_bank_codes()
    check_bank_codes()