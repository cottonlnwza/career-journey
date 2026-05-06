import { Router } from "express";
import { handleList, handleGet, handleCreate, handleUpdate, handleDelete } from "../controllers/salesPersons.controller.js";

const router = Router();
router.get("/", handleList);
router.get("/:id", handleGet);
router.post("/", handleCreate);
router.put("/:id", handleUpdate);
router.delete("/:id", handleDelete);

export default router;
