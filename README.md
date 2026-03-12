# Repo


Text-to-SQL 시스템 구조

User Question
      ↓
rewrite_followup
      ↓
parse_intent
      ↓
if unsupported → fallback answer
if missing info → ambiguity gate
if ok → resolve_plan
      ↓
compile_sql
      ↓
execute_query
      ↓
compose_answer
