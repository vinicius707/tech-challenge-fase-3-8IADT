import crypto from "crypto";
import bcrypt from "bcryptjs";
import { getDb, runMigrations } from "../src/db/client";

runMigrations();
const db = getDb();

const email = "demo@exemplo.org";
const password = "demo12345";
const hash = bcrypt.hashSync(password, 10);

const id = crypto.randomUUID();
const now = Date.now();

const tx = db.transaction(() => {
  const existing = db.prepare("SELECT id FROM users WHERE email = ?").get(email) as
    | { id: string }
    | undefined;
  if (existing) {
    console.log("Seed: user already exists", email);
    return;
  }
  db.prepare(
    `INSERT INTO users (id, email, name, password_hash, created_at)
     VALUES (?, ?, ?, ?, ?)`,
  ).run(id, email, "Utilizador demo", hash, now);
  console.log("Seed: created", email, "/", password);
});

tx();
