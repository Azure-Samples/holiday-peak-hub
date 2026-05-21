"use client";

import Centered from "@/layouts/centered";

export type LayoutProps = {
  children: React.ReactNode;
  pattern: string;
};

const getLayoutComponent = (_pattern: string) => {
  // Legacy patterns (`dashboard`, `products`) were tied to the deleted d-board
  // (layout-1) and ocean-tech e-commerce skins. Per ADR-035, all surfaces fall
  // back to the centered layout until per-audience layouts ship in F2-F6.
  return Centered;
};

const Layouts: React.FC<LayoutProps> = ({ children, pattern }) => {
  const LayoutComponent = getLayoutComponent(pattern);
  return <LayoutComponent>{children}</LayoutComponent>;
};

export default Layouts;
