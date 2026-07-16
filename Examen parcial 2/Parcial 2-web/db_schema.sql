CREATE DATABASE IF NOT EXISTS chinos_cafe;
USE chinos_cafe;

-- Tabla de pizzas
CREATE TABLE pizza (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL,
    ingredientes TEXT
);

-- Tabla de refrescos
CREATE TABLE refresco (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    precio DECIMAL(10,2) NOT NULL
);

-- Tabla de extras (adicionales)
CREATE TABLE extra (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    precio DECIMAL(10,2) NOT NULL
);

-- Tabla de combos (predefinidos por la empresa)
CREATE TABLE combo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL
);

-- Relación combo - pizza (muchos a muchos)
CREATE TABLE combo_pizza (
    combo_id INT,
    pizza_id INT,
    FOREIGN KEY (combo_id) REFERENCES combo(id) ON DELETE CASCADE,
    FOREIGN KEY (pizza_id) REFERENCES pizza(id) ON DELETE CASCADE,
    PRIMARY KEY (combo_id, pizza_id)
);

-- Relación combo - refresco
CREATE TABLE combo_refresco (
    combo_id INT,
    refresco_id INT,
    FOREIGN KEY (combo_id) REFERENCES combo(id) ON DELETE CASCADE,
    FOREIGN KEY (refresco_id) REFERENCES refresco(id) ON DELETE CASCADE,
    PRIMARY KEY (combo_id, refresco_id)
);

-- Relación combo - extra
CREATE TABLE combo_extra (
    combo_id INT,
    extra_id INT,
    FOREIGN KEY (combo_id) REFERENCES combo(id) ON DELETE CASCADE,
    FOREIGN KEY (extra_id) REFERENCES extra(id) ON DELETE CASCADE,
    PRIMARY KEY (combo_id, extra_id)
);

-- Tabla de pedidos
CREATE TABLE pedido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_nombre VARCHAR(100) NOT NULL,
    cliente_email VARCHAR(100) NOT NULL,
    cliente_direccion TEXT,
    total DECIMAL(10,2) NOT NULL,
    metodo_pago VARCHAR(50),
    costo_envio DECIMAL(10,2) DEFAULT 0,
    estado VARCHAR(20) DEFAULT 'pendiente',
    fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archivo_json_orden VARCHAR(200),
    archivo_json_pago VARCHAR(200)
);

-- Líneas del pedido
CREATE TABLE pedido_linea (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT,
    tipo_item ENUM('pizza','refresco','extra') NOT NULL,
    item_id INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedido(id) ON DELETE CASCADE
);

-- Datos iniciales mínimos (5 pizzas, 3 refrescos, 3 extras, 5 combos)
INSERT INTO pizza (nombre, descripcion, precio, ingredientes) VALUES
('Margarita', 'Salsa de tomate, mozzarella, albahaca', 8.50, 'Tomate,Mozzarella,Albahaca'),
('Pepperoni', 'Pepperoni, queso, salsa', 9.00, 'Pepperoni,Queso,Salsa'),
('Hawaiana', 'Jamón, piña, queso', 9.50, 'Jamón,Piña,Queso'),
('Cuatro Quesos', 'Mozzarella, parmesano, azul, ricotta', 10.00, 'Mozzarella,Parmesano,Queso azul,Ricotta'),
('Vegetariana', 'Champiñones, pimientos, cebolla, aceitunas', 8.00, 'Champiñones,Pimientos,Cebolla,Aceitunas');

INSERT INTO refresco (nombre, precio) VALUES 
('Coca-Cola', 1.50), 
('Sprite', 1.50), 
('Fanta Naranja', 1.50);

INSERT INTO extra (nombre, precio) VALUES 
('Papas fritas', 2.00), 
('Alitas de pollo', 3.50), 
('Aros de cebolla', 2.50);

INSERT INTO combo (nombre, descripcion, precio) VALUES
('Combo Familiar', '2 pizzas medianas + 2 refrescos + papas', 25.00),
('Combo Pepperoni Lover', 'Pizza Pepperoni + refresco + alitas', 14.00),
('Combo Vegetariano', 'Pizza Vegetariana + refresco + aros de cebolla', 12.00),
('Combo Hawaiano', 'Pizza Hawaiana + refresco + papas', 13.00),
('Combo Cuatro Quesos', 'Pizza Cuatro Quesos + refresco + alitas', 15.00);

-- Asignación de pizzas a combos
INSERT INTO combo_pizza (combo_id, pizza_id) VALUES 
(1,1), (1,2), (2,2), (3,5), (4,3), (5,4);
INSERT INTO combo_refresco (combo_id, refresco_id) VALUES 
(1,1), (1,2), (2,1), (3,2), (4,3), (5,1);
INSERT INTO combo_extra (combo_id, extra_id) VALUES 
(1,1), (2,2), (3,3), (4,1), (5,2);