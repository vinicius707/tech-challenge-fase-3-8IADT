import { getDatabasePath, getDb, runMigrations } from "../src/db/client";

runMigrations();
// Touch DB file
getDb().prepare("SELECT 1").get();
console.log("Migrations OK:", getDatabasePath());
