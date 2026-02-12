# Python Developer Task - Data Integration Pipeline
A complete data integration pipeline demonstrating ETL, REST API, and event-driven architecture.

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

### depnedencies installed
```bash
pip install requests fastapi uvicorn
pip install pylint
pip install email-validator
pip install pydantic
pip install fastapi uvicorn
pip install schedule

pip freeze > requirements.txt
```
### URL for aggregator:
http://localhost:8001/users/1/posts
http://localhost:8001/docs

## CMD:
step1: python -m function.t1_db -- db initialize

step2: python -m function.t3_aggregator -- Aggregator API

step3: python -m function.t4_worker -- Event Driven Integration

step4: python -m function.t2_etl      -- ETL
       python -m function.t2_etl --schedule  -- schedule ETL

## Linting
pylint function/function_name.py -- e.g. pylint function/t2_etl.py
