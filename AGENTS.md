# Project instructions for the coding agent

This repository is a demo workspace for an analytics task on a webshop data warehouse.
The shop is fictional and so is all of its data, but treat it as if it were real customer
data: it contains names, e-mail addresses, phone numbers and free-text support tickets.

## The warehouse

- DuckDB file: `data/warehouse.duckdb`, data from 2026-09-21 to 2026-11-01.
- Tables: `customers`, `products`, `sessions`, `events`, `orders`, `support_tickets`.
- Discover the schema yourself (`DESCRIBE`, `SHOW TABLES`). Do not assume column names.
- `events.event_name` is the funnel: `page_view`, `product_view`, `add_to_cart`,
  `checkout_start`, `payment_attempt`, `payment_failed`, `purchase`.

## How to work

- Use Python from the project environment: `.venv/bin/python`, with
  `duckdb.connect("data/warehouse.duckdb", read_only=True)`. The file is read-only on
  purpose. Never try to modify it.
- Put scripts and results into `analysis/`. Do not write anywhere else.
- Do not use the network. There is no reason to download anything.
- Keep personal data out of your written results: refer to customers by `customer_id`,
  never by name, e-mail address or phone number.
- Back every claim with a query result. Show the numbers, then the conclusion.
