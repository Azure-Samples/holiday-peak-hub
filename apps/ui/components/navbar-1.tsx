"use client";

import Link from "next/link";

export default function Navbar1() {
  return (
    <header className="sticky top-0 z-20 border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm font-semibold text-gray-900 dark:text-white">
          Holiday Peak Hub
        </Link>
      </div>
    </header>
  );
}
