// Reports API routes
// Example usage: GET /api/reports/product-sales
import { Router } from "express";
import * as c from "../controllers/reports.controller.js";
const r = Router();

r.get("/monthly-summary", c.getInvoicesMonthlySummary);
r.get("/product-sales", c.getSalesByProductSummary);
r.get("/customer-sales", c.getSalesByCustomerSummary);
r.get("/product-monthly-sales", c.getSalesByProductMonthlySummary);
r.get("/receipts", c.getReceiptsReport);
r.get("/invoices-with-receipts", c.getInvoicesWithReceiptsReport);

export default r;
