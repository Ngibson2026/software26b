
# init_db.py
import sqlite3
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    

    # ======================
    # 2. Give starter capital to existing users
    # ======================
    print("💰 Checking and updating user balances...")

    # Find users who don't have a balance row yet
    cursor.execute("""
        SELECT id FROM Users 
        WHERE id NOT IN (SELECT user_id FROM UserBalances)
    """)
    users_without_balance = cursor.fetchall()

    if users_without_balance:
        for user in users_without_balance:
            cursor.execute(
                "INSERT INTO UserBalances (user_id, cash_balance) VALUES (?, 10000.00)",
                (user['id'],)
            )
        conn.commit()
        print(f"✅ Added $10,000 starter capital to {len(users_without_balance)} existing user(s).")
    else:
        print("✅ All existing users already have a balance.")

    # ======================
    # 3. Final check
    # ======================
    cursor.execute("SELECT COUNT(*) as count FROM UserBalances")
    total_balances = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM Users")
    total_users = cursor.fetchone()['count']

    print(f"\n🎉 Database initialization completed!")
    print(f"   Total Users: {total_users}")
    print(f"   Users with Balance: {total_balances}")
    print(f"   Starter Capital: $10,000 per user")

    conn.close()

if __name__ == "__main__":
    init_database()
    input("\nPress Enter to exit...")