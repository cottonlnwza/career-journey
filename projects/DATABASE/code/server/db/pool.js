// PostgreSQL connection pool
// Example usage: pool.query("SELECT 1")
import pg from "pg";
import dotenv from "dotenv";
import logger from "../utils/logger.js";

dotenv.config();

const dbConfig = {
  host: process.env.DB_HOST || "pgdatabase",
  port: Number(process.env.DB_PORT || 5432),
  user: process.env.DB_USER || "root",
  password: process.env.DB_PASSWORD || "root",
  database: process.env.DB_NAME || "invoices_db",
};

export const pool = new pg.Pool(dbConfig);

pool.on("error", (err) => {
  logger.error("Database pool error", { message: err.message });
});
