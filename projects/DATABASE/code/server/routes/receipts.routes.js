import { Router } from "express";
import * as c from "../controllers/receipts.controller.js";

const r = Router();

r.get("/next-no", c.getNextReceiptNo);
r.get("/", c.listReceipts);
r.post("/", c.createReceipt);
r.get("/:id/print", c.printReceipt);
r.get("/:id", c.getReceipt);
r.put("/:id", c.updateReceipt);
r.delete("/:id", c.deleteReceipt);

export default r;
