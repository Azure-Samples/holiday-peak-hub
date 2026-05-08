import type { ReactElement } from 'react';
import { ValueProp, type ValuePropProps } from './ValueProp';

/**
 * ValuePropGrid — grid of value-prop cards (ADR-035 §54 / Issue #1057).
 *
 * Cardinality lock per ADR-034 §1: the audience-router home renders exactly
 * three `ValueProp`s. Audience pages render 3–5. The `cardinality` prop is
 * a compile-time switch:
 *
 *   - `cardinality="three"`  : tuple of exactly 3 props (Hick's-Law lock on `/`).
 *   - `cardinality="three-to-five"` : array of 3–5 props (audience pages).
 *
 * Composites have no `className` escape hatch.
 */
export type ValuePropGridStrictProps = {
  /** Three-card lock (used only on `/`). */
  cardinality: 'three';
  items: [ValuePropProps, ValuePropProps, ValuePropProps];
  testId?: string;
};

export type ValuePropGridFlexibleProps = {
  /** 3–5 cards (audience pages). Cardinality is asserted at runtime. */
  cardinality: 'three-to-five';
  items: ValuePropProps[];
  testId?: string;
};

export type ValuePropGridProps = ValuePropGridStrictProps | ValuePropGridFlexibleProps;

const GRID_STYLE = {
  display: 'grid',
  gap: '1rem',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 18rem), 1fr))',
  width: '100%',
  maxWidth: '72rem',
  margin: '0 auto',
  padding: '0 1.5rem',
};

export function ValuePropGrid(props: ValuePropGridProps): ReactElement {
  if (props.cardinality === 'three-to-five') {
    if (props.items.length < 3 || props.items.length > 5) {
      throw new Error(
        `ValuePropGrid (three-to-five): cardinality must be 3–5; received ${props.items.length}.`,
      );
    }
  }
  return (
    <div data-testid={props.testId} data-valueprop-grid={props.cardinality} style={GRID_STYLE}>
      {props.items.map((item, index) => (
        <ValueProp key={`${item.headline}-${index}`} {...item} />
      ))}
    </div>
  );
}
