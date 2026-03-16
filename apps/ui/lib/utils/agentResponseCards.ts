export type AgentCard = {
  id: string;
  title: string;
  value?: string;
  items?: string[];
};

export type AgentMessageView = {
  text: string;
  cards: AgentCard[];
  rawJson?: string;
};

const toRecord = (value: unknown): Record<string, unknown> | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
};

const toStringValue = (value: unknown): string | undefined => {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return undefined;
};

const readArrayStrings = (value: unknown): string[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((entry) => {
      if (typeof entry === 'string') {
        return entry;
      }

      if (entry && typeof entry === 'object') {
        const record = entry as Record<string, unknown>;
        const title = toStringValue(record.title || record.name || record.sku);
        const detail = toStringValue(record.message || record.reason || record.price);
        if (title && detail) {
          return `${title} — ${detail}`;
        }
        if (title) {
          return title;
        }
      }

      return undefined;
    })
    .filter((entry): entry is string => Boolean(entry));
};

export const formatAgentResponse = (payload: unknown): AgentMessageView => {
  if (typeof payload === 'string') {
    return {
      text: payload,
      cards: [],
    };
  }

  const base = toRecord(payload);
  if (!base) {
    return {
      text: 'Agent returned an unsupported payload.',
      cards: [],
      rawJson: JSON.stringify(payload, null, 2),
    };
  }

  const enriched = toRecord(base.enriched_product) || base;
  const cards: AgentCard[] = [];

  const summary =
    toStringValue(base.summary) ||
    toStringValue(base.answer) ||
    toStringValue(base.message) ||
    toStringValue(enriched.description);

  if (summary) {
    cards.push({
      id: 'summary',
      title: 'Summary',
      value: summary,
    });
  }

  const productTitle = toStringValue(enriched.title) || toStringValue(enriched.name);
  const productPrice = toStringValue(enriched.price);
  const productRating = toStringValue(enriched.rating);
  const productFeatures = readArrayStrings(enriched.features);

  if (productTitle || productPrice || productRating || productFeatures.length > 0) {
    const details: string[] = [];
    if (productTitle) details.push(productTitle);
    if (productPrice) details.push(`Price: ${productPrice}`);
    if (productRating) details.push(`Rating: ${productRating}`);

    cards.push({
      id: 'product',
      title: 'Product Snapshot',
      value: details.join(' • '),
      items: productFeatures.slice(0, 5),
    });
  }

  const inventory = toRecord(enriched.inventory);
  if (inventory) {
    const inventoryItems = Object.entries(inventory)
      .map(([key, value]) => {
        const readable = toStringValue(value);
        return readable ? `${key}: ${readable}` : undefined;
      })
      .filter((entry): entry is string => Boolean(entry));

    if (inventoryItems.length > 0) {
      cards.push({
        id: 'inventory',
        title: 'Inventory Signals',
        items: inventoryItems,
      });
    }
  }

  const related = readArrayStrings(enriched.related || base.related);
  if (related.length > 0) {
    cards.push({
      id: 'related',
      title: 'Related Products',
      items: related.slice(0, 5),
    });
  }

  const text =
    summary ||
    'Agent responded with structured enrichment details. See cards below.';

  return {
    text,
    cards,
    rawJson: cards.length === 0 ? JSON.stringify(payload, null, 2) : undefined,
  };
};
