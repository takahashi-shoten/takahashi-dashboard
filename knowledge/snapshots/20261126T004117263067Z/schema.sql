CREATE TABLE knowledge(
  knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, content TEXT, evidence TEXT, source_url TEXT, timestamp TEXT, observed_at TEXT,
  audience TEXT, market TEXT, conditions TEXT, success_factors TEXT, failure_factors TEXT, counterexamples_json TEXT DEFAULT '[]',
  confidence REAL, status TEXT, origin TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE knowledge_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id INTEGER, at TEXT, change TEXT, old_status TEXT, new_status TEXT, old_conf REAL, new_conf REAL, reason TEXT);
CREATE TABLE knowledge_uses(
  id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id INTEGER, used_in TEXT, task TEXT, used_at TEXT, outcome TEXT, outcome_detail TEXT);
