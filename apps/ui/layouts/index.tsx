"use client";

import Centered from "@/layouts/centered";
import Layout1 from "@/layouts/layout-1";
import ECommerce from "@/layouts/e-commerce";

export type LayoutProps = {
  children: React.ReactNode;
  pattern: string;
};

const getLayoutComponent = (pattern: string) => {
  switch (pattern) {
    case "dashboard":
      return Layout1;
    case "root":
      return Centered;
    case "products":
      return ECommerce;
    default:
      return Centered;
  }
};

const Layouts: React.FC<LayoutProps> = ({ children, pattern }) => {
  const LayoutComponent = getLayoutComponent(pattern);
  return <LayoutComponent>{children}</LayoutComponent>;
};

export default Layouts;
