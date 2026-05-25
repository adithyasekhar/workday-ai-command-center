# Governance Policy — Workday AI Command Center

## Core Principle
> AI reads and alerts. Humans decide and act.

## What AI Can Do
- Read integration status and error logs
- Read Prism dataset status
- Read Extend app status
- Analyze errors and explain in plain English
- Generate alerts for human action
- Generate health reports
- View audit log

## What AI Can NEVER Do
- Approve or reject any business process
- Initiate or approve terminations
- Approve or modify bonuses
- Modify compensation or job profiles
- Update or delete employee records
- Launch, delete or modify integrations
- Approve performance reviews
- Modify payroll
- Change security access

## Three Layers of Protection
1. Workday API Client — read-only scopes only
2. Python code — GET requests only, hard PermissionError on writes
3. Governance rules — blocked_forever list enforced on every action

## Data Privacy
These fields are NEVER sent to any AI — replaced with ***MASKED_BY_GOVERNANCE***:
- Social Security Number, National ID, Bank Account
- Exact Salary, Date of Birth, Passport Number
- Personal Email, Personal Phone, Medical Information

## Audit Trail
Every action logged to logs/audit_log.json with:
timestamp, event_type, action, triggered_by, details

Violations logged to logs/violations.json with HIGH severity.

## Human Action Required
AI generates alerts only. All actions taken by humans in Workday.
