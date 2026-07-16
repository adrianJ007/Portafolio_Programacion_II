import pymysql

DB_HOST = 'localhost'
DB_PORT = 3307
DB_NAME = 'chiriqui_main'
DB_USER = 'root'
DB_PASS = 'morena12345'

# Datos de los combos (con empresa_id = 1, asumiendo que existe una empresa)
combos_data = [
    ("Combo Clásico de Hamburguesa", "Jugosa hamburguesa con queso cheddar, lechuga y tomate en bollo de brioche.", "Hamburguesa, papas fritas, refresco", 9.99),
    ("Combo de Pollo Crujiente", "Tres piezas de pollo frito crujiente, puré de papas con gravy, biscuit y té dulce helado.", "Pollo frito, puré con gravy, biscuit, té dulce", 10.99),
    ("Combo Pizza Personal y Nudos de Ajo", "Pizza personal de pepperoni y mozzarella, acompañada de nudos de ajo y refresco oscuro.", "Pizza pepperoni, nudos de ajo, refresco", 8.99),
    ("Combo Sushi Variado", "Surtido: 8 California roll, 4 Spicy Tuna, 4 nigiri de salmón. Incluye sopa miso y té verde helado.", "California roll, spicy tuna, nigiri, sopa miso, té verde", 12.99)
]

conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
cursor = conn.cursor()

# Verificar que existe al menos una empresa
cursor.execute("SELECT id FROM companies LIMIT 1")
empresa = cursor.fetchone()
if not empresa:
    print("❌ No hay empresas en MariaDB. Crea una desde la web primero.")
    exit()
company_id = empresa[0]

for name, desc, items, price in combos_data:
    # Verificar si ya existe para no duplicar
    cursor.execute("SELECT id FROM combos WHERE name = %s", (name,))
    if cursor.fetchone():
        print(f"⚠️ El combo '{name}' ya existe. Saltando.")
        continue
    cursor.execute(
        "INSERT INTO combos (name, description, items, price, company_id) VALUES (%s, %s, %s, %s, %s)",
        (name, desc, items, price, company_id)
    )
conn.commit()
print("✅ Combos insertados correctamente.")
conn.close()