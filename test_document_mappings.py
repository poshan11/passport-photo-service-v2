#!/usr/bin/env python3
"""
Comprehensive test for updated document type mappings and canvas selection.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.process_images import US_DOCUMENT_TYPES, select_canvas_by_region, DOCUMENT_CONFIGS

def test_canvas_selection():
    """Test canvas selection for various document types"""
    
    print("=" * 80)
    print("CANVAS SELECTION TESTS")
    print("=" * 80)
    
    # Test cases: (doc_type, expected_canvas)
    test_cases = [
        # US documents (should use 4x6)
        ('default', '4x6'),
        ('baby_passport', '4x6'),
        ('ead_card', '4x6'),
        ('green_card', '4x6'),
        ('nfa_atf', '4x6'),
        ('real_id', '4x6'),
        ('student_id', '4x6'),
        ('us_passport', '4x6'),
        ('us_visa', '4x6'),
        ('usa_REAL_ID', '4x6'),
        ('usa_passport', '4x6'),
        ('usa_immigrant_visa', '4x6'),
        ('usa_nonimmigrant_visa', '4x6'),
        ('uscis', '4x6'),
        ('visa_photo', '4x6'),
        
        # International documents (should use 5x7)
        ('custom_size', '5x7'),  # This was the key fix
        ('saudi_arabia_passport', '5x7'),
        ('vietnam_passport', '5x7'),
        ('canada_passport', '5x7'),
        ('uk_passport', '5x7'),
        ('chinese_visa', '5x7'),
        ('unknown_document', '5x7'),  # Default fallback
    ]
    
    passed = 0
    failed = 0
    
    for doc_type, expected_canvas in test_cases:
        actual_canvas = select_canvas_by_region(doc_type)
        
        if actual_canvas == expected_canvas:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
            
        in_us_set = doc_type in US_DOCUMENT_TYPES
        in_config = doc_type in DOCUMENT_CONFIGS
        
        print(f"{status:8} {doc_type:25} → {actual_canvas} (expected: {expected_canvas}) | US: {in_us_set} | Config: {in_config}")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0

def test_specific_issues():
    """Test specific issues identified in the analysis"""
    
    print("\n" + "=" * 80)
    print("SPECIFIC ISSUE TESTS")
    print("=" * 80)
    
    issues = []
    
    # Issue 1: custom_size should use 5x7
    canvas = select_canvas_by_region('custom_size')
    if canvas != '5x7':
        issues.append(f"custom_size uses {canvas} instead of 5x7")
    else:
        print("✅ custom_size correctly uses 5x7 canvas")
    
    # Issue 2: Saudi Arabia should use 5x7
    canvas = select_canvas_by_region('saudi_arabia_passport')
    if canvas != '5x7':
        issues.append(f"saudi_arabia_passport uses {canvas} instead of 5x7")
    else:
        print("✅ saudi_arabia_passport correctly uses 5x7 canvas")
    
    # Issue 3: USA documents should use 4x6
    usa_docs = ['usa_REAL_ID', 'usa_passport', 'usa_immigrant_visa', 'usa_nonimmigrant_visa']
    for doc in usa_docs:
        canvas = select_canvas_by_region(doc)
        if canvas != '4x6':
            issues.append(f"{doc} uses {canvas} instead of 4x6")
        else:
            print(f"✅ {doc} correctly uses 4x6 canvas")
    
    # Issue 4: All USA documents should have configs
    for doc in usa_docs:
        if doc not in DOCUMENT_CONFIGS:
            issues.append(f"{doc} missing from DOCUMENT_CONFIGS")
        else:
            print(f"✅ {doc} has document configuration")
    
    if issues:
        print(f"\n❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ All specific issues resolved!")
        return True

def test_frontend_consistency():
    """Test consistency with frontend document types"""
    
    print("\n" + "=" * 80)
    print("FRONTEND CONSISTENCY TESTS")
    print("=" * 80)
    
    # Frontend USA documents (from analysis)
    frontend_usa_docs = [
        'baby_passport',
        'ead_card', 
        'green_card',
        'nfa_atf',
        'student_id',
        'usa_REAL_ID',
        'usa_immigrant_visa',
        'usa_nonimmigrant_visa',
        'usa_passport',  
        'uscis'
    ]
    
    issues = []
    
    print("Frontend USA documents canvas selection:")
    for doc in frontend_usa_docs:
        canvas = select_canvas_by_region(doc)
        in_us_set = doc in US_DOCUMENT_TYPES  
        
        if canvas != '4x6':
            issues.append(f"Frontend USA doc {doc} uses {canvas} instead of 4x6")
        
        if not in_us_set:
            issues.append(f"Frontend USA doc {doc} not in US_DOCUMENT_TYPES")
            
        status = "✅" if (canvas == '4x6' and in_us_set) else "❌"
        print(f"   {status} {doc:25} → {canvas} | In US set: {in_us_set}")
    
    if issues:
        print(f"\n❌ Found {len(issues)} consistency issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ All frontend documents correctly mapped!")
        return True

def test_large_format_documents():
    """Test that large format documents (40x60mm) use 5x7 canvas"""
    
    print("\n" + "=" * 80)
    print("LARGE FORMAT DOCUMENT TESTS")
    print("=" * 80)
    
    # Documents that should use large format (from analysis)
    large_format_docs = [
        'saudi_arabia_passport',
        'vietnam_passport', 
        'vietnam_visa',
        'custom_size'
    ]
    
    issues = []
    
    print("Large format documents (should use 5x7):")
    for doc in large_format_docs:
        canvas = select_canvas_by_region(doc)
        
        if canvas != '5x7':
            issues.append(f"Large format doc {doc} uses {canvas} instead of 5x7")
            
        status = "✅" if canvas == '5x7' else "❌"
        print(f"   {status} {doc:25} → {canvas}")
    
    if issues:
        print(f"\n❌ Found {len(issues)} large format issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ All large format documents correctly use 5x7!")
        return True

def main():
    """Run all tests"""
    
    print("🔍 DOCUMENT TYPE MAPPING TESTS")
    print(f"Testing {len(US_DOCUMENT_TYPES)} US document types")
    print(f"Testing {len(DOCUMENT_CONFIGS)} document configurations")
    
    # Run all test suites
    results = []
    results.append(test_canvas_selection())
    results.append(test_specific_issues()) 
    results.append(test_frontend_consistency())
    results.append(test_large_format_documents())
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed_suites = sum(results)
    total_suites = len(results)
    
    if all(results):
        print(f"✅ ALL TESTS PASSED ({passed_suites}/{total_suites} test suites)")
        print("\n🎉 Document type mapping is correctly implemented!")
        print("   - custom_size uses 5x7 for flexibility")
        print("   - USA documents use 4x6 canvas")  
        print("   - International documents use 5x7 canvas")
        print("   - Frontend consistency maintained")
        return True
    else:
        print(f"❌ SOME TESTS FAILED ({passed_suites}/{total_suites} test suites passed)")
        print("\n⚠️  Please review the failed tests above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
