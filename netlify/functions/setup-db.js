import { neon } from '@neondatabase/serverless';

// One-time setup function - call /.netlify/functions/setup-db to create table
export const handler = async (event, context) => {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
  };

  try {
    const sql = neon(process.env.NETLIFY_DATABASE_URL);

    // Create subscribers table
    await sql`
      CREATE TABLE IF NOT EXISTS subscribers (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
      )
    `;

    // Create indexes
    await sql`CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email)`;
    await sql`CREATE INDEX IF NOT EXISTS idx_subscribers_created_at ON subscribers(created_at DESC)`;

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        message: 'Database setup complete! Table "subscribers" created.'
      })
    };
  } catch (error) {
    console.error('Setup error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        error: 'Setup failed',
        details: error.message
      })
    };
  }
};
