/**
 * Central logger for the backend (winston).
 * Use: logger.info(), logger.warn(), logger.error() instead of console.log.
 */
import winston from "winston";

const { combine, timestamp, printf, colorize } = winston.format;

const devFormat = printf(({ level, message, timestamp: ts, ...meta }) => {
  const metaStr = Object.keys(meta).length ? " " + JSON.stringify(meta) : "";
  return `${ts} [${level}] ${message}${metaStr}`;
});

const isProd = process.env.NODE_ENV === "production";
const logFormat = isProd
  ? combine(timestamp(), winston.format.json())
  : combine(colorize(), timestamp({ format: "HH:mm:ss" }), devFormat);

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || "info",
  format: logFormat,
  defaultMeta: { service: "invoicedoc-server" },
  transports: [new winston.transports.Console()],
});

export default logger;
