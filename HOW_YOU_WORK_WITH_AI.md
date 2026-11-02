# How you work with AI

## 1. **Your workflow.** How do you actually use AI tools when you build? Does it change between writing ordinary backend code and designing something an LLM will consume, like a tool interface or a prompt?

I have a small spec-driven development framework that is modified and improved when I feel I've really used it at 100% or I find a pain that needs fixing, I really want to understand the tools and decisions, not just jumping to the next trendy thing. For me, the difference is in the returned values, I can tell a FE colleague to use just few properties returned in the endpoint but the rest may be useful in the future and it can be ok but if the consumer is an LLM, it will cost more money and it can influence the behavior of the LLM even if it's "ignored by prompt", that would cost even more money. Besides that, descriptors become a very relevant part of coding the BE code.

## 2. **When it went wrong.** Describe a time AI-assisted work led you somewhere bad. How did you notice? What do you do differently now? Pay particular attention to the case where the thing you are building will itself be driven by a model rather than a human.

When building a customer support review workflow for a client, the agent recommended going with LangChain for the orchestration and it looked ok in the beginning because it is a reasonable choice, a tool the team knew and it was ok. Later on the project, the tech lead of the client told us that the orchestration needed to be included in the observability layer of their organization and wanted to have it as part of their queue system they had in Laravel for a custom tool they had built on top of that system. 

Recommendation was ok but the problem was that I didn't scope it properly because I thoght about it as an isolated system and I was too deep on AI-assisted designing. In the past, I would have asked about existing components and re-using logics but it is easy to get in echo chambers working with AI.

Nowadays, even if it didn't happen more than once, I've re-learnt how to deal with these situations basically coming back to basics in the scoping phase before architectre design, using AI-assisted tools for the process but asking the questions I'd have asked before, not assuming it was ok because there was a logical answer.

## 3. **In the room.** A client challenges a technical decision you made - they want it done another way. Walk us through how you handle that. When do you hold your position, and what would make you change it?

First of all, I would consider if the client's option is better than mine. I don't know who the client is but it is maybe someone with a deep technical knowledge and might be proposing and reasonable option. If that is the case and the change is doable considering timings and resources, I would just accept the change.

If the change is objectively a bad decision, by bad I mean that it doesn't match the requirements, it compromises security or will make the deadline unreacheable, I would explain why my decision is better (in the same terms) and what are the consequences of doing it in their way. 

If the client insists on doing the change, I would ask to modify requirements accordingly or push the deadline the number of days the new solutions requires. If the problem is a security issue, I would reject the change and escalate it. A security issue, depending on the case, can compromise other clients or the reputation of the company so it is not acceptable.