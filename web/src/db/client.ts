import fs from "fs";
import path from "path";
import Database from "better-sqlite3";

declare global {
  // eslint-disable-next-line no-var
  var __sqliteDb: import("better-sqlite3").Database | undefined;
}

export function getDatabasePath(): string {
  const raw = process.env.DATABASE_PATH?.trim();
  if (raw) return path.isAbsolute(raw) ? raw : path.join(process.cwd(), raw);
  return path.join(process.cwd(), "data", "app.db");
}

export function getDb(): Database.Database {
  if (globalThis.__sqliteDb) return globalThis.__sqliteDb;
  const file = getDatabasePath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new Database(file);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  globalThis.__sqliteDb = db;
  return db;
}

export function runMigrations(): void {
  const db = getDb();
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      created_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS atendimentos (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      flow_id TEXT NOT NULL,
      pergunta_text TEXT NOT NULL,
      categoria TEXT NOT NULL,
      categoria_confidence REAL,
      seguranca_status TEXT NOT NULL,
      fontes_count INTEGER NOT NULL DEFAULT 0,
      duracao_ms INTEGER NOT NULL,
      request_id TEXT NOT NULL UNIQUE,
      urgencia TEXT NOT NULL DEFAULT 'nenhuma',
      bloqueado INTEGER NOT NULL DEFAULT 0,
      sensitive_redacted INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_atendimentos_user_created
      ON atendimentos(user_id, created_at DESC);

    CREATE TABLE IF NOT EXISTS atendimento_detalhes (
      atendimento_id TEXT PRIMARY KEY,
      prompt_text TEXT,
      resposta_bruta TEXT,
      classificacao_json TEXT,
      langgraph_trace_json TEXT,
      FOREIGN KEY (atendimento_id) REFERENCES atendimentos(id) ON DELETE CASCADE
    );
  `);
}
