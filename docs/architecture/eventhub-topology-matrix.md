# Event Hub topology matrix

_Last updated: 2026-03-18_

## Active topology

| Topic | Primary publishers | Active subscribers |
|---|---|---|
| `order-events` | CRUD `orders` routes, ACP checkout completion | `crm-*`, `ecommerce-*`, `inventory-*`, `logistics-*`, `product-management-*` services |
| `payment-events` | CRUD `payments` routes, Stripe webhook, ACP checkout completion | `crm-campaign-intelligence` |
| `return-events` | CRUD customer/staff returns lifecycle routes | `logistics-returns-support`, `crm-support-assistance` |
| `inventory-events` | CRUD `cart` route (successful reservation publish path) | `ecommerce-checkout-support`, `inventory-health-check`, `inventory-alerts-triggers`, `inventory-jit-replenishment` |
| `user-events` | CRUD `users` route (`PATCH /api/users/me` as `UserUpdated`) | `crm-campaign-intelligence`, `crm-profile-aggregation` |
| `shipment-events` | Reserved publisher path in CRUD integration (`publish_shipment_created`) | _No direct subscribers currently wired_ |

## Notes

- Product-domain event publishing remains pending a dedicated product mutation route set in CRUD.
- Shipment-domain subscribers remain pending in logistics services for end-to-end shipment lifecycle orchestration.
- This matrix is intended as a living architecture artifact and should be updated alongside topology changes.
