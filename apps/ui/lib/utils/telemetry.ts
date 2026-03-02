type TracePayload = {
  message: string;
  severityLevel?: number;
  properties?: Record<string, string>;
};

type BrowserAppInsights = {
  trackTrace?: (trace: TracePayload) => void;
};

const WARNING_SEVERITY = 2;

export function trackWarning(message: string, properties?: Record<string, string>) {
  if (typeof window !== 'undefined') {
    const appInsights = (window as unknown as { appInsights?: BrowserAppInsights }).appInsights;
    if (appInsights?.trackTrace) {
      appInsights.trackTrace({
        message,
        severityLevel: WARNING_SEVERITY,
        properties,
      });
      return;
    }
  }

  console.warn(message, properties || {});
}