import { z } from "zod";

export const emailSchema = z.string().email("Email inválido");
export const loginSchema = z.object({ email: emailSchema });

export type LoginInput = z.infer<typeof loginSchema>;
