"use client"; // Now this is a Client Component

import { ReactNode } from "react";
import { Provider } from "react-redux";
import store from "@/store";
import NProgressHandler from "@/components/NprogressHandler";
import Layouts from "@/layouts";

interface ClientLayoutProps {
  children: ReactNode;
  pattern: string;
}

export default function ClientLayout({ children, pattern }: ClientLayoutProps) {
  return (
    <Provider store={store}>
      <NProgressHandler />
      <Layouts pattern={pattern}>{children}</Layouts>
    </Provider>
  );
}