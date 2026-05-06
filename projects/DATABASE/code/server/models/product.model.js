import { z } from "zod";

export const ProductSchema = z.object({
  id: z.number().int(),
  code: z.string(),
  name: z.string(),
  unit_price: z.number().nullable().optional(),
  units_id: z.number().int(),
  units_code: z.string().optional(),
});

export const CreateProductBodySchema = z.object({
  code: z.string().optional(),
  name: z.string().min(1),
  units_id: z.coerce.number().int(),
  unit_price: z.coerce.number().optional(),
});

export const UpdateProductBodySchema = z.object({
  code: z.string().optional(),
  name: z.string().optional(),
  units_id: z.coerce.number().int().optional(),
  unit_price: z.coerce.number().optional(),
});

