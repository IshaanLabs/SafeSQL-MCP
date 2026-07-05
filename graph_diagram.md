# SQL AI Agent - LangGraph Flow

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	classify(classify)
	generate_sql(generate_sql)
	validate(validate)
	risk(risk)
	approval(approval)
	execute(execute)
	summarize(summarize)
	error_handler(error_handler)
	audit(audit)
	__end__([<p>__end__</p>]):::last
	__start__ --> classify;
	approval -.-> execute;
	approval -.-> summarize;
	classify --> generate_sql;
	error_handler --> audit;
	execute --> summarize;
	generate_sql --> validate;
	risk -.-> approval;
	risk -.-> execute;
	risk -.-> summarize;
	summarize --> audit;
	validate -.-> error_handler;
	validate -.-> risk;
	audit --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

## Flow Legend

- **Solid lines** (`-->`) = always follows this path
- **Dashed lines** (`-.->`) = conditional routing

## Paths

| Scenario                   | Path                                                                                                      |
| -------------------------- | --------------------------------------------------------------------------------------------------------- |
| READ (SAFE)                | start → classify → generate_sql → validate → risk → execute → summarize → audit → end             |
| WRITE (MEDIUM/HIGH)        | start → classify → generate_sql → validate → risk → approval → execute → summarize → audit → end |
| WRITE (LOW)                | start → classify → generate_sql → validate → risk → execute → summarize → audit → end             |
| BLOCKED (DROP/TRUNCATE)    | start → classify → generate_sql → validate → error_handler → audit → end                            |
| BLOCKED (at risk)          | start → classify → generate_sql → validate → risk → summarize → audit → end                        |
| REJECTED (approval denied) | start → classify → generate_sql → validate → risk → approval → summarize → audit → end            |
