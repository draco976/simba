const express = require('express');
const bodyParser = require('body-parser');
const { Pool } = require('pg');

// Initialize express app
const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Database connection
const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'ecommerce',
  database: 'ecommerce',
  password: 'password',
  port: 5432,
});

// Test database connection
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('Database connection error:', err.stack);
  } else {
    console.log('Database connected successfully');
  }
});

// Root endpoint
app.get('/', (req, res) => {
  res.send('API is running');
});

// GET all users
app.get('/api/users', async (req, res) => {
  try {
    const result = await pool.query('SELECT user_id, username, email, first_name, last_name FROM users');
    res.json(result.rows);
  } catch (err) {
    console.error('Error fetching users:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET user by ID
app.get('/api/users/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await pool.query(
      'SELECT user_id, username, email, first_name, last_name FROM users WHERE user_id = $1',
      [id]
    );
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Error fetching user:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST create new user
app.post('/api/users', async (req, res) => {
  try {
    const { username, email, password, first_name, last_name, date_of_birth } = req.body;
    
    // Simple validation
    if (!username || !email || !password) {
      return res.status(400).json({ error: 'Username, email and password are required' });
    }
    
    const result = await pool.query(
      'INSERT INTO users (username, email, password_hash, first_name, last_name, date_of_birth) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
      [username, email, password, first_name, last_name, date_of_birth]
    );
    
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('Error creating user:', err);
    if (err.code === '23505') { // Unique violation
      res.status(409).json({ error: 'Username or email already exists' });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

// GET all products
app.get('/api/products', async (req, res) => {
  try {
    const { category } = req.query;
    let query = 'SELECT * FROM products WHERE is_active = true';
    const queryParams = [];
    
    if (category) {
      query += ' AND category = $1';
      queryParams.push(category);
    }
    
    const result = await pool.query(query, queryParams);
    res.json(result.rows);
  } catch (err) {
    console.error('Error fetching products:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET product by ID
app.get('/api/products/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await pool.query('SELECT * FROM products WHERE product_id = $1', [id]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Product not found' });
    }
    
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Error fetching product:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST create new order
app.post('/api/orders', async (req, res) => {
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');
    
    const { user_id, items, shipping_address } = req.body;
    
    if (!user_id || !items || !items.length) {
      return res.status(400).json({ error: 'User ID and at least one item are required' });
    }
    
    // Calculate total amount
    let total_amount = 0;
    for (const item of items) {
      const productResult = await client.query(
        'SELECT price FROM products WHERE product_id = $1',
        [item.product_id]
      );
      
      if (productResult.rows.length === 0) {
        throw new Error(`Product with ID ${item.product_id} not found`);
      }
      
      total_amount += productResult.rows[0].price * item.quantity;
    }
    
    // Create order
    const orderResult = await client.query(
      'INSERT INTO orders (user_id, total_amount, shipping_address) VALUES ($1, $2, $3) RETURNING *',
      [user_id, total_amount, shipping_address]
    );
    
    const order_id = orderResult.rows[0].order_id;
    
    // Create order items
    for (const item of items) {
      await client.query(
        'INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES ($1, $2, $3, $4)',
        [order_id, item.product_id, item.quantity, item.unit_price]
      );
      
      // Update product stock
      await client.query(
        'UPDATE products SET stock_quantity = stock_quantity - $1 WHERE product_id = $2',
        [item.quantity, item.product_id]
      );
    }
    
    await client.query('COMMIT');
    
    res.status(201).json({
      order_id,
      user_id,
      total_amount,
      status: 'pending',
      items
    });
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('Error creating order:', err);
    res.status(500).json({ error: 'Internal server error' });
  } finally {
    client.release();
  }
});

// GET orders for a user
app.get('/api/users/:id/orders', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await pool.query('SELECT * FROM orders WHERE user_id = $1', [id]);
    res.json(result.rows);
  } catch (err) {
    console.error('Error fetching orders:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Start server
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});

module.exports = app;