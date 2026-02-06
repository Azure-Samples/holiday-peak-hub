# Customer demo script (Patagonia scenario)

## 1) Open the stage

Show the left column first.

Say:
“Pretend we’re on a product list page. We select a category and an item. That becomes page context.”

## 2) Select a product (PDP)

Click a jacket and pause.

Say:
“This is the product detail page. We pass the SKU and category into the chat. We don’t rely on the user to re-type this stuff.”

## 3) Ask a comparison question

Use Preset 1:
“Compare this to the best alternative for wet 40°F hikes. Give me the tradeoffs.”

While it runs, point to the right panel.

Say:
“On the right you can see the system steps. We inject page context, run scope checks, and call specific actions like ranking and availability.”

## 4) Prove it’s not magic

Scroll the trace panel and open details.

Say:
“This is the same contract we’d keep in production. Tools map to real services. The model doesn’t get direct access to internal APIs.”

## 5) Close with the path to production

Say:
“To productionize this, we swap the demo tools for real services, add auth/roles, and plug in your catalog via Search or a service layer. The UI stays the same.”
