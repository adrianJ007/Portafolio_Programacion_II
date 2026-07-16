import sqlite3
import pymysql

DB_HOST = 'localhost'
DB_PORT = 3307
DB_NAME = 'chiriqui_main'
DB_USER = 'root'
DB_PASS = 'morena12345'

def main():
    sqlite_conn = sqlite3.connect('instance/chiriqui_main.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    mariadb_conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset='utf8mb4'
    )
    mariadb_cursor = mariadb_conn.cursor()
    mariadb_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    # Insertar companies (sin id, deja que MariaDB lo asigne)
    sqlite_cursor.execute("SELECT name, email, phone, address FROM companies")
    companies = sqlite_cursor.fetchall()
    for row in companies:
        mariadb_cursor.execute(
            "INSERT INTO companies (name, email, phone, address) VALUES (%s, %s, %s, %s)",
            row
        )
    mariadb_conn.commit()
    
    # Mapear id antiguo -> nuevo para companies
    sqlite_cursor.execute("SELECT id, email FROM companies")
    old_company_by_email = {email: old_id for old_id, email in sqlite_cursor.fetchall()}
    mariadb_cursor.execute("SELECT id, email FROM companies")
    new_company_by_email = {email: new_id for new_id, email in mariadb_cursor.fetchall()}
    company_id_map = {}
    for email, old_id in old_company_by_email.items():
        if email in new_company_by_email:
            company_id_map[old_id] = new_company_by_email[email]
    
    # Insertar combos
    sqlite_cursor.execute("SELECT name, description, items, price, company_id FROM combos")
    combos = sqlite_cursor.fetchall()
    for row in combos:
        new_cid = company_id_map.get(row[4])
        if new_cid:
            mariadb_cursor.execute(
                "INSERT INTO combos (name, description, items, price, company_id) VALUES (%s, %s, %s, %s, %s)",
                (row[0], row[1], row[2], row[3], new_cid)
            )
    mariadb_conn.commit()
    
    # Mapear id antiguo -> nuevo para combos (por nombre y company_id)
    sqlite_cursor.execute("SELECT id, name, company_id FROM combos")
    old_combos = sqlite_cursor.fetchall()
    combo_id_map = {}
    for old_id, name, old_cid in old_combos:
        new_cid = company_id_map.get(old_cid)
        if new_cid:
            mariadb_cursor.execute("SELECT id FROM combos WHERE name = %s AND company_id = %s", (name, new_cid))
            row = mariadb_cursor.fetchone()
            if row:
                combo_id_map[old_id] = row[0]
    
    # Insertar orders
    sqlite_cursor.execute("SELECT customer_name, quantity, total_price, status, created_at, company_id, combo_id FROM orders")
    orders = sqlite_cursor.fetchall()
    for row in orders:
        new_cid = company_id_map.get(row[5])
        new_combo_id = combo_id_map.get(row[6])
        if new_cid and new_combo_id:
            mariadb_cursor.execute(
                "INSERT INTO orders (customer_name, quantity, total_price, status, created_at, company_id, combo_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (row[0], row[1], row[2], row[3], row[4], new_cid, new_combo_id)
            )
    mariadb_conn.commit()
    
    mariadb_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    sqlite_conn.close()
    mariadb_conn.close()
    print("✅ Datos reinsertados correctamente.")

if __name__ == "__main__":
    main()