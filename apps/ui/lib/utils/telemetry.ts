type TracePayload = {
  message: string;
  severityLevel?: number;
  properties?: Record<string, string>;
};

type EventPayload = {
  name: string;
};

type BrowserAppInsights = {
  trackTrace?: (trace: TracePayload) => void;
  trackEvent?: (
    event: EventPayload,
    customProperties?: Record<string, string>,
    customMeasurements?: Record<string, number>,
  ) => void;
};

export type EcommerceEventName =
  | 'shelf_scrolled'
  | 'shelf_item_opened'
  | 'product_opened'
  | 'add_to_cart_clicked'
  | 'category_opened'
  | 'search_executed';

type ShelfScrollInteraction = 'wheel' | 'button' | 'keyboard' | 'drag';
type ProductOpenSource =
  | 'product_card_image'
  | 'product_card_title'
  | 'product_page'
  | 'canvas_shelf';

export interface EcommerceEventMap {
  shelf_scrolled: {
    shelf_title: string;
    interaction: ShelfScrollInteraction;
    item_count: number;
    delta: number;
  };
  shelf_item_opened: {
    shelf_title: string;
    item_id: string;
    item_href: string;
    item_position: number;
  };
  product_opened: {
    sku: string;
    source: ProductOpenSource;
  };
  add_to_cart_clicked: {
    sku: string;
    source: 'product_card' | 'product_page';
    in_stock: boolean;
  };
  category_opened: {
    slug: string;
    source: 'home_link' | 'category_page' | 'canvas_shelf';
  };
  search_executed: {
    query: string;
    source: 'search_page';
    result_count?: number;
  };
}

type TelemetryPayloadValue = string | number | boolean;
type TelemetryPayload = Record<string, TelemetryPayloadValue | undefined>;

const WARNING_SEVERITY = 2;

const getBrowserAppInsights = (): BrowserAppInsights | undefined => {
  if (typeof window === 'undefined') {
    return undefined;
  }

  return (window as unknown as { appInsights?: BrowserAppInsights }).appInsights;
};

const splitPayload = (payload: TelemetryPayload) => {
  const properties: Record<string, string> = {};
  const measurements: Record<string, number> = {};

  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined) {
      return;
    }

    if (typeof value === 'number') {
      measurements[key] = value;
      return;
    }

    properties[key] = typeof value === 'boolean' ? String(value) : value;
  });

  return {
    properties,
    measurements,
  };
};

export function trackEcommerceEvent<K extends EcommerceEventName>(
  eventName: K,
  payload: EcommerceEventMap[K],
) {
  const appInsights = getBrowserAppInsights();
  const telemetryPayload = payload as TelemetryPayload;

  if (appInsights?.trackEvent) {
    const { properties, measurements } = splitPayload(telemetryPayload);
    appInsights.trackEvent({ name: eventName }, properties, measurements);
    return;
  }

  if (appInsights?.trackTrace) {
    const { properties, measurements } = splitPayload(telemetryPayload);
    appInsights.trackTrace({
      message: eventName,
      severityLevel: 0,
      properties: {
        ...properties,
        measurements: JSON.stringify(measurements),
      },
    });
    return;
  }

  console.debug('ecommerce_telemetry', {
    eventName,
    payload,
  });
}

export function trackDebug(message: string, properties?: Record<string, string>) {
  const appInsights = getBrowserAppInsights();
  if (appInsights?.trackTrace) {
    appInsights.trackTrace({
      message,
      severityLevel: 0,
      properties,
    });
    return;
  }

  console.debug(message, properties || {});
}

export function trackWarning(message: string, properties?: Record<string, string>) {
  const appInsights = getBrowserAppInsights();
  if (appInsights?.trackTrace) {
    appInsights.trackTrace({
      message,
      severityLevel: WARNING_SEVERITY,
      properties,
    });
    return;
  }

  console.warn(message, properties || {});
}