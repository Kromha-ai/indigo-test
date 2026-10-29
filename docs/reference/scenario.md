# Project context

Our client runs an online gift shop. Their customers arrive knowing they need a present and very little else: *"something for my sister, she just moved into a new flat, maybe fifty euros."* Today those people browse category pages, get overwhelmed, and leave.

The client wants a product discovery assistant in the widget on their site - something that behaves like a good shop assistant. Ask a couple of sharp questions, understand the constraint, then recommend two or three things and say why.

What they have given you is a **CSV export of their catalogue** (raw_data/gift-shop-catalog.csv). That is it. No API, no documentation, no data team.

## The Catalog Service

Build a small **FastAPI** service that turns the CSV into something an AI agent can query.

It must expose at least these three tools:

| Tool | Purpose |
| --- | --- |
| `get_categories` | The categories available in the catalogue |
| `get_products_by_category` | The products within a category |
| `get_product_details` | The full detail of a single product |

### Requirements

- **REST endpoints with an OpenAPI specification served by the service.** This is what the indigo.ai platform turns into the agent's tools - it is not optional decoration.
- **Authenticated.** Protect the endpoints (API key header, bearer token, your choice) and document how a caller authenticates.

### Open questions

- What parameters does each operation take? Which are required, which have defaults, what are the constraints?
- What comes back, in what shape, and how much of it? An LLM has a finite context window - a category with forty products and long descriptions in every one is a problem you have to solve, not a fact you report.
- What do the descriptions say? Your tool and parameter descriptions are the *entire* basis on which the model decides whether to call you and with what. Write them for that reader.
- What happens on the unhappy paths? Category that does not exist, product ID that does not exist, filter that matches nothing. An error the agent can recover from is worth more than a correct 404.
- Do three operations actually cover the conversations you want to support? If not, add what is missing and say why.

## The Gift Assistant

The Catalog Service exists to be consumed by an agent built on the **indigo.ai platform**. The service's OpenAPI specification is loaded into the platform as a tool collection, and each operation becomes a tool the agent can call. The agent is what shoppers actually talk to, in the widget on the client's site.

The assistant should:

- Open with at most a couple of sharp questions - who is it for, what are they into, what budget, what occasion, by when - and only ask what would actually change the recommendation.
- Search the catalogue through the tools, never from memory. Every product, price and availability claim comes from a tool response in that conversation.
- Recommend **two or three** products, each with a one-line reason tied to what the shopper said (budget, recipient, occasion, delivery deadline).
- Handle the awkward cases gracefully: nothing within budget, the product they want is out of stock, a category the shop does not carry, a shopper who knows almost nothing about the recipient.

The agent is built from zero in a sandbox workspace on the indigo.ai platform, using the platform's own documentation (*Getting Started* and *Build Your AI Agents*).

### Conversations it must hold up in

- The shopper is **vague** (*"I need a gift"*) and needs narrowing down without being interrogated.
- The shopper is **specific** (*"a chef's knife under a hundred euros"*) and should get an answer, not a questionnaire.
- There is a **budget**, and something they liked is over it.
- The catalogue genuinely has **nothing suitable**, and the honest answer is to say so.
- The obvious recommendation is **out of stock**.
- The shopper goes **somewhere else entirely**: asks about the weather, pushes for a returns policy there is no data for, or tests what the assistant does when the subject is not gifts.

### What a recommendation is

A recommendation comes with a reason. *"This one, because it's in your budget, it ships in two days and it suits someone who has just moved"* is a recommendation. A list of three product names is a search result.

How the recommendation looks as a message matters as much as which products it contains. The widget is a narrow column, often on a phone. Three products with every catalogue field are a wall of text nobody reads; three bare names are useless. The design has to decide, and be able to justify:

- how many products go in one message;
- which fields earn their place;
- how the message is formatted;
- what the shopper can do next.

## Engagement scope and handover

What gets handed back to the client, from raw export to a live assistant:

1. **A deployed Catalog Service**, reachable over public HTTPS, authenticated, and serving its OpenAPI specification.
2. **The assistant, live on the indigo.ai platform**, with a shareable link that anyone can open and try without setup.
3. **The repository**, with specs, a decision record, and instructions to run and test the service locally. Its README documents the agent's prompt, how the tools were bound to the agent, and the conversation design decisions, especially how many questions are asked before recommending and why.
4. **A walkthrough** of the decisions: how the data was cleaned, why the tools are shaped the way they are, how the assistant's behaviour was tuned, and what was left out and why.

The client is not technical about APIs, but they will ask "why did you do it that way?". Every non-obvious choice needs a reason that fits in a sentence.