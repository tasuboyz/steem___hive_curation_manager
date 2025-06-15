#!/usr/bin/env python3
"""
Script di test per verificare che tutto funzioni correttamente
"""

import sys
import os

# Aggiungi il percorso del progetto al Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test degli import"""
    print("🧪 Testing imports...")
    
    try:
        from curation.components.factory import create_app
        print("✅ Factory import OK")
        
        from curation.services.auth_service import AuthService
        print("✅ AuthService import OK")
        
        from curation.models.auth import UserAccount, UserWatchedAccount
        print("✅ Auth models import OK")
        
        from curation.middleware.auth_middleware import auth_required
        print("✅ Auth middleware import OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_app_creation():
    """Test della creazione dell'app"""
    print("\n🧪 Testing app creation...")
    
    try:
        from curation.components.factory import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App created successfully")
            print(f"✅ App name: {app.name}")
            
            # Test delle route
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            required_routes = [
                '/', '/login.html', '/api/auth/login', 
                '/api/auth/logout', '/api/auth/me', '/api/auth/check'
            ]
            
            missing_routes = [route for route in required_routes if route not in routes]
            if missing_routes:
                print(f"⚠️  Missing routes: {missing_routes}")
            else:
                print("✅ All required routes present")
            
            return True
            
    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False

def test_database():
    """Test del database"""
    print("\n🧪 Testing database...")
    
    try:
        from curation.components.factory import create_app
        from curation.components.db import db
        
        app = create_app()
        
        with app.app_context():
            # Test connessione database
            db.engine.execute('SELECT 1')
            print("✅ Database connection OK")
            
            # Test tabelle
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Database tables: {tables}")
            
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_static_files():
    """Test dei file statici"""
    print("\n🧪 Testing static files...")
    
    required_files = [
        'static/js/app.js',
        'static/js/modules/api.js',
        'static/js/modules/ui.js',
        'static/style.css',
        'templates/index.html',
        'templates/login.html'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required static files present")
        return True

def main():
    print("🚀 Running system tests...\n")
    
    tests = [
        test_imports,
        test_app_creation, 
        test_database,
        test_static_files
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! The system should work correctly.")
        print("\n📝 Next steps:")
        print("1. Initialize database: python init_auth_db.py")
        print("2. Start application: python app.py")
        print("3. Open browser: http://localhost:8089")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please fix issues before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()
