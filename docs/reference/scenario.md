# Project context

Our client runs an online gift shop. Their customers arrive knowing they need a present and very little else: *"something for my sister, she just moved into a new flat, maybe fifty euros."* Today those people browse category pages, get overwhelmed, and leave.

The client wants a product discovery assistant in the widget on their site - something that behaves like a good shop assistant. Ask a couple of sharp questions, understand the constraint, then recommend two or three things and say why.

What they have given you is a **CSV export of their catalogue**. That is it. No API, no documentation, no data team.

## The Catalog Service

Build a small **FastAPI** service that turns the CSV into something an AI agent can query.

It must expose at least these three tools:

| Tool | Purpose |
| --- | --- |
| `get_categories` | The categories available in the catalogue |
| `get_products_by_category` | The products within a category |
| `get_product_details` | The full detail of a single product |

### Requirements

- **REST endpoints with an OpenAPI specification served by the service.** This is what Indigo platform imports to create the tools - it is not optional decoration.
- **Authenticated.** Protect the endpoints (API key header, bearer token, your choice) and document how a caller authenticates.

### Open questions

- What parameters does each operation take? Which are required, which have defaults, what are the constraints?
- What comes back, in what shape, and how much of it? An LLM has a finite context window - a category with forty products and long descriptions in every one is a problem you have to solve, not a fact you report.
- What do the descriptions say? Your tool and parameter descriptions are the *entire* basis on which the model decides whether to call you and with what. Write them for that reader.
- What happens on the unhappy paths? Category that does not exist, product ID that does not exist, filter that matches nothing. An error the agent can recover from is worth more than a correct 404.
- Do three operations actually cover the conversations you want to support? If not, add what is missing and say why.